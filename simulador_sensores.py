import os
import json
import random
import time
from threading import Thread
import paho.mqtt.client as mqtt

threads_lista = []


def sensor_worker(sensor_id):
    caminho_arquivo = f"config/sensor_{sensor_id}.json"
    file = open(caminho_arquivo, 'r')
    config = json.load(file)
    file.close()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(config['broker_ip'], config['broker_porta'], 60)
    # client.loop_start() # nao necessario neste projeto

    print(f"[SENSOR {sensor_id}] Conectado ao broker. Iniciando transmissão...")

    while True:
        temp = config['base_temp'] + random.uniform(-1.0, 1.0)
        if random.random() < 0.01:
            temp = 95.0

        payload_dict = {
            "sensor_id": sensor_id,
            "temp": round(temp, 2),
            "timestamp": time.time()
        }
        sensor_dada = json.dumps(payload_dict)
        client.publish(f"factory/sensors/{sensor_id}", sensor_dada)
        time.sleep(config.get('intervalo_envio_s', 1))

def run_app():
    if not os.path.isdir("config"):
        print("E necessario que os arquivos de configuracao existam. Execute o criador_sensores_vistuais.py")
        return
    files = os.listdir("config")
    for sensor_id in range(len(files)):
        t = Thread(target=sensor_worker, args=(sensor_id,))
        threads_lista.append(t)
    for t in threads_lista:
        time.sleep(0.1) # apenas para nao atropelar o log inicial
        t.start()
    while True: # Mantem o script vivo para que as threaads filhas continue em execucao
        time.sleep(1)


if __name__ == '__main__':
    try:
        run_app()
    except KeyboardInterrupt:
        print(f"\n[*] Smart Gateway finalizado pelo usuario.")
