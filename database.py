import asyncio, aiosqlite, time, sys

from sanic import Sanic
from sanic import response
from sanic import exceptions

app = Sanic('RemoteAdmin')
app.config.DB_NAME = 'user.db'

@app.exception(exceptions.NotFound)
async def ignor_404(req, exc):
    return response.text('errUrl', status = 404)

@app.post('/user')
async def add_user(req):
    usrname = req.json.get('usrname')
    usrpassword = req.json.get('usrpassword')
    if not usrname or not usrpassword:
        return response.text(f'err usrname={usrname} usrpassword={usrpassword}', status = 400)
    async with aiosqlite.connect(app.config.DB_NAME) as db:
        await db.execute("INSERT INTO user(usrname,usrpassword,cur_amount,last_time) VALUES(?,?,?,?)",(usrname,usrpassword,int(sys.argv[1]),time.time()))
        await db.commit()
    return response.json({})

@app.delete('/user/<name>')
async def delete_user(req, name):
    async with aiosqlite.connect(app.config.DB_NAME) as db:
        await db.execute("DELETE FROM user WHERE usrname=?",(name,))
        await db.commit()
    return response.json({})

@app.put('/user/<usrname>')
async def modify_password(req, usrname):
    usrpassword = req.json.get('usrpassword')
    if not usrname or not usrpassword:
        return response.text(f'err usrname={usrname} usrpassword={usrpassword}', status = 400)
    async with aiosqlite.connect(app.config.DB_NAME) as db:
        await db.execute("UPDATE user SET usrpassword=? WHERE usrname=?",(usrpassword, usrname))
        await db.commit()
    return response.json({})

@app.get('/user')
async def list_all_user(req):
    userList = list()
    async with aiosqlite.connect(app.config.DB_NAME) as db:
        async with db.execute("SELECT usrname,usrpassword,cur_amount FROM user;") as cursor:
            async for row in cursor:
                user = {'usrname':row[0], 'usrpassword':row[1], 'cur_amount':row[2]}
                userList.append(user)
    return response.json(userList)

@app.get('/user/<name>')
async def query_one_user(req, name):
    async with aiosqlite.connect(app.config.DB_NAME) as db:
        async with db.execute("SELECT usrpassword,cur_amount FROM user WHERE usrname=?",(name,)) as cursor:
            async for row in cursor:
                user = {'usrname':name, 'usrpassword':row[0],'cur_amount':row[1]}
                return response.json(user)
    return response.json({}, status = 404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port = 8088)