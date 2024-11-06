#include <LoRa.h>
#include "LoRaBoards.h"
#include <TinyGPS++.h>
#include <ClosedCube_HDC1080.h>

#ifndef CONFIG_RADIO_FREQ
#define CONFIG_RADIO_FREQ 915.0
#endif
#ifndef CONFIG_RADIO_OUTPUT_POWER
#define CONFIG_RADIO_OUTPUT_POWER 17
#endif
#ifndef CONFIG_RADIO_BW
#define CONFIG_RADIO_BW 125.0
#endif

#if !defined(USING_SX1276) && !defined(USING_SX1278)
#error "LoRa example is only allowed to run SX1276/78. For other RF models, please run examples/RadioLibExamples"
#endif

int counter = 0;

TinyGPSPlus gps;

const int numMedidas = 3;

float medidas_temp[numMedidas];
float medidas_hum[numMedidas];
float promedio_temp;
float promedio_hum;

float latitud;
float longitud;

ClosedCube_HDC1080 sensor;

float calcularPromedio(float medidas[])
{
    float promedio;
    float sum = 0;
    for (int i = 0; i < numMedidas; i++)
    {
        sum += medidas[i];
    }
    return promedio = sum / numMedidas;
}

static void smartDelay(unsigned long ms)
{
    unsigned long start = millis();
    do
    {
        while (Serial1.available())
            gps.encode(Serial1.read());
    } while (millis() - start < ms);
}

void setup()
{
    sensor.begin(0x40);
    delay(100);
    Serial.begin(115200);
    Serial1.begin(9600, SERIAL_8N1, 34, 12); // RX, TX
    delay(100);

    setupBoards();
    // When the power is turned on, a delay is required.
    delay(1500);

#ifdef RADIO_TCXO_ENABLE
    pinMode(RADIO_TCXO_ENABLE, OUTPUT);
    digitalWrite(RADIO_TCXO_ENABLE, HIGH);
#endif

    Serial.println("LoRa Sender");
    LoRa.setPins(RADIO_CS_PIN, RADIO_RST_PIN, RADIO_DIO0_PIN);
    if (!LoRa.begin(CONFIG_RADIO_FREQ * 1000000))
    {
        Serial.println("Starting LoRa failed!");
        while (1)
            ;
    }

    LoRa.setTxPower(CONFIG_RADIO_OUTPUT_POWER);

    LoRa.setSignalBandwidth(CONFIG_RADIO_BW * 1000);

    LoRa.setSpreadingFactor(10);

    LoRa.setPreambleLength(16);

    LoRa.setSyncWord(0xAB);

    LoRa.disableCrc();

    LoRa.disableInvertIQ();

    LoRa.setCodingRate4(7);

}

void loop()
{

    // SmartDelay para GPS, se encarga de obtener lo que envia el GPS
    smartDelay(10000);

    // Chirp
    for (int i = 0; i < numMedidas; i++)
    {
        // Tomar medidas
        float temperature = sensor.readTemperature();
        smartDelay(100); // Respetamos el tiempo de espera para el sensor
        float humidity = sensor.readHumidity();
        smartDelay(100); // Respetamos el tiempo de espera para el sensor
        // Guardar medidas
        medidas_temp[i] = temperature;
        medidas_hum[i] = humidity;
    }
    // Prunning
    // Calcular promedios
    promedio_temp = calcularPromedio(medidas_temp);
    promedio_hum = calcularPromedio(medidas_hum);

    // Leer datos del GPS
    gps.encode(Serial1.read());

    // Obtener latitud y longitud
    latitud = gps.location.lat();
    longitud = gps.location.lng();

    // Empaquetar datos
    String jsonData = "jeroag${\"lat\": {\"value\":" + String(gps.location.lat(), 6) + "} ,\"lon\": {\"value\":" + String(gps.location.lng(), 6) + "} , \"temp\": {\"value\":" + String(promedio_temp) + "} ,\"humedad\": {\"value\":" + String(promedio_hum) + "}}";
    Serial.print("Sending packet: ");
    Serial.println(jsonData);

    // send packet
    LoRa.beginPacket();
    LoRa.print(jsonData);
    LoRa.endPacket();

    if (u8g2)
    {
        char buf[256];
        u8g2->clearBuffer();
        u8g2->drawStr(0, 12, "Transmitting: OK!");
        snprintf(buf, sizeof(buf), "Sending: %d", counter);
        u8g2->drawStr(0, 30, buf);
        u8g2->sendBuffer();
    }
    delay(6000);

    if(millis() > 3600000){
        ESP.restart();
    }
}