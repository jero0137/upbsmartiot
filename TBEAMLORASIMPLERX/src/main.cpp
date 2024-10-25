// Only supports SX1276/SX1278
#include <LoRa.h>
#include "LoRaBoards.h"
#include <WiFi.h>
#ifndef CONFIG_RADIO_FREQ
#define CONFIG_RADIO_FREQ           915.0
#endif
#ifndef CONFIG_RADIO_OUTPUT_POWER
#define CONFIG_RADIO_OUTPUT_POWER   17
#endif
#ifndef CONFIG_RADIO_BW
#define CONFIG_RADIO_BW             125.0
#endif
 
 
const char* ssid = "UPBWiFi";
 
const char* host = "10.38.32.137";
const uint16_t port = 1026;
 
WiFiClient client;
 
void setup()
{
    setupBoards();
    // When the power is turned on, a delay is required.
    delay(1500);
 
    Serial.println("LoRa Receiver");
 
#ifdef  RADIO_TCXO_ENABLE
    pinMode(RADIO_TCXO_ENABLE, OUTPUT);
    digitalWrite(RADIO_TCXO_ENABLE, HIGH);
#endif
 
    LoRa.setPins(RADIO_CS_PIN, RADIO_RST_PIN, RADIO_DIO0_PIN);
    if (!LoRa.begin(CONFIG_RADIO_FREQ * 1000000)) {
        Serial.println("Starting LoRa failed!");
        while (1);
    }
 
    LoRa.setTxPower(CONFIG_RADIO_OUTPUT_POWER);
 
    LoRa.setSignalBandwidth(CONFIG_RADIO_BW * 1000);
 
    LoRa.setSpreadingFactor(10);
 
    LoRa.setPreambleLength(16);
 
    LoRa.setSyncWord(0xAB);
 
    LoRa.disableCrc();
 
    LoRa.disableInvertIQ();
 
    LoRa.setCodingRate4(7);
 
    // put the radio into receive mode
    LoRa.receive();
 
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid);
 
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
}
 
void loop()
{
    // try to parse packet
    String nombre = "";
    String jsonData = "";
    int packetSize = LoRa.parsePacket();
 
    if (packetSize) {
        // received a packet
        Serial.print("Received packet '");
 
        String recv = "";
 
        // read packet
        while (LoRa.available()) {
            recv += (char)LoRa.read();
        }

        int separatorIndex = recv.indexOf('$');
        if (separatorIndex != -1) {
            nombre = recv.substring(0, separatorIndex);
            jsonData = recv.substring(separatorIndex + 1);
        }
        else {
            Serial.println("Separator '$' not found in received data.");
            return; // Salir si no se encuentra el separador
        }
         
        if (client.connect(host, port)){
            Serial.println("connected");
            client.println("PATCH /v2/entities/" +nombre + "/attrs HTTP/1.1");
            client.println("Host: 10.38.32.137");
            client.println("Content-Type: application/json");
            client.println("Content-Length: " + String(jsonData.length()));
            client.println("");
            client.println(jsonData);
        }
        else {
            Serial.println("connection failed");
        }

    }
}