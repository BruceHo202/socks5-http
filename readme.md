# Python程序设计课程大作业

班级：2018211310

学号：2018211517

姓名：何泓川

# 本地系统

【文字描述】

* 本地系统运行方法（console port为监听localgui的端口 如果只运行local.py可以直接写成8081（如果listenport不是8081的话））：

  python local.py -[option] [username] [password] [console port] [listen port] (option包括注册和登录)

  例如：

  登录：python local.py -l abc 123 8081 8080

  注册：python local.py -s hhc 456 8081 8080

  (注册中两个port都没有实际作用，因为注册只是把信息发送给remote，等待remote回送反馈后就结束程序)

  （远端数据库中预置两个用户：用户名abc，密码123；用户名efg，密码321）

* 概要

  主程序先启动计算接受带宽和发送带宽的函数。

  实现方式：设置四个全局变量gSendBrandWidth、gRecvBrandWidth、now_rdata_len、now_sdata_len，在StreamReader.read()后now_rdata_len加上读取的数据长度，SreamWriter.write()后now_sdata_len加上发送数据的长度。每秒钟先用now_rdata_len和now_sdata_len分别给gRecvBrandWidth、gSendBrandWidth赋值，然后把now_rdata_len和now_sdata_len清零。gSendBrandWidth和gRecvBrandWidth就是本地系统的实时发送带宽和接受带宽。

  然后监听console port，有连接时执行localConsole函数。localConsole函数每秒钟发送一次本地系统的接受带宽和发送带宽。

  （1）如果选项是登录，则监听端口listen port，如果有连接则执行handle_tcp函数。handle_tcp函数中先把选项（登录还是注册）、用户名长度、用户名、密码长度、密码发送给remote，remote经过处理后回传反馈，告诉本地系统是否注册成功或登录成功。如果登录成功，则先收一个来自客户端的数据包，这个包是用来建立连接的。判断是http服务还是socks5服务。判断方法是，如果数据的第一个字节是'H'且第二个字节是'T'，则是http，否则，解析数据包第一个字节，如果是5，则是socks5。两种服务都是先解析出来要建立连接的外部地址和端口，把外部地址和端口和用户名打包发送给remote端。两种服务的解析地址的方法在下面介绍。建立连接后执行exchan_data函数进行交换数据，交换数据部分在与远端通信部分有详细描述。

  （2）如果选项是注册，则把选项（注册）、用户名长度、用户名、密码长度、密码打包发送给remote，接收到remote反馈是结束程序。

## SOCKS5服务

```python
async def handle_socks5_echo(reader,writer):
    print('------socks5------')
    data = await reader.read(4096)
    version,nmethods,methods=struct.unpack('!BBB',data[:3])
    if methods == 0:
        print("hi")
    writer.write(struct.pack('!BB',version,0))
    await writer.drain()
    
    data = await reader.read(4096)
    _, command, _, address_type = struct.unpack('!BBBB', data[:4])
    #ipv4
    if address_type == 1 and command == 1:
        address = '.'.join([str(a) for a in struct.unpack('!BBBB',data[4:8])])
        print("address")
        print(address)
        port = struct.unpack('!H',data[-2:])[0]
        reply=struct.pack('!8B',5,0,0,3,struct.unpack(data[4:8]))+struct.pack('!H',port)
        try:
            reader_out,writer_out=await asyncio.open_connection(address, port)
            print('连接成功')
        except:
            print('ipv4 connect err!!!!!!!!!!')
    #域名
    elif address_type == 3 and command == 1:
        domain_size = struct.unpack('!B', data[4:5])[0]
        address = data[5:domain_size+5].decode()
        
        port = struct.unpack('!H', data[-2:])[0]
        print(address)
        print(port)
        reply=struct.pack('!5B',5,0,0,3,domain_size)+address.encode()+struct.pack('!H',port)
        try:
            reader_out,writer_out=await asyncio.open_connection(address, port)
            print('连接成功')
        except:
            print('!!!!!!!!!!!!!!!!!!!!domainname connect err')
            
    writer.write(reply)
    await writer.drain()
    
    in_to_out = exchange_data(reader, writer_out)
    out_to_in = exchange_data(reader_out, writer)
    await asyncio.gather(in_to_out,out_to_in)
```

【文字描述】先解析version、nmethods、methods，如果methods是0，则把version和methods打包发送给客户端。再接受一个数据包，解析类型和command。如果command是1，类型是ipv4，则先按点分十进制解析ipv4地址，再解析端口，把地址和端口和用户名打包发送给remote，再打包反馈信息发送给客户端，至此完成建立连接。上述代码是第一次作业的代码，是直接与目的地址建立连接，且没有打包用户名。

## HTTPS隧道服务

```python
async def handle_http_echo(reader,writer):
    print('------HTTP tunnel------')
    data = await reader.read(4096)
    data = data[8:]
    try:
      address = ''
      seq=0
      for i in range(0,50):
        if data[i]==58:
          seq=i
          break
      address=data[0:seq]
      seq1=seq
      for i in range(seq,seq+100):
        if data [i] == 32:
          seq1 = i
          break
      port = data[seq+1:seq1]
      port = int(port.decode())
      data = struct.pack("!B",len(address)) + address+ struct.pack("!H", port) + struct.pack("!B",len(uname))+uname.encode()

      #reader_out,writer_out=await asyncio.open_connection('127.0.0.1', 7878)
      print(data)
      writer_out.write(data)
      now_wdata_len += len(data)
      await writer_out.drain()
      try:
        sendbuf='HTTP/1.1 200 Connection Established\r\n\r\n'
        writer.write(sendbuf.encode())
        now_wdata_len += len(sendbuf.encode())
        await writer.drain()
        print('======send sucess')
        in_to_out = exchange_data(reader, writer_out)
        out_to_in = exchange_data(reader_out, writer)
        await asyncio.gather(in_to_out,out_to_in)
        except:
          print('!!!!!!!!fail to send')

          except:
            print('http send err')
```

【文字描述】先读到字符':'为止，记录下角标，从数据开始到':'之前为目的地址，然后再从冒号之后到空格之前为目的端口。把目的地址、端口和用户名打包发送给remote，然后发送反馈信息给客户端。

上述代码为最终版中http隧道服务的解析地址和端口的方法，本人在作业二中的方法数据不是一次性读完，是读到冒号停止进行处理或读到空格停止进行处理，然后再继续读后续的数据。在最终版中需要同时支持http和socks5，需要先判断服务类型，所以最终版中先读完整的来自客户端建立连接的请求，再进行分析。

## 与远端模块通信

```python
async def exchange_data(reader, writer):
    while True:
        try:
            data = await reader.read(4096)
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
```

【文字描述】与远端模块通信包括程序开始发送选项（注册或登录）、发送连接请求（解析出目的地址、端口，和用户名打包发送给remote）、交换数据。前两个在概要和socks、http隧道服务中有体现，所以这里只介绍交换数据部分。exchange_data函数有三个参数，包括self、StreamReader、StreamWriter。这个函数功能是从StreamReader中读数据，发送到StreamWriter。调用exchange_data时要执行两次，一次是传递与客户端的StreamReader和与remote的StreamWriter，一次是传递与remote的StreamReader和与客户端的StreamWriter，即接受客户端数据发送给remote，再接受remote数据发送给客户端。

## 图形管理界面

```python
class Window(QWidget):
    def __init__(self):
        super().__init__()

        self.resize(750, 750)
        self.move(1000, 200)

        self.sendBandwidthLabel = QLabel(self)
        self.sendBandwidthLabel.setText('发送带宽')
        self.sendBandwidthLabel.resize(500,30)
        self.sendBandwidthLabel.move(250,0)
        self.sendBandwidthLabel.setStyleSheet("color: rgb(0, 0, 0);background-color: white")

        self.recvBandwidthLabel = QLabel(self)
        self.recvBandwidthLabel.setText('接收带宽')
        self.recvBandwidthLabel.resize(500,30)
        self.recvBandwidthLabel.move(250,40)
        self.recvBandwidthLabel.setStyleSheet("color: rgb(0, 0, 0);background-color: white")

        self.listenportlabel = QLabel(self)
        self.listenportlabel.setText('console port')
        self.listenportlabel.move(0,0)
        self.listenPortLine = QLineEdit(self)
        self.listenPortLine.move(0,30)
        self.listenPortLine.setText('')

        self.consolePortlabel = QLabel(self)
        self.consolePortlabel.setText('listen Port')
        self.consolePortlabel.move(0,60)
        self.consolePortLine = QLineEdit(self)
        self.consolePortLine.move(0,90)
        self.consolePortLine.setText('')

        self.usernamelabel = QLabel(self)
        self.usernamelabel.setText('user name')
        self.usernamelabel.move(0,120)
        self.usernameLine = QLineEdit(self)
        self.usernameLine.move(0,150)
        self.usernameLine.setText('')

        self.passwordlabel = QLabel(self)
        self.passwordlabel.setText('password')
        self.passwordlabel.move(0,180)
        self.passwordLine = QLineEdit(self)
        self.passwordLine.move(0,210)
        self.passwordLine.setText('')
        self.passwordLine.setEchoMode(QLineEdit.Password)

        self.startBtn = QPushButton(self)
        self.startBtn.move(0,250)
        self.startBtn.setText('start button')

        self.startBtn.clicked.connect(self.startClicked)
        
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.finished.connect(self.processFinished)
        self.process.started.connect(self.processStarted)
        self.process.readyReadStandardOutput.connect(self.processReadyRead)
        
    def processReadyRead(self): 
        data = self.process.readAll()
        
        try:
            print(data.data().strip())
        except Exception as exc:
            log.error(f'{traceback.format_exc()}')
            exit(1)
        
    def processStarted(self):
        process = self.sender()
        processId = process.processId()
        print('pid = ',processId)
        log.debug(f'pid={processId}')
        self.startBtn.setText('Stop')
        # self.processIdLine.setText(str(processId))

        self.websocket = QWebSocket()
        self.websocket.connected.connect(self.websocketConnected)
        self.websocket.disconnected.connect(self.websocketDisconnected)
        
        try:
            self.websocket.open(QUrl(f'ws://127.0.0.1:{self.listenPortLine.text()}/'))
            self.websocket.textMessageReceived.connect(self.websocketMsgRcvd)
            print('conn')
        except:
            print('conn err')
        
    def processFinished(self):
        self.process.kill()

    def startClicked(self):
        btn = self.sender()
        text = btn.text().lower()
        if text.startswith('start'):
            listenPort = self.listenPortLine.text()
            username = self.usernameLine.text()
            password = self.passwordLine.text()
            consolePort = self.consolePortLine.text()
            cmdLine = 'python local.py -l ' + username + ' '+  password + ' ' + listenPort + ' ' + consolePort
            print(cmdLine)
            log.debug(f'cmd={cmdLine}')
            self.process.start(cmdLine)
        else:
            self.process.kill()

    def websocketConnected(self):
        pass
        # self.websocket.sendTextMessage('secret')

    def websocketDisconnected(self):
        self.process.kill()

    def websocketMsgRcvd(self, msg):
        print('recved msg')
        log.debug(f'msg={msg}')
        sendBandwidth, recvBandwidth, *_= msg.split()
        print(sendBandwidth, recvBandwidth)
        nowTime = QDateTime.currentDateTime().toString('hh:mm:ss')
        self.sendBandwidthLabel.setText(f'发送带宽：{nowTime} {sendBandwidth}')
        self.recvBandwidthLabel.setText(f'接收带宽：{nowTime} {recvBandwidth}')
```

【文字描述】先设置界面布局， 包括显示发送和接受带宽的QLabel、输入console port、listen port、用户名、密码的QLineEdit、启动按钮QPushButton。把启动按钮按下的信号与startClicked槽函数连接。然后新建一个进程。把进程开始的信号和槽函数processStarted连接，把进程结束的信号和槽函数processFinished连接。

startClicked函数用来获取用户输入的console port、listen port、用户名、密码，生成一个用来启动local.py的命令的字符串，再用这个字符串启动新建的进程。

processStarted函数用来与local建立连接，从而获取local的实时发送带宽和接受带宽。processFinished函数用来结束进程。

# 远端系统

【文字描述】

* 远端系统运行方法：python remote.py [BrandWidth]

  例如：python remote.py 100000 此命令用来控制每个用户流量为100KB/s。

* 概要

  如果user.db存在则删除。然后建立一个user.db，其中有属性usrname、usrpassword、cur_amount、last_time。然后监听端口6666，如果有连接则执行confirm函数。confirm函数中先接受一个数据包，这个数据包是local.py中创建的。从中读取选项（登录或注册）、用户名、密码。如果是注册则在数据库中插入一条记录，如果是登录则从数据库中查找对应该用户名的密码，如果密码错误则返回wrong password信息，密码正确则返回密码正确信息，然后执行handle_tcp_echo函数。handle_tcp_echo函数中先从local端接受一个数据包，其中包括要建立连接的外部地址和端口和用户名。然后与该目的地址建立连接。此时创建一个同步锁，用来在交换数据部分防止多个协程同时修改数据库中用户令牌的信息。然后交换数据，从local读数据发送给外部服务器，再从外部服务器读数据发送给local。

## 与本地模块通信

```python
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
    
    # async with aiosqlite3.connect("user.db") as db:
    #     async with db.execute(f"select usrname,usrpassword,cur_amount,last_time from user") as cursor:
    #         print("all info:")
    #         for row in cursor:
    #              print(row[0],row[1],row[2],row[3])
    #     if option == 0:
    #         await db.execute(f"insert into user (usrname,usrpassword,cur_amount,last_time) \
    #             values ({name!r},{password!r},{capacity!r},{int(time.time())!r})")
    #         await db.commit()

    #         print('after insert:')
    #         async with db.execute(f"select usrname,usrpassword,cur_amount,last_time from user") as cursor:
    #             print("all info:")
    #             for row in cursor:
    #                 print(row[0],row[1],row[2],row[3])
    #         flag = 0
    #     elif option == 1:
    #         find = 1
    #         async with db.execute(f'select usrpassword  from user where usrname="{name}"') as cursor:
    #             if len(list(cursor))==0:
    #                 flag = 2
    #                 find = 0
                
    #         if find == 1:
    #             async with db.execute(f'select usrpassword from user where usrname="{name}"') as cursor:
    #                 for row in cursor:
    #                     if row[0] != password:
    #                         print(row[0],password)
    #                         flag = 10
    #                         print('wrong pwd')
    # db.close()
    data0 = struct.pack("!B",flag)
    writer.write(data0)
    await writer.drain()
    if flag == 1:
        await handle_tcp_echo(reader, writer)
```

【文字描述】注释部分为对数据库的操作，与本地通信无关。exchange_data用于读取外部数据发送给本地模块和读取本地模块数据发送给外部。handle_confirm用于本地连接到远端程序时远端读取本地发来的请求，包括选项（登录或注册）、用户名、密码。更新数据库后把操作结果（密码错误或注册成功或登录成功）发送给本地端。上述操作读数据时用myRead函数，传入参数_addr（用户名）进行用户流量控制。

## 多用户管理

```python
async def handle_confirm(reader, writer):
    # name = ''
    # flag = 1
    # data = await reader.read(50)
    # option = struct.unpack("!B",data[0:1])[0]
    # name_len = struct.unpack("!B",data[1:2])[0]
    
    # name = data[2:2+name_len].decode()
    # password_len = struct.unpack("!B", data[2+name_len:3+name_len])[0]
    # password = data[3+name_len:3+name_len+password_len].decode()
    
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
        await db.execute("delete from user")
        await db.commit()
        print("清除数据")
        await db.execute("drop table user")
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
```

【文字描述】注释部分是与本地模块通信，与多用户管理无关。handle_confirm中获取本地端用户信息，如果是注册就更新数据库（插入），如果是登录就从数据库中查找用户和密码，查看输入的密码是否正确。main中创建多用户的数据库。另外在用户流控部分，myRead函数通过传入参数_addr(用户名)也会对多用户进行管理，从数据库中读取信息，并结合同步锁更新数据库，此部分在用户流控详细介绍。

## 用户流控

```python
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
```

【文字描述】用户流控发生在读取数据时，所以把带有流控的读取数据封装成一个函数，返回值是读取到的数据。传入参数StreamReader（用来读取数据）、_addr（用户名）和lock（同步锁）。流控采用令牌桶算法。所有用户令牌桶容量capacity为输入的参数，即控制的流量速率，令牌产生速率也设为与capacity相同的值，以此来控制每个用户的流量，即每秒最多读取capacity字节的数据，这一秒内他的已经用完也会新产生rate*1=capacity的令牌量。数据库中每个用户初始都有cur_amount（令牌量）和last_time（上次从令牌桶中取令牌的时间）。当用户要读取数据时，调用myRead函数，函数中先查询该用户的当前令牌量和上次取令牌的时间，通过这两个值计算当前令牌量。变量increment表示从上次取令牌到当前时刻按照令牌产生速率令牌的产生量，如果cur_amount+increment大于令牌桶容量capacity则将用户的cur_amount修改为capacity，否则改为cur_amount+increment。然后进行数据的读取。如果用户的cur_amount不足4096就阻塞，阻塞过程中持续根据当前时间更新用户的cur_amount。当令牌量cur_amount超过4096时，把上次使用令牌的时间last_time设置为当前的时间，然后用调用StreamReader.read(4096)，即最多读4096个字节，然后该用户令牌量减去读取到数据的长度。上述每次对数据库做修改操作时都需要使用同步锁，防止多个协程同时修改用户的令牌量。

## 用户数据库管理接口

```python
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
    app.run(host='127.0.0.1', port = 8088)
```

【文字描述】通过运行一个单独的程序作为服务端，insomnia可以作为客户端通过地址和端口连接到该程序，执行增、删、改、查操作时通过此程序进行对数据库的修改。本程序需要传递一个参数作为用户的流量控制，如果用下列语句运行程序：python interface.py 100000 用来控制用户流量为100KB/s。

# 程序完整源码

【此处根据个人具体情况粘贴程序源码，可以是单个文件或多个文件，但是只限于自己编写的源程序】

local.py 

```python
import asyncio,struct,socket,select,sys,time,websockets,logging, traceback

uname = ''

gSendBrandWidth = 0
gRecvBrandWidth = 0
now_rdata_len = 0
now_wdata_len = 0

async def handle_tcp(reader, writer):
    global now_rdata_len
    global now_wdata_len
    global uname
    option = sys.argv[1]
    name = sys.argv[2]
    uname = name
    password = sys.argv[3]
    if option == '-s':
        data0 = struct.pack("!B",0)#sign in
    elif option == '-l':
        data0 = struct.pack("!B",1)#log in
    reader_out, writer_out = await asyncio.open_connection('127.0.0.1', 6666)
    data0 += struct.pack("!B",len(name))+name.encode()+struct.pack("!B",len(password))+password.encode()
    writer_out.write(data0)
    now_wdata_len += len(data0)
    
    await writer_out.drain()
    data1=''
    
    data1 = await reader_out.read(1024)
    now_rdata_len += len(data1)
    flag = struct.unpack("!B",data1[0:1])[0]
    
    if flag == 0:
        print('sign success')
    elif flag == 10:
        print('wrong password')
        return
    elif flag == 2:
        print('username not find')
        return
        ########33
    elif flag == 1:
        print(f'{name!r} log in sucess')
        data = await reader.read(4096)
        now_rdata_len += len(data)
        choose = -1
        if data[0] == 67 and data[1] == 79:
            choose = 0
        else:
            version,nmethods,methods=struct.unpack('!BBB',data[:3])
            if version == 5:
                choose = 1
        if choose == 0:#http
            print('-----http-----')
            data = data[8:]
            try:
                address = ''
                seq=0
                for i in range(0,50):
                    if data[i]==58:
                        seq=i
                        break
                address=data[0:seq]
                seq1=seq
                for i in range(seq,seq+100):
                    if data [i] == 32:
                        seq1 = i
                        break
                port = data[seq+1:seq1]
                port = int(port.decode())
                data = struct.pack("!B",len(address)) + address+ struct.pack("!H", port) + struct.pack("!B",len(uname))+uname.encode()

                #reader_out,writer_out=await asyncio.open_connection('127.0.0.1', 7878)
                print(data)
                writer_out.write(data)
                now_wdata_len += len(data)
                await writer_out.drain()
                try:
                    sendbuf='HTTP/1.1 200 Connection Established\r\n\r\n'
                    writer.write(sendbuf.encode())
                    now_wdata_len += len(sendbuf.encode())
                    await writer.drain()
                    print('======send sucess')
                    in_to_out = exchange_data(reader, writer_out)
                    out_to_in = exchange_data(reader_out, writer)
                    await asyncio.gather(in_to_out,out_to_in)
                except:
                    print('!!!!!!!!fail to send')

            except:
                print('http send err')
        elif choose == 1:#socks5
            print('-----socks5-----')
            if methods == 0:
                print("hi")
            writer.write(struct.pack('!BB',version,0))
            now_wdata_len += 2
            await writer.drain()
            
            data = await reader.read(4096)
            now_rdata_len += len(data)
            _, command, _, address_type = struct.unpack('!BBBB', data[:4])
            #ipv4
            if address_type == 1 and command == 1:
                try:
                    address = '.'.join([str(a) for a in struct.unpack('!BBBB',data[4:8])])
                    print("address")
                    print(address)
                    port = struct.unpack('!H',data[8:10])[0]
                    data = struct.pack('!B', len(address))+address.encode()+struct.pack('!H', port) + struct.pack("!B",len(uname))+uname.encode()
                    #reader_out,writer_out=await asyncio.open_connection('127.0.0.1', 7878)
                    print('连接成功')
                    
                    writer_out.writer(data)
                    now_wdata_len += len(data)
                    await writer_out.drain()
                    reply=struct.pack('!4B',5,0,0,1)+address.encode()+struct.pack('!H',port)
                except:
                    print('ipv4 connect err!!!!!!!!!!')
            #域名
            elif address_type == 3 and command == 1:
                try:
                    addr_len = struct.unpack('!B', data[4:5])[0]
                    address = data[5:5+addr_len].decode()
                    port = struct.unpack('!H', data[5+addr_len:5+addr_len+2])[0]
                    data = struct.pack('!B', addr_len)+address.encode()+struct.pack('!H', port) + struct.pack("!B",len(uname))+uname.encode()
                    #reader_out,writer_out=await asyncio.open_connection('127.0.0.1', 7878)
                    print('连接成功')
                    
                    writer_out.write(data)
                    now_wdata_len += len(data)
                    await writer_out.drain()
                    reply=struct.pack('!5B',5,0,0,3,addr_len)+address.encode()+struct.pack('!H',port)
                    #reply = await reader_out.read(4096)
                except:
                    print('!!!!!!!!!!!!!!!!!!!!domainname connect err')
                    
            writer.write(reply)
            now_wdata_len += len(reply)
            await writer.drain()
            
            in_to_out = exchange_data(reader, writer_out)
            out_to_in = exchange_data(reader_out, writer)
            await asyncio.gather(in_to_out,out_to_in)

async def exchange_data(reader, writer):
    global now_rdata_len
    global now_wdata_len
    while True:
        try:
            data = await reader.read(4096)
            now_rdata_len += len(data)
            if not data:
                writer.close()
                break
        except:
            writer.close()
            break
        try:
            writer.write(data)
            now_wdata_len += len(data)
            await writer.drain()
        except:
            writer.close()
            break
        
async def clacbrandwidth():
    global gSendBrandWidth
    global gRecvBrandWidth
    global now_rdata_len
    global now_wdata_len
    gSendBrandWidth = 0
    gRecvBrandWidth = 0
    # last_rdata_len = 0
    # last_wdata_len = 0
    while True:
        gSendBrandWidth = now_wdata_len# - last_wdata_len
        gRecvBrandWidth = now_rdata_len# - last_rdata_len
        # last_wdata_len = now_wdata_len
        # last_rdata_len = now_rdata_len
        now_rdata_len = 0
        now_wdata_len = 0
        
        print(f'接收带宽：{gRecvBrandWidth!r}')
        print(f'发送带宽：{gSendBrandWidth!r}')
        await asyncio.sleep(1)

async def localConsole(ws, path):
    global gRecvBrandWidth
    global gSendBrandWidth
    try:
        while True:
            await asyncio.sleep(1)
            msg = await ws.send(f'{gSendBrandWidth} {gRecvBrandWidth}')
    except websockets.exceptions.ConnectionClosedError as exc:
        log.error(f'exc')
    except websockets.exceptions.ConnectionClosedOK as exc:
        log.error(f'exc')
    except Exception:
        log.error(f'{traceback.format_exc()}')
        exit(1)

async def main():
    global now_rdata_len
    global now_wdata_len
    print('local started')
    asyncio.create_task(clacbrandwidth())
    ws_server = await websockets.serve(localConsole, '127.0.0.1', int(sys.argv[4]))

    if sys.argv[1]=='-l':
        print('serving on 127.0.0.1:8080')
        my_tcp = await asyncio.start_server(handle_tcp, '127.0.0.1', int(sys.argv[5]))
        async with my_tcp:
            await my_tcp.serve_forever()
    else:
        option = sys.argv[1]
        name = sys.argv[2]
        password = sys.argv[3]
        if option == '-s':
            data0 = struct.pack("!B",0)#sign in
        reader_out, writer_out = await asyncio.open_connection('127.0.0.1', 6666)
        data0 += struct.pack("!B",len(name))+name.encode()+struct.pack("!B",len(password))+password.encode()
        writer_out.write(data0)
        now_wdata_len += len(data0)
        
        await writer_out.drain()
        data1=''
        
        data1 = await reader_out.read(1024)
        now_rdata_len += len(data1)

        flag = struct.unpack("!B",data1[0:1])[0]
        
        if flag == 0:
            print('sign success')
if __name__ == 'main':
    log = logging.getLogger(__file__)
asyncio.run(main())
```

localGui.py

```python
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebSockets import *
import sys,logging,traceback

class Window(QWidget):
    #def __init__(self, parent=None):
    def __init__(self):
        super().__init__()
        #QDialog.__init__(self, parent)

        self.resize(750, 750)
        self.move(1000, 200)

        self.sendBandwidthLabel = QLabel(self)
        self.sendBandwidthLabel.setText('发送带宽')
        self.sendBandwidthLabel.resize(500,30)
        self.sendBandwidthLabel.move(250,0)
        self.sendBandwidthLabel.setStyleSheet("color: rgb(0, 0, 0);background-color: white")

        self.recvBandwidthLabel = QLabel(self)
        self.recvBandwidthLabel.setText('接收带宽')
        self.recvBandwidthLabel.resize(500,30)
        self.recvBandwidthLabel.move(250,40)
        self.recvBandwidthLabel.setStyleSheet("color: rgb(0, 0, 0);background-color: white")

        self.consolePortlabel = QLabel(self)
        self.consolePortlabel.setText('console port')
        self.consolePortlabel.move(0,0)
        self.consolePortLine = QLineEdit(self)
        self.consolePortLine.move(0,30)
        self.consolePortLine.setText('')

        self.listenPortlabel = QLabel(self)
        self.listenPortlabel.setText('listen Port')
        self.listenPortlabel.move(0,60)
        self.listenPortLine = QLineEdit(self)
        self.listenPortLine.move(0,90)
        self.listenPortLine.setText('')

        self.usernamelabel = QLabel(self)
        self.usernamelabel.setText('user name')
        self.usernamelabel.move(0,120)
        self.usernameLine = QLineEdit(self)
        self.usernameLine.move(0,150)
        self.usernameLine.setText('')

        self.passwordlabel = QLabel(self)
        self.passwordlabel.setText('password')
        self.passwordlabel.move(0,180)
        self.passwordLine = QLineEdit(self)
        self.passwordLine.move(0,210)
        self.passwordLine.setText('')
        self.passwordLine.setEchoMode(QLineEdit.Password)

        self.startBtn = QPushButton(self)
        self.startBtn.move(0,250)
        self.startBtn.setText('start button')

        self.startBtn.clicked.connect(self.startClicked)

        # 上面为界面布局
        
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.finished.connect(self.processFinished)
        self.process.started.connect(self.processStarted)
        self.process.readyReadStandardOutput.connect(self.processReadyRead)
        
    def processReadyRead(self): 
        data = self.process.readAll()
        
        try:
            print(data.data().strip())
        except Exception as exc:
            log.error(f'{traceback.format_exc()}')
            exit(1)
        
    def processStarted(self):
        process = self.sender()
        processId = process.processId()
        print('pid = ',processId)
        log.debug(f'pid={processId}')
        self.startBtn.setText('Stop')
        # self.processIdLine.setText(str(processId))

        self.websocket = QWebSocket()
        self.websocket.connected.connect(self.websocketConnected)
        self.websocket.disconnected.connect(self.websocketDisconnected)
        
        try:
            self.websocket.open(QUrl(f'ws://127.0.0.1:{self.consolePortLine.text()}/'))
            self.websocket.textMessageReceived.connect(self.websocketMsgRcvd)
            print('conn')
        except:
            print('conn err')
        
    def processFinished(self):
        self.process.kill()

    def startClicked(self):
        btn = self.sender()
        text = btn.text().lower()
        if text.startswith('start'):
            listenPort = self.listenPortLine.text()
            username = self.usernameLine.text()
            password = self.passwordLine.text()
            consolePort = self.consolePortLine.text()
            cmdLine = 'python local.py -l ' + username + ' '+  password + ' ' + consolePort + ' ' + listenPort
            print(cmdLine)
            log.debug(f'cmd={cmdLine}')
            self.process.start(cmdLine)
        else:
            self.process.kill()

    def websocketConnected(self):
        pass
        # self.websocket.sendTextMessage('secret')

    def websocketDisconnected(self):
        self.process.kill()

    def websocketMsgRcvd(self, msg):
        print('recved msg')
        log.debug(f'msg={msg}')
        sendBandwidth, recvBandwidth, *_= msg.split()
        print(sendBandwidth, recvBandwidth)
        nowTime = QDateTime.currentDateTime().toString('hh:mm:ss')
        self.sendBandwidthLabel.setText(f'发送带宽：{nowTime} {sendBandwidth}')
        self.recvBandwidthLabel.setText(f'接收带宽：{nowTime} {recvBandwidth}')

def main():
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    log = logging.getLogger(__file__)
    main()
```

remote.py

```python
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
```

remoteRest.py

```python
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
```

