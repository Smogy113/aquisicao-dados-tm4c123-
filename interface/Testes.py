import sys, serial, time
from threading import Thread
from queue import Queue
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import *
from PyQt6.QtCore import QTimer, Qt
import pyqtgraph as pg
import pandas as pd


class Interface(QWidget):
    """
    Interface gráfica para leitura serial e plotagem em tempo real.

    Principais responsabilidades:
    - Gerenciar conexão serial (abrir/fechar/escrever)
    - Ler dados da serial em uma thread separada para não travar a GUI
    - Empilhar (linha, timestamp) em uma fila threadsafe
    - Consumir a fila no thread da GUI via QTimer e atualizar buffers
    - Plotar os dados com pyqtgraph e permitir exportar o histórico para CSV
    """

    def __init__(self):
        super().__init__()
        # --- Variáveis de controle e estado ---
        self.indicador = 0         # indicador simples de estado de leitura
        self.lendo = False         # flag para saber se estamos lendo/consumindo
        self.intervalo = 0.1       # intervalo de leitura (segundos)
        self.ser = None            # objeto Serial (pyserial)
        # últimos valores recebidos (strings/temporários)
        self.tensao0 = self.tensao1 = self.tensao2 = self.tensao3 = 0.0
        self.razaociclica = 0
        self.frequencia = 0.0

        # --- Buffer e controle da thread de leitura ---
        self.buffer_serial = Queue()
        self.thread_lendo = False
        self.thread = None

        # tempo inicial para eixo X (será definido na primeira leitura)
        self.tempo_inicial = None

        # inicializa timers e interface gráfica
        self.iniciar_timer()
        self.iniciar_interface()

    def resetar_dados(self):
        self.x_tempo = []
        self.dados_tensao0 = []
        self.dados_tensao1 = []
        self.dados_tensao2 = []
        self.dados_tensao3 = []
        self.dados_frequencia = []
        self.dados_corrente0 = []
        self.dados_corrente1 = []
        self.dados_corrente2 = []
        self.dados_corrente3 = []

        self.full_x_tempo = []
        self.full_tensao0 = []
        self.full_tensao1 = []
        self.full_tensao2 = []
        self.full_tensao3 = []
        self.full_frequencia = []

        self.tempo_inicial = None

    def apagar_graficos(self):
        self.grafico0_widget.clear()
        self.grafico1_widget.clear()
        self.grafico2_widget.clear()
        self.grafico3_widget.clear()

    def iniciar_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.ler_serial)

        self.timer_graficos = QTimer()
        self.timer_graficos.timeout.connect(self.atualizar_graficos)

    def iniciar_interface(self):
        self.setWindowTitle("Projeto")
        self.setGeometry(0, 0, 1280, 800)
        self.showMaximized()

        self.grafico0_widget = pg.PlotWidget()
        self.grafico0_widget.setMaximumHeight(800)
        self.grafico1_widget = pg.PlotWidget()
        self.grafico1_widget.setMaximumHeight(800)
        self.grafico2_widget = pg.PlotWidget()
        self.grafico2_widget.setMaximumHeight(800)
        self.grafico3_widget = pg.PlotWidget()
        self.grafico3_widget.setMaximumHeight(800)

        self.fonte1 = QFont("Arial", 12)

        self.y0_label = QLabel("A0:")
        self.y0_label.setFont(self.fonte1)
        self.y1_label = QLabel("A1:")
        self.y1_label.setFont(self.fonte1)
        self.y2_label = QLabel("A2:")
        self.y2_label.setFont(self.fonte1)

        self.x0_label = QLabel("Tempo:")
        self.x0_label.setFont(self.fonte1)
        self.x1_label = QLabel("Tempo:")
        self.x1_label.setFont(self.fonte1)
        self.x2_label = QLabel("Tempo:")
        self.x2_label.setFont(self.fonte1)

        self.eixoy0_combobox = QComboBox()
        self.eixoy0_combobox.addItems(["", "A0", "A1", "A2", "A3", "Tempo"])
        self.eixoy0_combobox.setCurrentText("A0")
        self.eixoy0_corrente_combobox = QComboBox()
        self.eixoy0_corrente_combobox.addItems(["", "A0", "A1", "A2", "A3", "Tempo"])
        self.eixox0_combobox = QComboBox()
        self.eixox0_combobox.addItems(["A0", "A1", "A2", "A3", "Tempo"])
        self.eixox0_combobox.setCurrentText("Tempo")

        self.eixoy1_combobox = QComboBox()
        self.eixoy1_combobox.addItems(["", "A0", "A1", "A2", "A3", "Tempo"])
        self.eixoy1_combobox.setCurrentText("A1")
        self.eixoy1_corrente_combobox = QComboBox()
        self.eixoy1_corrente_combobox.addItems(["", "A0", "A1", "A2", "A3", "Tempo"])
        self.eixox1_combobox = QComboBox()
        self.eixox1_combobox.addItems(["A0", "A1", "A2", "A3", "Tempo"])
        self.eixox1_combobox.setCurrentText("Tempo")

        self.eixoy2_combobox = QComboBox()
        self.eixoy2_combobox.addItems(["", "A0", "A1", "A2", "A3", "Tempo"])
        self.eixoy2_combobox.setCurrentText("A2")
        self.eixoy2_corrente_combobox = QComboBox()
        self.eixoy2_corrente_combobox.addItems(["", "A0", "A1", "A2", "A3", "Tempo"])
        self.eixox2_combobox = QComboBox()
        self.eixox2_combobox.addItems(["A0", "A1", "A2", "A3", "Tempo"])
        self.eixox2_combobox.setCurrentText("Tempo")

        self.intervalo_spinbox = QDoubleSpinBox()
        self.intervalo_spinbox.setDecimals(2)
        self.intervalo_spinbox.setValue(0.01)
        self.intervalo_spinbox.setRange(0.01, 99999)
        self.intervalo_label = QLabel("Intervalo(s):")

        self.intervalo_botao = QPushButton("Atualizar")
        self.intervalo_botao.clicked.connect(self.set_intervalo)

        self.razaociclica_slider = QSlider(Qt.Orientation.Horizontal)
        self.razaociclica_slider.setValue(50)
        self.razaociclica_slider.sliderReleased.connect(self.set_razaociclica)
        self.razaociclica_slider.valueChanged.connect(lambda x: self.razaociclica_label.setText(f"Razão Cíclica: {self.razaociclica_slider.value()}%"))
        self.razaociclica_slider.setRange(0,100)

        self.frequencia_slider = QSlider(Qt.Orientation.Horizontal)
        self.frequencia_slider.setValue(100)
        self.frequencia_slider.sliderReleased.connect(self.set_frequencia)
        self.frequencia_slider.valueChanged.connect(lambda x: self.frequencia_label.setText(f"Frequencia: {self.frequencia_slider.value()}Hz"))
        self.frequencia_slider.setRange(1,10000)

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
        self.porta_line.setText("COM5")
        self.porta_botao = QPushButton("Alterar porta")
        self.porta_botao.setFont(self.fonte1)
        self.porta_botao.clicked.connect(self.iniciar_serial)

        self.baudrate_line = QLineEdit()
        self.baudrate_line.setText("115200") # ATENÇÃO: Mudei para 115200 para casar com o C!

        self.intervalodebug_label = QLabel("Intervalo atual: 0,1s")
        self.atualizacao_label = QLabel("                                     Atualizar gráfico a cada: ")
        self.atualizacao_doubleSpinbox = QDoubleSpinBox()
        self.atualizacao_doubleSpinbox.setDecimals(4)
        self.atualizacao_doubleSpinbox.setValue(0.1)
        self.atualizacao_doubleSpinbox.setRange(0.0001, 99999)
        self.atualizacao_doubleSpinbox.valueChanged.connect(
            lambda _: self.timer_graficos.start(int(self.atualizacao_doubleSpinbox.value() * 1000))
            if self.timer_graficos.isActive() else None
        )
        self.atualizacao_label2 = QLabel("segundo(s)")
        self.maxpontos_label = QLabel("       Quantidade máxima de pontos no gráfico:")
        self.maxpontos_spinbox = QSpinBox()
        self.maxpontos_spinbox.setRange(1, 100000000)
        self.maxpontos_spinbox.setValue(1000)

        self.erro_label = QLabel()

        layout_vertical0 = QVBoxLayout()
        layout_vertical0.addWidget(self.grafico0_widget)
        layout_vertical0.addWidget(self.y0_label)
        layout_vertical0.addWidget(self.x0_label)
        layout_vertical0.addWidget(self.eixoy0_combobox)
        layout_vertical0.addWidget(self.eixoy0_corrente_combobox)
        layout_vertical0.addWidget(self.eixox0_combobox)

        layout_vertical1 = QVBoxLayout()
        layout_vertical1.addWidget(self.grafico1_widget)
        layout_vertical1.addWidget(self.y1_label)
        layout_vertical1.addWidget(self.x1_label)
        layout_vertical1.addWidget(self.eixoy1_combobox)
        layout_vertical1.addWidget(self.eixoy1_corrente_combobox)
        layout_vertical1.addWidget(self.eixox1_combobox)

        layout_vertical2 = QVBoxLayout()
        layout_vertical2.addWidget(self.grafico2_widget)
        layout_vertical2.addWidget(self.y2_label)
        layout_vertical2.addWidget(self.x2_label)
        layout_vertical2.addWidget(self.eixoy2_combobox)
        layout_vertical2.addWidget(self.eixoy2_corrente_combobox)
        layout_vertical2.addWidget(self.eixox2_combobox)

        layout_vertical3 = QVBoxLayout()
        layout_vertical3.addWidget(self.grafico3_widget)
        layout_horizontal0 = QHBoxLayout()
        layout_horizontal0.addWidget(self.intervalo_label)
        layout_horizontal0.addWidget(self.intervalo_spinbox)
        layout_horizontal0.addWidget(self.intervalo_botao)
        layout_vertical3.addLayout(layout_horizontal0)

        layout_horizontal1 = QHBoxLayout()
        layout_horizontal1.addLayout(layout_vertical0)
        layout_horizontal1.addLayout(layout_vertical1)
        layout_horizontal1.addLayout(layout_vertical2)
        layout_horizontal1.addLayout(layout_vertical3)

        layout_vertical6 = QVBoxLayout()
        layout_horizontal2 = QHBoxLayout()
        layout_horizontal2.addWidget(self.leitura_botao)
        layout_horizontal2.setContentsMargins(0, 50, 0, 0)
        layout_horizontal2.addWidget(self.csv_botao)
        layout_vertical6.addLayout(layout_horizontal2)
        layout_vertical6.addWidget(self.pausar_botao)

        layout_vertical4 = QVBoxLayout()
        layout_vertical4.setContentsMargins(0, 50, 0, 0)
        layout_vertical4.addWidget(self.razaociclica_slider)
        layout_vertical4.addWidget(self.razaociclica_label)

        layout_vertical5 = QVBoxLayout()
        layout_vertical5.setContentsMargins(0, 50, 0, 0)
        layout_vertical5.addWidget(self.frequencia_slider)
        layout_vertical5.addWidget(self.frequencia_label)

        layout_horizontal3 = QHBoxLayout()
        layout_horizontal3.addLayout(layout_vertical6)
        layout_horizontal3.addLayout(layout_vertical4)
        layout_horizontal3.addLayout(layout_vertical5)

        self.layout_vertical = QVBoxLayout()
        layout_vertical0.setContentsMargins(0, 0, 0, 0)
        layout_vertical1.setContentsMargins(0, 0, 0, 0)
        layout_vertical2.setContentsMargins(0, 0, 0, 0)
        layout_vertical3.setContentsMargins(0, 0, 0, 0)
        layout_horizontal3.setContentsMargins(0, 0, 0, 30)

        self.layout_debugHorizontal = QHBoxLayout()
        self.layout_debugHorizontal.setContentsMargins(0, 0, 0, 0)
        self.layout_debugHorizontal.addWidget(self.intervalodebug_label)
        self.layout_debugHorizontal.addWidget(self.atualizacao_label)
        self.layout_debugHorizontal.addWidget(self.atualizacao_doubleSpinbox)
        self.layout_debugHorizontal.addWidget(self.atualizacao_label2)
        self.layout_debugHorizontal.addWidget(self.maxpontos_label)
        self.layout_debugHorizontal.addWidget(self.maxpontos_spinbox)

        self.layout_vertical.addLayout(layout_horizontal1)
        self.layout_vertical.addLayout(layout_horizontal3)
        self.layout_vertical.addWidget(self.porta_line)
        self.layout_vertical.addWidget(self.baudrate_line)
        self.layout_vertical.addWidget(self.porta_botao)
        self.layout_vertical.addLayout(self.layout_debugHorizontal)
        self.layout_vertical.addWidget(self.erro_label)

        self.setLayout(self.layout_vertical)

    def iniciar_serial(self):
        try:
            if self.ser is not None:
                try:
                    self.ser.close()
                except Exception:
                    pass
            self.ser = serial.Serial(self.porta_line.text(), int(self.baudrate_line.text()), timeout=0.1)
            self.erro_label.setText("")
            self.leitura_botao.setEnabled(True)

            time.sleep(2)
            self.set_razaociclica()
            time.sleep(1)
            self.set_frequencia()
            time.sleep(1)
            self.set_intervalo()

        except serial.serialutil.SerialException as e:
            self.ser = None
            self.leitura_botao.setEnabled(False)
            self.erro_label.setText(f"{e}")
            print(f"Erro: {e}")

    def exportar_csv(self):
        if not getattr(self, "full_x_tempo", []):
            QMessageBox.warning(self, "Exportar CSV", "Não há dados para exportar.")
            return

        nome_arquivo, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Arquivo CSV",
            "",
            "Arquivos CSV (*.csv);;Todos os Arquivos (*)"
        )

        if nome_arquivo:
            try:
                dados = {
                    "Tempo": self.full_x_tempo,
                    "A0_Tensao": self.full_tensao0,
                    "A1_Tensao": self.full_tensao1,
                    "A2_Tensao": self.full_tensao2,
                    "A3_Tensao": self.full_tensao3,
                    "A0_Corrente": [v * 0.008 for v in self.full_tensao0],
                    "A1_Corrente": [v * 0.008 for v in self.full_tensao1],
                    "A2_Corrente": [v * 0.008 for v in self.full_tensao2],
                    "A3_Corrente": [v * 0.008 for v in self.full_tensao3],
                    "Frequencia": self.full_frequencia,
                }

                df = pd.DataFrame(dados)
                df.to_csv(nome_arquivo, index=False, sep=';', decimal=',')
                QMessageBox.information(self, "Exportar CSV", f"Dados exportados com sucesso para:\n{nome_arquivo}")

            except Exception as e:
                QMessageBox.critical(self, "Erro ao Exportar", f"Não foi possível salvar o arquivo:\n{e}")

    # --- INÍCIO DAS FUNÇÕES ALTERADAS PARA O PROTOCOLO ---

    def set_razaociclica(self):
        """Envia comando 'i0' + valor + '\n' para alterar Duty Cycle"""
        try:
            if self.ser and self.ser.is_open:
                comando = f"i0{self.razaociclica_slider.value()}\n"
                self.ser.write(comando.encode())
        except Exception as e:
            print(f"Erro ao razaoCiclica: {e}")

    def set_frequencia(self):
        """Envia comando 'i1' + valor + '\n' para alterar Frequência"""
        try:
            if self.ser and self.ser.is_open:
                comando = f"i1{self.frequencia_slider.value()}\n"
                self.ser.write(comando.encode())
        except Exception as e:
            print(f"Erro ao enviar frequencia: {e}")

    def set_intervalo(self):
        """Envia comando 'i2' + valor + '\n' para alterar Intervalo"""
        self.intervalo = self.intervalo_spinbox.value()
        self.intervalodebug_label.setText(f"Intervalo atual: {self.intervalo}s")
        if self.timer.isActive():
            self.timer.start(int(self.intervalo * 1000))
        try:
            if self.ser and self.ser.is_open:
                comando = f"i2{self.intervalo_spinbox.value()}\n"
                self.ser.write(comando.encode())
        except Exception as e:
            print(f"Erro ao enviar intervalo: {e}")

    # --- FIM DAS FUNÇÕES ALTERADAS PARA O PROTOCOLO ---

    def alternar_leitura(self):
        if not self.lendo:
            self.iniciar_serial()
            self.resetar_dados()
            self.pausar_botao.setEnabled(True)
            self.comecar_ler()
        else:
            self.parar_ler()
            try:
                if self.ser:
                    self.ser.close()
            except Exception:
                pass

    def comecar_ler(self):
        if not self.ser or not self.ser.is_open:
            self.iniciar_serial()
            if not self.ser:
                return

        self.lendo = True
        self.indicador = 1

        self.thread_lendo = True
        self.thread = Thread(target=self._leitura_thread, daemon=True)
        self.thread.start()

        self.timer.start(int(self.intervalo * 1000))
        self.timer_graficos.start(int(self.atualizacao_doubleSpinbox.value() * 1000))

        self.leitura_botao.setText("Parar Leitura")

    def parar_ler(self):
        self.lendo = False
        self.indicador = 0

        self.thread_lendo = False
        self.timer.stop()
        self.timer_graficos.stop()

        self.leitura_botao.setText("Iniciar Leitura")
        self.pausar_botao.setText("Pausar Leitura")

    def pausar_ler(self):
        if self.lendo:
            self.timer.stop()
            self.timer_graficos.stop()

            self.lendo = False
            self.pausar_botao.setText("Retomar Leitura")
        else:
            self.timer.start(int(self.intervalo * 1000))
            self.timer_graficos.start(int(self.atualizacao_doubleSpinbox.value() * 1000))
            self.lendo = True
            self.pausar_botao.setText("Pausar Leitura")

    def _leitura_thread(self):
        try:
            while self.thread_lendo and self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting:
                        linha = self.ser.readline().decode('utf-8', errors='ignore').strip()
                        if linha:
                            self.buffer_serial.put((linha, time.time()))
                    else:
                        time.sleep(0.001)
                except Exception:
                    time.sleep(0.01)
        finally:
            pass

    def ler_serial(self):
        if self.buffer_serial.empty():
            return

        last = None
        while not self.buffer_serial.empty():
            try:
                last = self.buffer_serial.get_nowait()
            except Exception:
                last = None

        if last:
            last_line, timestamp = last
            try:
                parts = last_line.split()
                if len(parts) >= 5:
                    self.tensao0, self.tensao1, self.tensao2, self.tensao3, self.frequencia = parts[:5]
                    self.atualizar_dados(timestamp=timestamp)
            except Exception as e:
                print("Erro ao processar linha do buffer:", e)

    def atualizar_dados(self, timestamp=None):
        try:
            if timestamp is None:
                timestamp = time.time()

            if self.tempo_inicial is None:
                self.tempo_inicial = timestamp

            tempo_relativo = round(timestamp - self.tempo_inicial, 5)

            self.x_tempo.append(tempo_relativo)
            self.dados_tensao0.append(float(self.tensao0))
            self.dados_tensao1.append(float(self.tensao1))
            self.dados_tensao2.append(float(self.tensao2))
            self.dados_tensao3.append(float(self.tensao3))
            self.dados_frequencia.append(float(self.frequencia))

            self.dados_corrente0.append(float(self.tensao0) * 0.008)
            self.dados_corrente1.append(float(self.tensao1) * 0.008)
            self.dados_corrente2.append(float(self.tensao2) * 0.008)
            self.dados_corrente3.append(float(self.tensao3) * 0.008)

            self.max_pontos = self.maxpontos_spinbox.value()
            if len(self.x_tempo) > self.max_pontos:
                self.x_tempo = self.x_tempo[-self.max_pontos:]
                self.dados_tensao0 = self.dados_tensao0[-self.max_pontos:]
                self.dados_tensao1 = self.dados_tensao1[-self.max_pontos:]
                self.dados_tensao2 = self.dados_tensao2[-self.max_pontos:]
                self.dados_tensao3 = self.dados_tensao3[-self.max_pontos:]
                self.dados_corrente0 = self.dados_corrente0[-self.max_pontos:]
                self.dados_corrente1 = self.dados_corrente1[-self.max_pontos:]
                self.dados_corrente2 = self.dados_corrente2[-self.max_pontos:]
                self.dados_corrente3 = self.dados_corrente3[-self.max_pontos:]
                self.dados_frequencia = self.dados_frequencia[-self.max_pontos:]

            self.full_x_tempo.append(tempo_relativo)
            self.full_tensao0.append(float(self.tensao0))
            self.full_tensao1.append(float(self.tensao1))
            self.full_tensao2.append(float(self.tensao2))
            self.full_tensao3.append(float(self.tensao3))
            self.full_frequencia.append(float(self.frequencia))

        except Exception as e:
            print("atualizar_dados:", e)

    def atualizar_graficos(self):
        if not hasattr(self, "x_tempo"):
            return

        x_tempo = self.x_tempo[:]

        eixos = {
            "A0": self.dados_tensao0,
            "A1": self.dados_tensao1,
            "A2": self.dados_tensao2,
            "A3": self.dados_tensao3,
            "Tempo": x_tempo,
            "": []
        }

        eixos_corrente = {
            "A0": self.dados_corrente0,
            "A1": self.dados_corrente1,
            "A2": self.dados_corrente2,
            "A3": self.dados_corrente3,
            "Tempo": x_tempo,
            "": []
        }

        def ultimo_valor(key, mapping):
            arr = mapping.get(key, [])
            return arr[-1] if arr else "N/A"

        try:
            y0_text = ultimo_valor(self.eixoy0_combobox.currentText(), eixos)
            y1_text = ultimo_valor(self.eixoy1_combobox.currentText(), eixos)
            y2_text = ultimo_valor(self.eixoy2_combobox.currentText(), eixos)

            self.y0_label.setText(f"{self.eixoy0_combobox.currentText()}: {y0_text}")
            self.y1_label.setText(f"{self.eixoy1_combobox.currentText()}: {y1_text}")
            self.y2_label.setText(f"{self.eixoy2_combobox.currentText()}: {y2_text}")

            x0_text = ultimo_valor(self.eixox0_combobox.currentText(), eixos)
            x1_text = ultimo_valor(self.eixox1_combobox.currentText(), eixos)
            x2_text = ultimo_valor(self.eixox2_combobox.currentText(), eixos)

            self.x0_label.setText(f"{self.eixox0_combobox.currentText()}: {x0_text}")
            self.x1_label.setText(f"{self.eixox1_combobox.currentText()}: {x1_text}")
            self.x2_label.setText(f"{self.eixox2_combobox.currentText()}: {x2_text}")

            def alinhar_xy(x_arr, y_arr):
                if not x_arr or not y_arr:
                    return None, None
                n = min(len(x_arr), len(y_arr))
                return x_arr[:n], y_arr[:n]

            x_corr0, y_corr0 = alinhar_xy(
                eixos_corrente.get(self.eixox0_combobox.currentText(), []),
                eixos_corrente.get(self.eixoy0_corrente_combobox.currentText(), [])
            )
            x_ten0, y_ten0 = alinhar_xy(
                eixos.get(self.eixox0_combobox.currentText(), []),
                eixos.get(self.eixoy0_combobox.currentText(), [])
            )

            x_corr1, y_corr1 = alinhar_xy(
                eixos_corrente.get(self.eixox1_combobox.currentText(), []),
                eixos_corrente.get(self.eixoy1_corrente_combobox.currentText(), [])
            )
            x_ten1, y_ten1 = alinhar_xy(
                eixos.get(self.eixox1_combobox.currentText(), []),
                eixos.get(self.eixoy1_combobox.currentText(), [])
            )

            x_corr2, y_corr2 = alinhar_xy(
                eixos_corrente.get(self.eixox2_combobox.currentText(), []),
                eixos_corrente.get(self.eixoy2_corrente_combobox.currentText(), [])
            )
            x_ten2, y_ten2 = alinhar_xy(
                eixos.get(self.eixox2_combobox.currentText(), []),
                eixos.get(self.eixoy2_combobox.currentText(), [])
            )

            x_freq, y_freq = alinhar_xy(eixos.get("Tempo", []), self.dados_frequencia)

            self.apagar_graficos()

            if x_corr0 is not None and y_corr0 is not None:
                self.grafico0_widget.plot(x_corr0, y_corr0, pen='b')
            if x_ten0 is not None and y_ten0 is not None:
                self.grafico0_widget.plot(x_ten0, y_ten0, pen='r')

            if x_corr1 is not None and y_corr1 is not None:
                self.grafico1_widget.plot(x_corr1, y_corr1, pen='b')
            if x_ten1 is not None and y_ten1 is not None:
                self.grafico1_widget.plot(x_ten1, y_ten1, pen='r')

            if x_corr2 is not None and y_corr2 is not None:
                self.grafico2_widget.plot(x_corr2, y_corr2, pen='b')
            if x_ten2 is not None and y_ten2 is not None:
                self.grafico2_widget.plot(x_ten2, y_ten2, pen='r')

            if x_freq is not None and y_freq is not None:
                self.grafico3_widget.plot(x_freq, y_freq, pen='b')

        except Exception as e:
            print("Erro em atualizar_graficos():", e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = Interface()
    monitor.show()
    sys.exit(app.exec())