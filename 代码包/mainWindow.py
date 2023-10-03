# -*- coding: utf-8 -*-
import time
from enum import Enum
from functools import partial
from turtle import color

from PyQt5.QtCore import QRect, QTimer, QMutex, QThread
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLCDNumber, QPushButton, QLabel

# Form implementation generated from reading ui file 'mainWindow.py'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

# 窗口大小设置
UI_SIZE = QRect(200, 60, 800, 900)

# 一共五个电梯
ELEVATOR_NUM = 5
# 一共二十层楼
ELEVATOR_FLOORS = 20
# 运行一层电梯所需时间
TIME_PER_FLOOR = 1000
# 打开一扇门所需时间
DOOR_OPENING_TIME = 1000
# 门打开后维持的时间
DOOR_OPENED_TIME = 1500


# 标明电梯状态的Enum类
class EleStates(Enum):
    # 电梯故障
    malfunction = -1
    # 电梯空闲
    leisure = 0
    # 电梯上行
    upward = 1
    # 电梯下行
    downward = 2
    # 电梯正在开门
    door_opening = 3
    # 电梯已开门
    door_opened = 4
    # 电梯正在关门
    door_closing = 5

# 标明电梯上/下行状态的Enum类
class directions(Enum):
    up = 1
    down = 2


# 标明电梯外部任务三种状态的Enum类
class OuterTaskState(Enum):
    unfinished = 1
    waiting = 2
    finished = 3


# 外部任务的集合类
class OuterTasks:
    def __init__(self, floor, direction, isFinished=OuterTaskState.unfinished):
        self.floor = floor   # 电梯的目标方向
        self.direction = direction  # 需要的电梯运行方向
        self.isFinished = isFinished  # 是否完成（默认未完成）


# 全局变量
# 外部按钮产生上/下行的需求
Outer_Cmd = []
# 每组电梯的状态
Ele_States = []
# 每台电梯的当前楼层
Ele_Floor = []
# 每台电梯当前需要向上运行处理的目标
UpTargets = []
# 每台电梯当前需要向下运行处理的目标
DownTargets = []
# 每台电梯内部的开门/关门是否被按
is_open_btn_clicked = []
is_close_btn_clicked = []
# 每台电梯当前的运行状态
move_states = []

for qwerty in range(ELEVATOR_NUM):
    # inner_requests.append([])  # add list
    Ele_States.append(EleStates.leisure)  # 默认空闲
    Ele_Floor.append(1)  # 默认在1楼
    UpTargets.append([])  # 二维数组
    DownTargets.append([])  # 二维数组
    is_close_btn_clicked.append(False)  # 默认开门关门键没按
    is_open_btn_clicked.append(False)
    move_states.append(directions.up)  # 默认向上（一开始在1楼 只能向上咯

# mutex互斥锁
mutex = QMutex()


# 电梯内部按钮的处理
class InnerCmd(QThread):  # 继承Qthread
    # 构造函数
    def __init__(self, eId):
        super().__init__()  # 父类构造函数
        self.eId = eId  # 电梯编号

    # 使电梯向上/下移动一层楼
    def One_Floor(self, direction):
        # 设置本电梯状态为上/下行
        if direction == directions.up:
            Ele_States[self.eId] = EleStates.upward
        elif direction == directions.down:
            Ele_States[self.eId] = EleStates.downward

        slept_time = 0
        while slept_time != TIME_PER_FLOOR:
            # 开锁 使别的线程也能够运行
            mutex.unlock()
            self.msleep(10)
            slept_time += 10
            # 锁
            mutex.lock()
            # 故障报警
            if Ele_States[self.eId] == EleStates.malfunction:
                self.fault_execute()
                return

        # 更新内部数组的内容
        if direction == directions.up:
            Ele_Floor[self.eId] += 1
        elif direction == directions.down:
            Ele_Floor[self.eId] -= 1

        # 运行结束将电梯设置为空闲状态
        Ele_States[self.eId] = EleStates.leisure
        # 设置日程方便调试
        print(self.eId, "号在", Ele_Floor[self.eId], "楼")
        # 如果此时故障报警则跳转故障处理
        if Ele_States[self.eId] == EleStates.malfunction:
            self.fault_execute()

    # 故障处理函数
    def fault_execute(self):
        # 更新电梯状态为故障
        Ele_States[self.eId] = EleStates.malfunction
        # 更新开关门为未使用
        is_open_btn_clicked[self.eId] = False
        is_close_btn_clicked[self.eId] = False
        # 将外部任务更新为未处理，方便重新分配给其他电梯处理
        for outer_task in Outer_Cmd:
            if outer_task.isFinished == OuterTaskState.waiting:
                if outer_task.floor in UpTargets[self.eId] or outer_task.floor in DownTargets[self.eId]:
                    outer_task.isFinished = OuterTaskState.unfinished
        # 将本电梯的目标都清空
        UpTargets[self.eId] = []
        DownTargets[self.eId] = []

    # 电梯内部运行函数
    def run(self):
        while True:
            mutex.lock()
            # 如果故障报警
            if Ele_States[self.eId] == EleStates.malfunction:
                self.fault_execute()
                mutex.unlock()
                continue

            # 电梯向上运行
            if move_states[self.eId] == directions.up:
                # 向上的目标不为空
                if UpTargets[self.eId]:
                    # 因为每次都会删去已完成任务，且任务按照楼层高低已经排序，所以一直从0位读取即可
                    # 如果已经到达目标楼层
                    if UpTargets[self.eId][0] == Ele_Floor[self.eId]:
                        # self.door()
                        # 到达以后 把完成的内部任务删去
                        UpTargets[self.eId].pop(0)
                        # 如果此时恰好完成了外部任务的需求，则顺便将外部任务设置为已完成
                        for outer_task in Outer_Cmd:
                            if outer_task.floor == Ele_Floor[self.eId]:
                                outer_task.isFinished = OuterTaskState.finished
                    # 如果还没到达目标楼层
                    elif UpTargets[self.eId][0] > Ele_Floor[self.eId]:
                        self.One_Floor(directions.up)

                # 当没有上行目标而出现下行目标时 更换状态
                elif UpTargets[self.eId] == [] and DownTargets[self.eId] != []:
                    move_states[self.eId] = directions.down

            # 电梯向下运行
            elif move_states[self.eId] == directions.down:
                # 向下运行的任务不为空
                if DownTargets[self.eId]:
                    # 因为每次都会删去已完成任务，且任务按照楼层高低已经排序，所以一直从0位读取即可
                    # 如果已经到达目标楼层
                    if DownTargets[self.eId][0] == Ele_Floor[self.eId]:
                        # self.door()
                        # 到达以后 把完成的任务删去
                        DownTargets[self.eId].pop(0)
                        # 如果此时恰好完成了外部任务的需求，则顺便将外部任务设置为已完成
                        for outer_task in Outer_Cmd:
                            if outer_task.floor == Ele_Floor[self.eId]:
                                outer_task.isFinished = OuterTaskState.finished
                    # 如果还没到达目标楼层
                    elif DownTargets[self.eId][0] < Ele_Floor[self.eId]:
                        self.One_Floor(directions.down)

                # 当没有下行目标而出现上行目标时 更换状态
                elif DownTargets[self.eId] == [] and UpTargets[self.eId] != []:
                    move_states[self.eId] = directions.up

            mutex.unlock()


# 外部任务的判断算法，外部任务和内部任务分开进行
class Handler(QThread):
    # 构造函数
    def __init__(self):
        super().__init__()  # 父类构造函数

    # 运行函数
    def run(self):
        while True:
            mutex.lock()
            global Outer_Cmd

            # 逐个读取外部任务进行算法研究
            for outer_task in Outer_Cmd:
                # 如果外部任务标识为未分配
                if outer_task.isFinished == OuterTaskState.unfinished:
                    min_distance = ELEVATOR_FLOORS + 1
                    target_id = -1
                    # 测试每一台电梯是否能够分配任务
                    for i in range(ELEVATOR_NUM):
                        # 保证符合要求的电梯没有故障
                        if Ele_States[i] == EleStates.malfunction:
                            continue

                        # 如果电梯正在运行状态，则需要先考虑已经需要运行的任务，同时再考虑新任务
                        # 即将本电梯的初始位置设置为位置+/- = 1
                        origin = Ele_Floor[i]
                        if Ele_States[i] == EleStates.upward:
                            origin += 1
                        elif Ele_States[i] == EleStates.downward:
                            origin -= 1

                        if move_states[i] == directions.up:
                            targets = UpTargets[i]
                        else:
                            targets = DownTargets[i]

                        # 每种外部需求具有八种情况，即：需求与电梯运行方向是否相同，在电梯上方还是下方，是否有任务三个“是否”，共2^3=8种情况
                        # 第一种情况，如果电梯空闲
                        if not targets:
                            distance = abs(origin - outer_task.floor)

                        # 第二种情况，如果电梯运行方向和外部需求方向相同
                        elif move_states[i] == outer_task.direction and \
                                ((outer_task.direction == directions.up and outer_task.floor >= origin) or
                                 (outer_task.direction == directions.down and outer_task.floor <= origin)):
                            distance = abs(origin - outer_task.floor)

                        # 其余情况则计算最远任务楼层到目标楼层的绝对值和最远楼层到当前电梯楼层的绝对值之和
                        else:
                            distance = abs(origin - targets[-1]) + abs(outer_task.floor - targets[-1])

                        # 在所有情况中寻找最小值
                        if distance < min_distance:
                            min_distance = distance
                            target_id = i

                    # 如果有符合条件的电梯，就把任务分配给它
                    if target_id != -1:
                        # 如果这一电梯已经到达目标楼层
                        if Ele_Floor[target_id] == outer_task.floor:
                            if outer_task.direction == directions.up and outer_task.floor not in UpTargets[
                                target_id] and Ele_States[target_id] != EleStates.upward:
                                UpTargets[target_id].append(outer_task.floor)
                                UpTargets[target_id].sort()
                                # 将外部任务设置为等待
                                outer_task.isFinished = OuterTaskState.waiting

                            elif outer_task.direction == directions.down and outer_task.floor not in DownTargets[
                                target_id] and Ele_States[target_id] != EleStates.downward:
                                DownTargets[target_id].append(outer_task.floor)
                                # 设置降序排列
                                DownTargets[target_id].sort(reverse=True)
                                # 设为等待态
                                outer_task.isFinished = OuterTaskState.waiting

                        # 如果电梯还在为了完成外部任务而运行
                        elif Ele_Floor[target_id] < outer_task.floor and outer_task.floor not in UpTargets[
                            target_id]:
                            UpTargets[target_id].append(outer_task.floor)
                            UpTargets[target_id].sort()
                            outer_task.isFinished = OuterTaskState.waiting

                        elif Ele_Floor[target_id] > outer_task.floor and outer_task.floor not in DownTargets[
                            target_id]:
                            DownTargets[target_id].append(outer_task.floor)
                            DownTargets[target_id].sort(reverse=True)
                            # 设为等待态
                            outer_task.isFinished = OuterTaskState.waiting

            # 移除已经完成的任务
            Outer_Cmd = [task for task in Outer_Cmd if task.isFinished != OuterTaskState.finished]

            mutex.unlock()

# UI的绘制和更新
class OSUi(QWidget):
    # 构造函数
    def __init__(self):
        super().__init__()  # 父类构造函数
        self.output = None

        # 各种需要更新的控件
        self.floor_displayers = []
        self.inner_num_btn = []
        self.inner_floor_mark = []
        self.inner_open_btn = []
        self.inner_close_btn = []
        self.inner_fault_btn = []
        self.outer_up_btn = []
        self.outer_down_btn = []

        # 定时器更新UI界面
        self.timer = QTimer()

        # 设置UI
        self.setup_ui()

    # UI绘制
    def setup_ui(self):
        # 设置窗口标题
        self.setWindowTitle("OS_Lab1_Elevator")
        # 设置窗口大小
        self.setGeometry(UI_SIZE)

        # 总页面的水平布局对象
        h1 = QHBoxLayout()
        self.setLayout(h1)

        # 水平布局对象中的竖直布局对象，用来存放五个电梯
        h2 = QHBoxLayout()
        h1.addLayout(h2)

        # 从左到右生成四个电梯
        for i in range(ELEVATOR_NUM):
            # 竖直布局对象，存放每一台电梯（显示屏，楼层，内部按键）
            v2 = QVBoxLayout()
            v2.setContentsMargins(10, 10, 10, 10)
            # 将竖直布局对象添加到水平布局对象中
            h2.addLayout(v2)

            # 电梯上方的LCD显示屏
            floor_display = QLCDNumber()
            floor_display.setFixedSize(150, 30)
            floor_display.setStyleSheet("background-color:black")
            self.floor_displayers.append(floor_display)
            v2.addWidget(floor_display)
            self.inner_num_btn.append([])
            self.inner_floor_mark.append([])

            # 设置竖直的每层
            for j in range(ELEVATOR_FLOORS):

                # 设置水平布局对象，用来存放每个楼层和它对应的楼层按钮
                floor = QHBoxLayout()
                # 内部数字按键
                btn = QPushButton()
                btn.setFixedSize(150, 35)
                btn.setStyleSheet("background-color : rgb(255,255,255)")
                self.inner_num_btn[i].append(btn)
                floor.addWidget(btn)

                mark = QPushButton(str(ELEVATOR_FLOORS - j))  # 因为控件是从上到下依次生成
                mark.setFixedSize(35, 35)
                mark.clicked.connect(partial(self.inner_floor_mark_clicked, i, ELEVATOR_FLOORS - j))
                mark.setStyleSheet("border-radius: 25px")
                mark.setStyleSheet("background-color : rgb(255,255,255)")
                self.inner_floor_mark[i].append(mark)
                floor.addWidget(mark)

                # 将水平布局对象添加到v2中
                v2.addLayout(floor)

            # 设置一个水平布局对象存放“报警”。“开门”和“关门”三个按钮
            h_fod_btn = QHBoxLayout()
            # 故障按钮
            fault_btn = QPushButton("报警")
            fault_btn.setFixedSize(45, 30)
            fault_btn.clicked.connect(partial(self.inner_fault_btn_clicked, i))
            self.inner_fault_btn.append(fault_btn)
            h_fod_btn.addWidget(fault_btn)

            # 开门按钮
            open_button = QPushButton("开门")
            open_button.setFixedSize(45, 30)
            # open_button.clicked.connect(partial(self.inner_open_btn_clicked, i))
            self.inner_open_btn.append(open_button)
            h_fod_btn.addWidget(open_button)

            # 关门按钮
            close_button = QPushButton("关门")
            close_button.setFixedSize(45, 30)
            # close_button.clicked.connect(partial(self.inner_close_btn_clicked, i))
            self.inner_close_btn.append(close_button)

            h_fod_btn.addWidget(close_button)
            v2.addLayout(h_fod_btn)

        # 设置电梯每一层的上下呼叫键
        v3 = QVBoxLayout()

        btn = QPushButton("上下行")
        btn.setFixedSize(80, 40)
        v3.addWidget(btn)

        h1.addLayout(v3)

        # 对每个楼层，放置上下行和外部电梯呼唤按钮
        for i in range(ELEVATOR_FLOORS):
            h4 = QHBoxLayout()
            v3.addLayout(h4)

            if i != 0:
                # 给2楼到顶楼放置上行按钮，因为顶楼不能再上行，所以不需要上行按钮
                up_btn = QPushButton("↑")
                up_btn.setFixedSize(25, 25)
                up_btn.clicked.connect(partial(self.outer_direction_btn_clicked, ELEVATOR_FLOORS - i, directions.up))
                self.outer_up_btn.append(up_btn)  # 从顶楼往下一楼开始..
                h4.addWidget(up_btn)
            elif i == 0:
                x_btn = QPushButton("X")
                x_btn.setFixedSize(25, 25)
                h4.addWidget(x_btn)

            if i != ELEVATOR_FLOORS - 1:
                # 给1楼到顶楼往下一楼放置下行按钮，1楼不需要下行，不需要下行按钮
                down_btn = QPushButton("↓")
                down_btn.setFixedSize(25, 25)
                down_btn.clicked.connect(
                    partial(self.outer_direction_btn_clicked, ELEVATOR_FLOORS - i, directions.down))
                self.outer_down_btn.append(down_btn)  # 从顶楼开始..到2楼
                h4.addWidget(down_btn)
            elif i == ELEVATOR_FLOORS - 1:
                x_btn = QPushButton("X")
                x_btn.setFixedSize(25, 25)
                h4.addWidget(x_btn)

            label = QLabel(str(ELEVATOR_FLOORS - i))
            h4.addWidget(label)

        btn = QPushButton("----")
        btn.setFixedSize(80, 40)
        v3.addWidget(btn)

        # 设置定时
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.update)
        self.timer.start()

        self.show()

    # 如果电梯内部楼层按钮被点击
    def inner_floor_mark_clicked(self, eId, floor):
        mutex.lock()
        if Ele_States[eId] == EleStates.malfunction:  # 如果电梯故障
            mutex.unlock()
            return
        elif Ele_Floor[eId] == floor:  # 如果当前电梯已经停留在目标楼层，开门
            self.inner_open_btn[eId].setStyleSheet("background-color : blue")
            mutex.unlock()
            return

        # 添加任务
        if Ele_States[eId] != EleStates.malfunction:
            if floor > Ele_Floor[eId] and floor not in UpTargets[eId]:
                UpTargets[eId].append(floor)
                UpTargets[eId].sort()
            elif floor < Ele_Floor[eId] and floor not in DownTargets[eId]:
                DownTargets[eId].append(floor)
                DownTargets[eId].sort(reverse=True)  # 電梯下行時降序

        mutex.unlock()
        self.inner_floor_mark[eId][ELEVATOR_FLOORS - floor].setStyleSheet("background-color : yellow")

    # 如果电梯内部报警按钮被点击，分为按钮已生效->未生效和按钮未生效->生效两种状态
    # 此处本想用win32api进行弹窗提示，但是发现这一功能在多线程中使用可能会出现错误
    def inner_fault_btn_clicked(self, eId):
        mutex.lock()
        if Ele_States[eId] == EleStates.malfunction:  # 如果电梯故障
            self.inner_fault_btn[eId].setStyleSheet("background-color : none")
            Ele_States[eId] = EleStates.leisure
            mutex.unlock()
            return
        else:
            Ele_States[eId] = EleStates.leisure  # 如果电梯未故障
            self.inner_fault_btn[eId].setStyleSheet("background-color : red")
            Ele_States[eId] = EleStates.malfunction
            for button in self.inner_num_btn[eId]:
                button.setStyleSheet("background-color : rgb(255,255,255)")
            mutex.unlock()
            return

    # 如果点击了外部的电梯呼唤按钮
    def outer_direction_btn_clicked(self, floor, move_state):
        mutex.lock()

        all_fault = True
        for i in EleStates:
            if i != EleStates.malfunction:
                all_fault = False

        if all_fault:
            mutex.unlock()
            return

        task = OuterTasks(floor, move_state)

        if task not in Outer_Cmd:
            Outer_Cmd.append(task)

        mutex.unlock()

    # 按照固定周期更新UI
    def update(self):
        mutex.lock()
        # 更新每一个电梯
        for i in range(ELEVATOR_NUM):
            # 实时更新楼层
            if Ele_States[i] == EleStates.upward:
                self.floor_displayers[i].display("↑" + str(Ele_Floor[i]))
            elif Ele_States[i] == EleStates.downward:
                self.floor_displayers[i].display("↓" + str(Ele_Floor[i]))
            else:
                self.floor_displayers[i].display(Ele_Floor[i])

            # 实时更新开关门按钮
            if not is_open_btn_clicked[i]:
                self.inner_open_btn[i].setStyleSheet("background-color : None")

            if not is_close_btn_clicked[i]:
                self.inner_close_btn[i].setStyleSheet("background-color : None")


            self.inner_floor_mark[i][ELEVATOR_FLOORS - Ele_Floor[i]].setStyleSheet(
                    "background-color : rgb(255, 255 ,255)")

            # 标明电梯位置
            for j in range(ELEVATOR_FLOORS):
                if j == Ele_Floor[i]:
                    self.inner_num_btn[i][ELEVATOR_FLOORS - j].setStyleSheet("background-color : RGB(245, 245, 245)")
                elif j == 0:
                    self.inner_num_btn[i][ELEVATOR_FLOORS - j - 1].setStyleSheet("background-color : rgb(255, 255 ,255)")
                else:
                    self.inner_num_btn[i][ELEVATOR_FLOORS - j].setStyleSheet("background-color : rgb(255, 255, 255)")

        mutex.unlock()

        # 外侧上下楼呼叫电梯按钮
        for button in self.outer_up_btn:
            button.setStyleSheet("background-color : None")

        for button in self.outer_down_btn:
            button.setStyleSheet("background-color : None")

        mutex.lock()
        for outer_task in Outer_Cmd:
            if outer_task.isFinished != OuterTaskState.finished:
                if outer_task.direction == directions.up:
                    self.outer_up_btn[ELEVATOR_FLOORS - outer_task.floor - 1].setStyleSheet("background-color : yellow")
                elif outer_task.direction == directions.down:
                    self.outer_down_btn[ELEVATOR_FLOORS - outer_task.floor].setStyleSheet("background-color : yellow")
        mutex.unlock()
