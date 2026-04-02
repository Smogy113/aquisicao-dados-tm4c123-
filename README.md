# 📡 Sistema de Aquisição de Dados — TM4C123

Interface gráfica em Python para monitoramento serial em tempo real, com firmware embarcado para o microcontrolador TM4C123. O sistema lê até 5 canais analógicos, gera um sinal PWM configurável e transmite os dados via UART para plotagem e exportação no PC.

---

## 🗂️ Estrutura do Repositório

```
├── firmware/
│   └── main.c          # Código C para o TM4C123 (TivaWare)
├── interface/
│   └── interface.py    # Interface PyQt6 com plotagem em tempo real
└── README.md
```

---

## ⚙️ Funcionamento Geral

```
┌─────────────────────────────┐          UART 115200 baud          ┌───────────────────────────┐
│         TM4C123             │  ──────── dados → ──────────────►  │     PC (interface.py)     │
│                             │                                     │                           │
│  ADC: 5 canais (PE0–PE3,    │  ◄─────── comandos ─────────────   │  PyQt6 + pyqtgraph        │
│       PD3)                  │                                     │  Plots em tempo real      │
│  PWM: saída em PB6          │                                     │  Exportação para CSV      │
└─────────────────────────────┘                                     └───────────────────────────┘
```

O firmware converte as tensões dos 5 canais ADC e as envia pela serial a cada `intervalo` segundos. A interface Python recebe, plota e permite exportar todo o histórico.

---

## 🔧 Hardware

| Componente | Detalhe |
|---|---|
| Microcontrolador | TM4C123GXL (Tiva C LaunchPad) |
| Clock do sistema | 80 MHz (PLL + cristal de 16 MHz) |
| Comunicação | UART0 — PA0 (RX) / PA1 (TX) |
| Baud rate | 115200 |
| Entradas analógicas | PE0, PE1, PE2, PE3, PD3 (ADC 12 bits, ref. 3,3 V) |
| Saída PWM | PB6 (M0PWM0) — frequência e duty cycle configuráveis |

### Mapa de pinos

| Pino | Função |
|---|---|
| PA0 | UART0 RX (recebe do PC) |
| PA1 | UART0 TX (envia ao PC) |
| PB6 | Saída PWM |
| PE0 | ADC Canal 3 (A3) |
| PE1 | ADC Canal 2 (A2) |
| PE2 | ADC Canal 1 (A1) |
| PE3 | ADC Canal 0 (A0) |
| PD3 | ADC Canal 4 |

---

## 📦 Firmware (`firmware/main.c`)

Desenvolvido com **TivaWare** para o TM4C123.

### O que faz

- Configura o ADC para ler 5 canais em sequência, disparado por software
- Converte os valores brutos (0–4095) para tensão (0–3,3 V)
- Envia os 5 valores pela UART no formato:
  ```
  1.23 0.45 2.10 3.30 1.65\r\n
  ```
- Aguarda o intervalo configurado e repete
- Atende comandos recebidos via interrupção UART para ajustar PWM e intervalo em tempo real

### Protocolo de comandos recebidos

| Comando | Exemplo | Efeito |
|---|---|---|
| `i0<valor>` | `i075` | Define duty cycle do PWM (0–100%) |
| `i1<valor>` | `i110000` | Define frequência do PWM (Hz) |
| `i2<valor>` | `i20.5` | Define intervalo de envio (segundos) |

### Como compilar

Importe o projeto em uma IDE compatível com TivaWare, como o **Code Composer Studio (CCS)** da Texas Instruments. Certifique-se de que as bibliotecas TivaWare estejam incluídas no path do projeto.

---

## 🖥️ Interface Python (`interface/interface.py`)

### Dependências

```bash
pip install PyQt6 pyqtgraph pyserial pandas
```

### Como executar

```bash
cd interface
python interface.py
```

### Funcionalidades

- **Conexão serial** — configure porta (padrão: `COM5`) e baud rate e clique em *Alterar porta*
- **Leitura em tempo real** — inicia uma thread dedicada para ler a serial sem travar a GUI
- **3 gráficos configuráveis** — escolha qual canal (A0–A3) plotar em cada eixo X e Y via combobox; cada gráfico exibe tensão (vermelho) e corrente derivada (azul)
- **4º gráfico** — sempre exibe a frequência ao longo do tempo
- **Pausar/retomar** — pausa os gráficos sem encerrar a leitura (dados continuam chegando)
- **Controle de PWM** — sliders para ajustar duty cycle (0–100%) e frequência (1–10.000 Hz) em tempo real
- **Controle de intervalo** — define a taxa de envio do firmware em segundos
- **Exportar CSV** — salva o histórico completo em `.csv` com separador `;` e decimal `,`

### Colunas do CSV exportado

| Coluna | Descrição |
|---|---|
| `Tempo` | Tempo relativo à primeira amostra (s) |
| `A0_Tensao` … `A3_Tensao` | Tensão em cada canal (V) |
| `A0_Corrente` … `A3_Corrente` | Corrente derivada (tensão × 0,008) |
| `Frequencia` | Frequência do PWM no momento da amostra (Hz) |

### Arquitetura da interface

A leitura serial é feita em uma **thread separada** para não bloquear a GUI. A comunicação entre a thread e a interface usa uma `Queue` threadsafe. Dois `QTimer` independentes controlam: um consome o buffer serial, outro atualiza os gráficos — permitindo taxas diferentes para cada operação.

```
Thread de leitura  ──►  Queue (buffer)  ──►  QTimer consumidor  ──►  Buffers de dados
                                                                             │
                                                                      QTimer gráficos
                                                                             │
                                                                       PlotWidgets
```

---

## 🚧 Limitações Conhecidas

- O protocolo de comandos entre a interface Python e o firmware usa formatos diferentes e precisa ser padronizado para funcionar corretamente
- Ao consumir o buffer serial, apenas a última amostra acumulada é processada — amostras intermediárias não são adicionadas ao histórico
- Após alterar a frequência do PWM pelo firmware, o duty cycle não é recalculado automaticamente e pode ficar incorreto
- A porta serial padrão está configurada para `COM5` (Windows); em Linux usar `/dev/ttyUSB0` ou similar

---

## 📄 Licença

Este projeto é de uso acadêmico/educacional.
