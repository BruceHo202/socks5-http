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
    reader_out, writer_out = await asyncio.open_connection('117.179.135.111', 6666)
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
        reader_out, writer_out = await asyncio.open_connection('117.179.135.111', 6666)
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