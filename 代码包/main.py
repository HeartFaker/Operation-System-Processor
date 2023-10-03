import sys
# pyqt5
from PyQt5.QtCore import QRect, QThread, QMutex, QTimer
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QLabel, QTextEdit, QVBoxLayout, QHBoxLayout, QLCDNumber, \
    QLineEdit
from mainWindow import OSUi, InnerCmd,Handler

# 窗口大小设置
UI_SIZE = QRect(400, 400, 800, 1000)


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow

    # import pics_ui_rc  # 导入添加的资源（根据实际情况填写文件名）
    app = QApplication(sys.argv)

    # 开启线程
    handler = Handler()
    handler.start()

    elevators = []
    for i in range(5):
        elevators.append(InnerCmd(i))

    for elevator in elevators:
        print(elevator.eId)
        elevator.start()

    ui = OSUi()
    sys.exit(app.exec_())
