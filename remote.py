import asyncio,struct,socket,select,sqlite3,time,sys
import aiosqlite3

rate = 1000000
capacity = 1000000

async def myRead(reader, _addr,lock):
    cur_amount = 0
    last_time = int(time.time())
    async with aiosqlite3.connect("user.db") as db:
        async with db.execute(f"select cur_amount,last_time from user where usrname={_addr!r}") as cursor:
            for row in cursor:
                cur_amount = row[0]
                last_time = row[1]
                print(f'cur_amount of client {_addr!r}: ',cur_amount)
    increment = (int(time.time())-last_time) * rate
    #lock
    await lock.acquire()
    cur_amount = min(cur_amount + increment, capacity)
    #unlock
    lock.release()
    async with aiosqlite3.connect("user.db") as db:
        await db.execute(f"update user set cur_amount={cur_amount!r} where usrname={_addr!r}")
        await db.commit()

    increment = (int(time.time())-last_time) * rate
    #lock
    await lock.acquire()
    cur_amount = min(cur_amount + increment, capacity)
    async with aiosqlite3.connect("user.db") as db:
        await db.execute(f"update user set cur_amount={cur_amount!r} where usrname={_addr!r}")
        await db.commit()
    #unlock
    lock.release()
    while cur_amount < 4096:
        increment = (int(time.time())-last_time) * rate
        #lock
        await lock.acquire()
        cur_amount = min(cur_amount + increment, capacity)
        async with aiosqlite3.connect("user.db") as db:
            await db.execute(f"update user set cur_amount={cur_amount!r} where usrname={_addr!r}")
            await db.commit()
        #unlock
        lock.release()
    #lock
    await lock.acquire()
    last_time = int(time.time())
    async with aiosqlite3.connect("user.db") as db:
        await db.execute(f"update user set last_time={last_time!r} where usrname={_addr!r}")
        await db.commit()
    #unlock
    lock.release()
    data = await reader.read(4096)
    #lock
    await lock.acquire()
    cur_amount -= len(data)
    async with aiosqlite3.connect("user.db") as db:
        await db.execute(f"update user set cur_amount={cur_amount!r} where usrname={_addr!r}")
        await db.commit()
    #unlock
    lock.release()
    return data

async def handle_tcp_echo(reader,writer):
    _addr = ''
    data = await reader.read(50)
    

    addr_len = struct.unpack('!B', data[0:1])[0]
    address = data[1:addr_len+1].decode()
    port = struct.unpack('!H', data[addr_len+1:addr_len+3])[0]
    _addr_len = struct.unpack('!B',data[addr_len+3:addr_len+4])[0]
    _addr = data[addr_len+4:addr_len+4+_addr_len].decode()
    print(address,port)
    print(f'client {_addr!r} exchange data')
    try:
        reader_out,writer_out=await asyncio.open_connection(address, port)
        print('连接成功')
    except:
        print('!!!!!!!!!!!!!!!!!!!!domainname connect err')
    lock = asyncio.Lock()
    in_to_out = exchange_data(reader, writer_out, _addr, lock)
    out_to_in = exchange_data(reader_out, writer, _addr, lock)
    await asyncio.gather(in_to_out,out_to_in)
 
async def exchange_data(reader, writer, _addr, lock):
    while True:
        try:
            data = await myRead(reader,_addr, lock)
            # data = await reader.read(4096)
            print(len(data),_addr)
            if not data:
                writer.close()
                break
        except:
            writer.close()
            break
        try:
            writer.write(data)
            await writer.drain()
        except:
            writer.close()
            break
        
async def handle_confirm(reader, writer):
    name = ''
    flag = 1
    data = await reader.read(50)
    option = struct.unpack("!B",data[0:1])[0]
    name_len = struct.unpack("!B",data[1:2])[0]
    
    name = data[2:2+name_len].decode()
    password_len = struct.unpack("!B", data[2+name_len:3+name_len])[0]
    password = data[3+name_len:3+name_len+password_len].decode()
    
    async with aiosqlite3.connect("user.db") as db:
        async with db.execute(f"select usrname,usrpassword,cur_amount,last_time from user") as cursor:
            print("all info:")
            for row in cursor:
                 print(row[0],row[1],row[2],row[3])
        if option == 0:
            await db.execute(f"insert into user (usrname,usrpassword,cur_amount,last_time) \
                values ({name!r},{password!r},{capacity!r},{int(time.time())!r})")
            await db.commit()

            print('after insert:')
            async with db.execute(f"select usrname,usrpassword,cur_amount,last_time from user") as cursor:
                print("all info:")
                for row in cursor:
                    print(row[0],row[1],row[2],row[3])
            flag = 0
        elif option == 1:
            find = 1
            async with db.execute(f'select usrpassword  from user where usrname="{name}"') as cursor:
                if len(list(cursor))==0:
                    flag = 2
                    find = 0
                
            if find == 1:
                async with db.execute(f'select usrpassword from user where usrname="{name}"') as cursor:
                    for row in cursor:
                        if row[0] != password:
                            print(row[0],password)
                            flag = 10
                            print('wrong pwd')
    db.close()
    data0 = struct.pack("!B",flag)
    writer.write(data0)
    await writer.drain()
    if flag == 1:
        await handle_tcp_echo(reader, writer)

async def main():
    global rate,capacity
    if sys.argv[1]=='-d':
        rate = 1000000
    else:
        rate = int(sys.argv[1])
    capacity = rate
    async with aiosqlite3.connect("user.db") as db:
        print("清除数据")
        await db.execute("drop table if exists user")
        await db.commit()
        await db.execute('''create table user
        (usrname test primary key not null,
        usrpassword text not null,
        cur_amount integer not null,
        last_time integer not null);''')
        await db.execute(f"insert into user (usrname,usrpassword,cur_amount,last_time) \
        values ('abc','123',{capacity!r},{int(time.time())!r})")
        await db.execute(f"insert into user (usrname,usrpassword,cur_amount,last_time) \
        values ('efg','321',{capacity!r},{int(time.time())!r})")
        await db.commit()
        
                 
    while True:
        
        confirm = await asyncio.start_server(handle_confirm,'127.0.0.1',6666)
        async with confirm:
            await confirm.serve_forever()
    
        
asyncio.run(main())