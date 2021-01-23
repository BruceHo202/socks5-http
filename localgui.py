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

        # 此处省略界面布局
        
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