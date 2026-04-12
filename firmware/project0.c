#include <stdint.h>
#include <stdbool.h>
#include "inc/hw_memmap.h"
#include "inc/hw_types.h"
#include "driverlib/sysctl.h"
#include "driverlib/gpio.h"
#include "driverlib/pwm.h"
#include "driverlib/adc.h"
#include "driverlib/pin_map.h"
#include "driverlib/uart.h"
#include "utils/uartstdio.h"
#include "utils/cmdline.h"
#include "driverlib/rom.h"
#include <stdlib.h>
#include "inc/hw_ints.h"
#include "driverlib/interrupt.h"

#define MAX_STRING_LEN 20

char buffer[MAX_STRING_LEN];
uint32_t index = 0;

void ConfigureUART0(void);
volatile bool g_bCommandReady = false;
char g_pcCmdBuf[32];
volatile uint32_t g_ui32CmdBufInd = 0;
float intervalo = 1.0;
bool sinalPwm = 0;

uint32_t pwmFreq = 100;
uint32_t pwmPer;
uint32_t pwmDuty = 50;

volatile bool g_bPrintPWM = true;

void PWM0Gen0IntHandler(void)
{
    uint32_t status = PWMGenIntStatus(PWM0_BASE, PWM_GEN_0, true);
    PWMGenIntClear(PWM0_BASE, PWM_GEN_0, status);

    if (!g_bPrintPWM) return;

    if (status & PWM_INT_CNT_ZERO)
    {
        sinalPwm = 1;
    }
    if (status & PWM_INT_CNT_AD)
    {
        sinalPwm = 0;
    }
}

void UART0IntHandler(void)
{
    uint32_t ui32Status;
    char charRecebido;

    ui32Status = UARTIntStatus(UART0_BASE, true);
    UARTIntClear(UART0_BASE, ui32Status);

    while(UARTCharsAvail(UART0_BASE))
    {
        charRecebido = UARTCharGet(UART0_BASE);

        if(charRecebido == 'i')
        {
            charRecebido = UARTCharGet(UART0_BASE);

            if (charRecebido == '0')
            {
                index = 0;
                while ((charRecebido != '\r') && (charRecebido != '\n') && index < (MAX_STRING_LEN - 1))
                {
                    charRecebido = UARTCharGet(UART0_BASE);
                    buffer[index] = charRecebido;
                    index++;
                }
                buffer[index] = '\0';
                pwmDuty = (uint32_t)atoi(buffer);
                PWMPulseWidthSet(PWM0_BASE, PWM_OUT_0, (pwmPer * pwmDuty) / 100);
                //UARTprintf("Duty cycle definido para: %d\r\n", pwmDuty);
            }
            else if (charRecebido == '1')
            {
                index = 0;
                while ((charRecebido != '\r') && (charRecebido != '\n') && index < (MAX_STRING_LEN - 1))
                {
                    charRecebido = UARTCharGet(UART0_BASE);
                    buffer[index] = charRecebido;
                    index++;
                }
                buffer[index] = '\0';
                pwmFreq = atoi(buffer);
                pwmPer  = SysCtlClockGet() / pwmFreq;
                PWMGenPeriodSet(PWM0_BASE, PWM_GEN_0, pwmPer);
                PWMPulseWidthSet(PWM0_BASE, PWM_OUT_0, (pwmPer * pwmDuty) / 100);
                //UARTprintf("Frequencia definida para: %d Hz\r\n", pwmFreq);
            }
            else if (charRecebido == '2')
            {
                index = 0;
                while ((charRecebido != '\r') && (charRecebido != '\n') && index < (MAX_STRING_LEN - 1))
                {
                    charRecebido = UARTCharGet(UART0_BASE);
                    buffer[index] = charRecebido;
                    index++;
                }
                buffer[index] = '\0';
                intervalo = atof(buffer);
                int parte_inteira = (int)intervalo;
                int parte_decimal = (int)((intervalo - parte_inteira) * 100);
                if(parte_decimal < 0) parte_decimal *= -1;
                //UARTprintf("Intervalo de leitura definido para: %d.%02d segundos.\r\n", parte_inteira, parte_decimal);
            }
            break;
        }
    }
}

int main(void) {
    uint32_t adc_values[5];
    float voltages[5];
    int i;

    SysCtlClockSet(SYSCTL_SYSDIV_2_5 | SYSCTL_USE_PLL | SYSCTL_OSC_MAIN | SYSCTL_XTAL_16MHZ);

    ConfigureUART0();
    UARTIntRegister(UART0_BASE, UART0IntHandler);
    IntEnable(INT_UART0);
    UARTIntEnable(UART0_BASE, UART_INT_RX | UART_INT_RT);
    IntMasterEnable();

    SysCtlPeripheralEnable(SYSCTL_PERIPH_PWM0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOB);
    SysCtlPWMClockSet(SYSCTL_PWMDIV_1);
    GPIOPinConfigure(GPIO_PB6_M0PWM0);
    GPIOPinTypePWM(GPIO_PORTB_BASE, GPIO_PIN_6);

    pwmPer = SysCtlClockGet() / pwmFreq;
    PWMGenConfigure(PWM0_BASE, PWM_GEN_0, PWM_GEN_MODE_DOWN | PWM_GEN_MODE_NO_SYNC);
    PWMGenPeriodSet(PWM0_BASE, PWM_GEN_0, pwmPer);
    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_0, (pwmPer * pwmDuty) / 100);
    PWMGenEnable(PWM0_BASE, PWM_GEN_0);
    PWMOutputState(PWM0_BASE, PWM_OUT_0_BIT, true);

    PWMGenIntRegister(PWM0_BASE, PWM_GEN_0, PWM0Gen0IntHandler);
    PWMGenIntTrigEnable(PWM0_BASE, PWM_GEN_0, PWM_INT_CNT_ZERO | PWM_INT_CNT_AD);
    PWMIntEnable(PWM0_BASE, PWM_INT_GEN_0);
    IntEnable(INT_PWM0_0);

    SysCtlPeripheralEnable(SYSCTL_PERIPH_ADC0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOE);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOD);

    GPIOPinTypeADC(GPIO_PORTE_BASE, GPIO_PIN_3 | GPIO_PIN_2 | GPIO_PIN_1 | GPIO_PIN_0);
    GPIOPinTypeADC(GPIO_PORTD_BASE, GPIO_PIN_3);

    ADCSequenceConfigure(ADC0_BASE, 0, ADC_TRIGGER_PROCESSOR, 0);
    ADCSequenceStepConfigure(ADC0_BASE, 0, 0, ADC_CTL_CH0);
    ADCSequenceStepConfigure(ADC0_BASE, 0, 1, ADC_CTL_CH1);
    ADCSequenceStepConfigure(ADC0_BASE, 0, 2, ADC_CTL_CH2);
    ADCSequenceStepConfigure(ADC0_BASE, 0, 3, ADC_CTL_CH3);
    ADCSequenceStepConfigure(ADC0_BASE, 0, 4, ADC_CTL_CH4 | ADC_CTL_IE | ADC_CTL_END);
    ADCSequenceEnable(ADC0_BASE, 0);

    while (1) {
        ADCProcessorTrigger(ADC0_BASE, 0);
        while (!ADCIntStatus(ADC0_BASE, 0, false)) {}
        ADCIntClear(ADC0_BASE, 0);
        ADCSequenceDataGet(ADC0_BASE, 0, adc_values);

        for (i = 0; i < 5; i++) {
            voltages[i] = ((float)adc_values[i] * 3.3f) / 4095.0f;
        }

        for (i = 0; i < 4; i++) {
            int parte_inteira = (int)voltages[i];
            int parte_decimal = (int)((voltages[i] - parte_inteira) * 100);
            if(parte_decimal < 0) parte_decimal *= -1;
            UARTprintf("%d.%02d ", parte_inteira, parte_decimal);
        }
        (sinalPwm == 1) ? UARTprintf("3.33\r\n") : UARTprintf("0.00\r\n");

        if (intervalo > 0) {
            SysCtlDelay((uint32_t)(SysCtlClockGet() * intervalo / 3.0f));
        }
    }

    return 0;
}

void ConfigureUART0(void)
{
    SysCtlPeripheralEnable(SYSCTL_PERIPH_UART0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOA);
    GPIOPinConfigure(GPIO_PA0_U0RX);
    GPIOPinConfigure(GPIO_PA1_U0TX);
    GPIOPinTypeUART(GPIO_PORTA_BASE, GPIO_PIN_0 | GPIO_PIN_1);

    UARTClockSourceSet(UART0_BASE, UART_CLOCK_PIOSC);
    UARTStdioConfig(0, 115200, 16000000);
}