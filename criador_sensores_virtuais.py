import json
import random
from pathlib import Path

config = "config"
numero_sensores = 2 # A atividade pede 30

def run_app():
    folder_path = Path(config)
    folder_path.mkdir(parents=True, exist_ok=True)
    for sensor_id in range(numero_sensores):
        temperature = random.uniform(10.0, 50.0)
        interval = random.random() + 0.1
        sensor_data = {
            "sensor_id": sensor_id,
            "base_temp": temperature,
            "intervalo_envio_s": interval,
            "broker_ip": "localhost", # "broker.emqx.io",
            "broker_porta": 1883
        }
        with open(f"{config}/sensor_{sensor_id}.json", "w") as file:
            json.dump(sensor_data, file, indent=4)


if __name__ == '__main__':
    run_app()
