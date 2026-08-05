import json
import threading
import time
from email.message import EmailMessage
import smtplib
import ssl
import paho.mqtt.client as mqtt
from threading import Thread
import firebase_admin
from firebase_admin import credentials, db

buffer_dados = []
lock_buffer = threading.Lock()
BROKER_IP = 'localhost'
BROKER_PORTA = 1883
TOPICO_FILTRO = "factory/sensors/#"
contador_dados_recebidos = 0
contador_dados_enviados = 0

EMAIL_DESTINATARIO = "" # email pessoal
EMAIL = "" # email da ufca
SENHA = "" # senha cadastrada no link abaixo
FIREBASE_DATABASE_URL = ""

# Link para criação de senha vinculada ao app, para uso nessa atividade
# Crie um app com nome simples exemplo: ADS_UFCA em https://myaccount.google.com/apppasswords

def enviar_email(sensor_id, temp):
    print(f"[EDGE LOG] *** ENVIANDO EMAIL DE ALERTA VIA SMTP - O sensor {sensor_id} registrou uma alta temperatura: {temp}! ***")
    if EMAIL_DESTINATARIO == "" or EMAIL == "" or SENHA == "": return
    msg = EmailMessage()
    msg.set_content(f"ALERTA> Sensor{sensor_id} detectou temperatura critica: {temp}C!")
    msg["Subject"] = 'Emergencia Industrial - Superaquecimento'
    msg["From"] = EMAIL
    msg["To"] = EMAIL_DESTINATARIO

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            context=context,
    ) as server:
        server.login(EMAIL, SENHA)
        server.send_message(msg)


def enviar_para_firebase(media_final):
    if FIREBASE_DATABASE_URL == "": return
    print("[EDGE LOG] Enviando media final para o Firebase")
    reference = db.reference("factory_stats")
    reference.set(media_final) # "push" modificado para "set" pois o metodo push cria multiplos valores paralelos, nao subscreve

def inicializar_fiebase():
    if FIREBASE_DATABASE_URL == "": return
    cred = credentials.Certificate("ufcasamples-firebase-adminsdk-fbsvc-b112cd0a55.json")
    firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DATABASE_URL})

def ao_receber_mensagem(client, user_data, msg):
    texto_recebido = msg.payload.decode("utf-8")
    dados_sensor = json.loads(texto_recebido)
    sensor_id = dados_sensor['sensor_id']
    temperatura = dados_sensor['temp']

    with lock_buffer:
        buffer_dados.append(dados_sensor)

    if temperatura >= 95: enviar_email(sensor_id, temperatura)

def processador_estatistico_borda():
    global contador_dados_recebidos
    global contador_dados_enviados
    while True:
        time.sleep(1)

        with lock_buffer:
            total_pacotes_no_segundo = len(buffer_dados)
            if total_pacotes_no_segundo > 0:
                soma_temperaturas = 0.0
                for dados_sensor in buffer_dados:
                    soma_temperaturas += dados_sensor['temp']
                    contador_dados_recebidos += len(json.dumps(dados_sensor))
                media_final = soma_temperaturas / total_pacotes_no_segundo

                print("-----------------------------------------------------------------")
                print(f"[EDGE LOG] Janela de 1s encerrada. Pacotes Locais Recebidos: {total_pacotes_no_segundo}")
                print(f"[EDGE LOG] Média consolidada da fábrica: {media_final:.2f}°C")

                media_final = {"media_final": media_final}
                contador_dados_enviados += len(json.dumps(media_final))
                enviar_para_firebase(media_final)

                # mostrando a economia de banda em tempo real
                percentage = 100 - int(((contador_dados_enviados / contador_dados_recebidos) * 100))
                print(f"[EDGE LOG] Total de dados recebidos: {contador_dados_recebidos}bytes. Total enviado para a nuvem: {contador_dados_enviados}bytes. Economia de {percentage}%.")

                buffer_dados.clear()
            else:
                print("[EDGE LOG] Nenhum dado de sensor recebido no último segundo. Aguardando...")

if __name__ == "__main__":
    inicializar_fiebase()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = ao_receber_mensagem
    client.connect(BROKER_IP, BROKER_PORTA)
    client.subscribe(TOPICO_FILTRO)
    print(f"[EDGE LOG]  Gateway inscrito com sucesso no topico: {TOPICO_FILTRO}")

    t = Thread(target=processador_estatistico_borda)
    t.daemon = True
    t.start()

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[EDGE LOG]  Smart Gateway finalizado pelo usuario.")