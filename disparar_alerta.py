"""
Disparador manual de anomalia — usado apenas na DEMONSTRACAO do alerta por e-mail.

Publica uma unica leitura critica (temp >= 95) diretamente no broker MQTT,
forcando o smart_gateway a detectar a anomalia e enviar o e-mail de alerta na hora.

Assim a gravacao do video fica deterministica, sem precisar esperar o 1% de
chance aleatoria do simulador_sensores.py gerar uma temperatura alta.

Uso:
    python disparar_alerta.py            # sensor_id=99, temp=97.5
    python disparar_alerta.py 3 99.9     # sensor_id=3, temp=99.9
"""
import json
import sys
import time
import paho.mqtt.client as mqtt

BROKER_IP = "localhost"
BROKER_PORTA = 1883

sensor_id = int(sys.argv[1]) if len(sys.argv) > 1 else 99
temp = float(sys.argv[2]) if len(sys.argv) > 2 else 97.5

payload = {"sensor_id": sensor_id, "temp": temp, "timestamp": time.time()}

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER_IP, BROKER_PORTA)
client.publish(f"factory/sensors/{sensor_id}", json.dumps(payload))
client.disconnect()

print(f"[DISPARADOR] Anomalia publicada -> sensor {sensor_id}, temp {temp}C. "
      f"O gateway deve detectar e enviar o e-mail de alerta agora.")
