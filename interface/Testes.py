import sys, serial, time
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt
import pyqtgraph as pg
import pandas


class Interface(QWidget):
    def __init__(self):
        super().__init__()
        self.indicador = 0
        self.intervalo = 0.1
        self.ser = 0
        self.frequencia =  0.0

        self.iniciar_timer()
        self.iniciar_interface()
        self.iniciar_serial()

    def atualizar_intervalo(self):
        self.intervalo = self.intervalo_spinbox.value()
        self.intervalodebug_label.setText(f"Intervalo atual: {self.intervalo_spinbox.value()}s")

    def resetar_dados(self):
        self.x_tempo = [-self.intervalo]
        self.dados_frequencia = []

    def apagar_graficos(self):
        self.grafico3_widget.clear()

    def iniciar_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.ler_serial)

    def iniciar_interface(self):
        self.setWindowTitle("Projeto")
        self.setGeometry(0,0,1980,1080)

        self.grafico3_widget = pg.PlotWidget()
        self.grafico3_widget.setMaximumHeight(600)

        self.fonte1 = QFont("Arial", 12)

        self.intervalo_spinbox = QDoubleSpinBox()
        self.intervalo_spinbox.setDecimals(15)
        self.intervalo_spinbox.setValue(0.1)
        self.intervalo_label = QLabel("Intervalo(s):")

        self.intervalo_botao = QPushButton("Atualizar")
        self.intervalo_botao.clicked.connect(self.atualizar_intervalo)

        self.razaociclica_slider = QSlider(Qt.Orientation.Horizontal)
        self.razaociclica_slider.setValue(50)
        self.razaociclica_slider.sliderReleased.connect(self.atualizar_razaociclica)
        self.razaociclica_slider.valueChanged.connect(lambda x: self.razaociclica_label.setText(f"Razão Cíclica: {self.razaociclica_slider.value()}%"))
        self.razaociclica_slider.setMaximum(100)
        self.razaociclica_slider.setMinimum(0)

        self.frequencia_slider = QSlider(Qt.Orientation.Horizontal)
        self.frequencia_slider.setValue(100)
        self.frequencia_slider.sliderReleased.connect(self.atualizar_frequencia)
        self.frequencia_slider.valueChanged.connect(
            lambda x: self.frequencia_label.setText(f"Frequencia: {self.frequencia_slider.value()}Hz"))
        self.frequencia_slider.setMaximum(10000)
        self.frequencia_slider.setMinimum(0)

        self.razaociclica_label = QLabel("Razão Cíclica: 50%")
        self.razaociclica_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frequencia_label = QLabel("Frequencia: 100Hz")
        self.frequencia_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.leitura_botao = QPushButton("Iniciar Leitura")
        self.leitura_botao.setFont(self.fonte1)
        self.leitura_botao.setMinimumWidth(300)
        self.leitura_botao.clicked.connect(self.alternar_leitura)

        self.csv_botao = QPushButton("Exportar CSV")
        self.csv_botao.setFont(self.fonte1)
        self.csv_botao.setMinimumWidth(300)
        self.csv_botao.clicked.connect(self.exportar_csv)

        self.pausar_botao = QPushButton("Pausar Leitura")
        self.pausar_botao.setFont(self.fonte1)
        self.pausar_botao.clicked.connect(self.pausar_ler)
        self.pausar_botao.setEnabled(0)

        self.porta_line = QLineEdit()
        self.porta_line.setText("/dev/ttyACM0")

        self.porta_botao = QPushButton("Definir porta")
        self.porta_botao.setFont(self.fonte1)
        self.porta_botao.clicked.connect(self.iniciar_serial)

        self.erro_label = QLabel()

        layout_vertical3 = QVBoxLayout()
        layout_vertical3.addWidget(self.grafico3_widget)
        layout_horizontal0 = QHBoxLayout()
        layout_horizontal0.addWidget(self.intervalo_label)
        layout_horizontal0.addWidget(self.intervalo_spinbox)
        layout_horizontal0.addWidget(self.intervalo_botao)
        layout_vertical3.addLayout(layout_horizontal0)

        layout_horizontal1 = QHBoxLayout()
        layout_horizontal1.addLayout(layout_vertical3)

        layout_vertical6 = QVBoxLayout()
        layout_horizontal2 = QHBoxLayout()
        layout_horizontal2.addWidget(self.leitura_botao)
        layout_horizontal2.setContentsMargins(0, 100, 0, 0)
        layout_horizontal2.addWidget(self.csv_botao)
        layout_vertical6.addLayout(layout_horizontal2)
        layout_vertical6.addWidget(self.pausar_botao)

        layout_vertical4 = QVBoxLayout()
        layout_vertical4.setContentsMargins(0, 100, 0, 0)
        layout_vertical4.addWidget(self.razaociclica_slider)
        layout_vertical4.addWidget(self.razaociclica_label)

        layout_vertical5 = QVBoxLayout()
        layout_vertical5.setContentsMargins(0, 100, 0, 0)
        layout_vertical5.addWidget(self.frequencia_slider)
        layout_vertical5.addWidget(self.frequencia_label)

        layout_horizontal3 = QHBoxLayout()
        layout_horizontal3.addLayout(layout_vertical6)
        layout_horizontal3.addLayout(layout_vertical4)
        layout_horizontal3.addLayout(layout_vertical5)


        self.layout_vertical = QVBoxLayout()
        layout_vertical3.setContentsMargins(0, 0, 0, 0)
        layout_horizontal3.setContentsMargins(0, 0, 0, 100)

        self.layout_debugHorizontal = QHBoxLayout()
        self.intervalodebug_label = QLabel("Intervalo atual: 4s")
        self.intervalopontosdebug_label = QLabel("Atualizar gráfico a cada: 2 pontos")
        self.layout_debugHorizontal.addWidget(self.intervalodebug_label)
        self.layout_debugHorizontal.addWidget(self.intervalopontosdebug_label)

        self.layout_vertical.addLayout(layout_horizontal1)
        self.layout_vertical.addLayout(layout_horizontal3)
        self.layout_vertical.addWidget(self.porta_line)
        self.layout_vertical.addWidget(self.porta_botao)
        self.layout_vertical.addLayout(self.layout_debugHorizontal)
        self.layout_vertical.addWidget(self.erro_label)

        self.setLayout(self.layout_vertical)

    def iniciar_serial(self):
        if type(self.ser) != int:
            self.ser.close()
            time.sleep(1)
        try:
            self.ser = serial.Serial(self.porta_line.text(), 57600, timeout=1)
            time.sleep(1)
            print(self.ser)
            self.layout_vertical.removeWidget(self.erro_label)
            self.erro_label.setText("")
            self.leitura_botao.setEnabled(True)
        except serial.serialutil.SerialException as e:
            self.leitura_botao.setEnabled(False)
            self.erro_label.setText(f"{e}")
            print(f"Erro: {e}")

    def exportar_csv(self):
        dados = {
             "Tempo": self.x_tempo
            }
        dataframe = pandas.DataFrame(dados)
        dataframe.to_csv("arquivo.csv", index=False)

    def atualizar_razaociclica(self):
        self.ser.write(f"pwm:{self.razaociclica_slider.value()}".encode())

    def atualizar_frequencia(self):
        self.ser.write(f"freq:{self.frequencia_slider.value()}".encode())

    def alternar_leitura(self):
        if self.indicador == 0 and not self.pausar_botao.isEnabled():
            self.iniciar_serial()
            self.apagar_graficos()
            self.resetar_dados()
            self.pausar_botao.setEnabled(1)
            self.comecar_ler()
        else:
            self.ser.close()
            self.pausar_botao.setEnabled(0)
            self.parar_ler()

    def comecar_ler(self):
        self.timer.start(int(self.intervalo * 1000))
        print(int(self.intervalo * 1000))
        self.leitura_botao.setText("Parar Leitura")
        self.m = 0

    def parar_ler(self):
        if (self.indicador == 1):
            self.indicador = 0
            self.timer.stop()
        self.pausar_botao.setText("Pausar Leitura")
        self.leitura_botao.setText("Iniciar Leitura")

    def pausar_ler(self):
        if (self.indicador == 1):
            self.indicador = 0
            self.timer.stop()
            self.pausar_botao.setText("Retornar Leitura")

        elif (self.indicador == 0):
            self.ler_serial()
            self.timer.start(int(self.intervalo * 1000))
            self.pausar_botao.setText("Pausar Leitura")
            self.m = 0

    def ler_serial(self):
        self.indicador = 1
        try:
            self.ser.write("solicitar tensao\n".encode())
            self.data = self.ser.readline().decode('utf-8')
            self.tensao0, self.tensao1, self.tensao2, self.tensao3, self.frequencia = self.data.split(",")
            print("self.frequencia:", self.frequencia)
            #print(self.tensao0, self.tensao1, self.tensao2, self.tensao3, self.frequencia)

        except  Exception as e:
            print(f"Erro: {e}")
            self.indicador = 0
        finally:
            self.atualizar_dados()

    def atualizar_dados(self):
        try:
            if self.indicador == 1:
                #self.x_tempo.append(round(self.x_tempo[-1]+self.intervalo, 5))
                self.x_tempo.append(self.x_tempo[-1]+1)
                self.dados_frequencia.append(float(self.frequencia))

                print("self.dados_frequencia", self.dados_frequencia)
                self.atualizar_graficos()
        except AttributeError as e:
            print(e)
            pass

    def atualizar_graficos(self):
        if self.x_tempo[0] == -self.intervalo:
            self.x_tempo = self.x_tempo[1:]

        self.grafico3_widget.plot(self.x_tempo, self.dados_frequencia, pen='b')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = Interface()
    monitor.show()
    sys.exit(app.exec())