import sys
import serial
import time
from PyQt6.QtCore import Qt,pyqtSignal
from PyQt6.QtGui import QPainter,QFont,QIcon
import PyQt6.QtWidgets as qt
from PyQt6 import QtSerialPort
import PyQt6.QtCore as qcore
import serial.tools.list_ports



class Dialog(qt.QDialog):
    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)
        self.setWindowTitle("Settings")
        self.setStyleSheet("background-color: rgb(255,255,224);")
        self.portname_comboBox = qt.QComboBox()
        self.baudrate_comboBox = qt.QComboBox()
        
        ports = serial.tools.list_ports.comports()
        port_names = [port.name for port in ports]
    
        for info in port_names:
            self.portname_comboBox.addItem(info)

        for baudrate in QtSerialPort.QSerialPortInfo.standardBaudRates():
            self.baudrate_comboBox.addItem(str(baudrate), baudrate)

        buttonBox = qt.QDialogButtonBox()
        buttonBox.setOrientation(qcore.Qt.Orientation.Horizontal)
        buttonBox.setStandardButtons(qt.QDialogButtonBox.StandardButton.Cancel|qt.QDialogButtonBox.StandardButton.Ok)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        lay = qt.QFormLayout(self)
        lay.addRow("Port Name:", self.portname_comboBox)
        lay.addRow("BaudRate:", self.baudrate_comboBox)
        lay.addRow(buttonBox)
        self.setFixedSize(self.sizeHint())

    def get_results(self):
        return self.portname_comboBox.currentText(), self.baudrate_comboBox.currentData()

class DisplayWidget(qt.QWidget):
    state = False
    def __init__(self, index):
        super().__init__()
        self.index = str(index)
        self.setFixedSize(32, 32)

    def setState(self, state):
        if self.state != state:
            self.state = state
            self.update()

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.setBrush(Qt.GlobalColor.green if self.state else Qt.GlobalColor.red)
        qp.drawRect(self.rect().adjusted(0, 0, -1, -1))
        qp.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.index)


class SerialViewer(qt.QWidget):
    def __init__(self, fieldCount=None):
        super().__init__()
        layout = qt.QGridLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.widgets = []

        if isinstance(fieldCount, int) and fieldCount > 0:
            self.createGrid(fieldCount)

    def createGrid(self, fieldCount, rows=2):
        while self.widgets:
            self.widgets.pop(0).deleteLater()
        rows = max(1, rows)
        count = 0
        columns, rest = divmod(fieldCount, rows)
        if rest:
            columns += 1
        for column in range(columns):
            for row in range(rows):
                widget = DisplayWidget(count)
                self.layout().addWidget(widget, row, column)
                self.widgets.append(widget)
                count += 1
                if count == fieldCount:
                    break

    def updateData(self, data):
        if len(data) != len(self.widgets):
            self.createGrid(len(data))
        for widget, state in zip(self.widgets, data):
            widget.setState(state)   


class SerialThread(qcore.QThread):
    dataReceived = pyqtSignal(object)
    def __init__(self):
        super(qcore.QThread, self).__init__()
        self.chosen_baudrate = 115200
        self.chosen_port = "COM3"
    def run(self):
        ser = serial.Serial(
            port= self.chosen_port, 
            baudrate= self.chosen_baudrate, 
            parity=serial.PARITY_NONE, 
            stopbits=serial.STOPBITS_ONE, 
            bytesize=serial.EIGHTBITS)

        self.keepRunning = True
        while self.keepRunning:
            if ser.inWaiting() > 0:
                num = ser.readline()
                line = [0]*32

                for i in range(0,32):
                    if(num&(1<<i)):
                        line[31-i] = 1
                    else:
                        line[31-i] = 0
                self.dataReceived.emit(
                    list(line) ####mogoče bo dvojni list in bo napaka, če bo samo odstrani list()
                )
            time.sleep(0.01) 


    def stop(self):
        self.keepRunning = False
        self.wait()



class MainWindow(qt.QMainWindow):
    def __init__(self):
        super().__init__()


        central = qt.QFrame()
        central.setStyleSheet("background-color: rgb(255,255,224);")
        self.setCentralWidget(central)
        self.setWindowTitle("Bee Counter")
        self.setWindowIcon(QIcon("icon.png"))

        self.configure_btn = qt.QPushButton("Configure")
        self.configure_btn.setStyleSheet("border-style: outset; border-width: 1px; border-radius: 5px; border-color: b")

        self.startButton = qt.QPushButton('Connect')
        self.startButton.setStyleSheet("border-style: outset; border-width: 1px; border-radius: 5px; border-color: b")
        self.stopButton = qt.QPushButton('Disconnect', enabled=False)
        self.stopButton.setStyleSheet("border-style: outset; border-width: 1px; border-radius: 5px; border-color: b")


        title = qt.QLabel("BEE COUNTER")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Times",30,20))
        
        
        self.serialViewer = SerialViewer(32)

        layout = qt.QGridLayout(central)
        layout.addWidget(title,0,0,1,3)
        layout.addWidget(self.startButton,1,0)
        layout.addWidget(self.stopButton, 1, 1,)
        layout.addWidget(self.configure_btn,1,2)
        layout.addWidget(self.serialViewer, 2, 0, 1, 3)
        
        self.serialThread = SerialThread()

        self.startButton.clicked.connect(self.start)
        self.stopButton.clicked.connect(self.serialThread.stop)
        self.configure_btn.clicked.connect(self.open_dialog)

        self.serialThread.dataReceived.connect(
            self.serialViewer.updateData)
        self.serialThread.finished.connect(self.stopped)

    def start(self):
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.serialThread.start()

    def stopped(self):
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    def open_dialog(self):
        dialog = Dialog()
        if dialog.exec():
            portname, baudrate = dialog.get_results()
            self.serialThread.chosen_port = portname
            self.serialThread.chosen_baudrate = baudrate


if __name__ == '__main__':
    app = qt.QApplication(sys.argv)
    app.setFont(QFont("Times",0,400))
    w = MainWindow()
    w.show()
    app.exec()