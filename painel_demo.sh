#!/usr/bin/env bash
#
# painel_demo.sh — Abre um painel tmux com todos os processos da demonstracao
# do Alerta por E-mail em uma unica tela, ideal para gravar o video.
#
# Layout:
#   +------------------+------------------+
#   |   SIMULADOR      |     BROKER       |   <- sensores geram / broker recebe
#   +------------------+------------------+
#   |          GATEWAY (destaque)         |   <- detecta anomalia e envia e-mail
#   +-------------------------------------+
#   |        CONTROLE (disparador)        |   <- voce dispara o alerta aqui
#   +-------------------------------------+
#
# Uso:
#   ./painel_demo.sh          # abre o painel
#   ./painel_demo.sh kill     # fecha o painel/sessao
#
set -euo pipefail

SESSION="smartgw"

# Diretorio do proprio script -> funciona em qualquer maquina/usuario
PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Python: prioriza o venv ativo, depois um .venv na pasta do projeto, depois o do sistema
if [[ -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  PY="$VIRTUAL_ENV/bin/python"
elif [[ -x "$PROJ/.venv/bin/python" ]]; then
  PY="$PROJ/.venv/bin/python"
else
  PY="$(command -v python3 || command -v python)"
fi

# Mosquitto: procura no PATH; se nao achar, tenta o caminho padrao do Homebrew (Apple Silicon)
MOSQ_BIN="$(command -v mosquitto || echo /opt/homebrew/opt/mosquitto/sbin/mosquitto)"
MOSQ_CONF="/tmp/mosq_ufca.conf"

# ---- opcao para fechar tudo ----
if [[ "${1:-}" == "kill" ]]; then
  tmux kill-session -t "$SESSION" 2>/dev/null || true
  echo "Painel '$SESSION' encerrado."
  exit 0
fi

# ---- garante config do broker ----
printf 'listener 1883 0.0.0.0\nallow_anonymous true\n' > "$MOSQ_CONF"

# ---- broker: usa o existente se ja estiver no ar, senao sobe um novo ----
if lsof -nP -iTCP:1883 -sTCP:LISTEN >/dev/null 2>&1; then
  BROKER_CMD="echo '>> Broker MQTT ja esta rodando na porta 1883 (reutilizando).'; echo '>> Aguardando publicacoes...'; sleep infinity"
else
  BROKER_CMD="echo '=== BROKER MOSQUITTO (porta 1883) ==='; $MOSQ_BIN -c $MOSQ_CONF -v"
fi

# ---- cria a pasta config/ dos sensores (roda 1x) ----
cd "$PROJ"
"$PY" criador_sensores_virtuais.py
echo ">> Sensores configurados. Abrindo painel..."

# ---- (re)cria a sessao tmux ----
tmux kill-session -t "$SESSION" 2>/dev/null || true

# labels visiveis na borda de cada painel
tmux new-session -d -s "$SESSION" -c "$PROJ"
tmux set -t "$SESSION" -g pane-border-status top
tmux set -t "$SESSION" -g pane-border-format " #[bold]#{pane_title} "
tmux set -t "$SESSION" -g mouse on

# --- monta o layout (usando IDs estaveis de painel; o tmux renumera os
#     indices por posicao apos cada split, entao amarramos por %id) ---
P_SIM=$(tmux display-message -p -t "$SESSION:0.0" '#{pane_id}')                 # topo-esquerda: SIMULADOR
P_CTRL=$(tmux split-window -v -l 10  -t "$P_SIM" -c "$PROJ" -P -F '#{pane_id}') # barra inferior: CONTROLE
P_GW=$(tmux split-window   -v -p 62  -t "$P_SIM" -c "$PROJ" -P -F '#{pane_id}') # faixa do meio: GATEWAY
P_BROKER=$(tmux split-window -h -p 50 -t "$P_SIM" -c "$PROJ" -P -F '#{pane_id}') # topo-direita: BROKER

# --- titulos ---
tmux select-pane -t "$P_SIM"    -T "1) SIMULADOR (sensores publicando)"
tmux select-pane -t "$P_BROKER" -T "2) BROKER MQTT (recebe/roteia)"
tmux select-pane -t "$P_GW"     -T "3) GATEWAY -> detecta anomalia e ENVIA E-MAIL"
tmux select-pane -t "$P_CTRL"   -T "4) CONTROLE -> dispare o alerta aqui"

# --- comandos em cada painel (com sleeps para respeitar a ordem de subida) ---
# Broker primeiro
tmux send-keys -t "$P_BROKER" "$BROKER_CMD" C-m
# Gateway sobe depois do broker
tmux send-keys -t "$P_GW" "sleep 2; echo '=== GATEWAY (o ator principal) ==='; $PY -u smart_gateway.py" C-m
# Simulador sobe por ultimo
tmux send-keys -t "$P_SIM" "sleep 4; echo '=== SIMULADOR (sensores) ==='; $PY -u simulador_sensores.py" C-m
# Painel de controle: deixa o comando do disparador pronto (so apertar Enter)
tmux send-keys -t "$P_CTRL" "clear; echo 'Para DISPARAR o alerta durante o video, rode:'; echo; echo '   $PY disparar_alerta.py 3 99.9'; echo" C-m
tmux send-keys -t "$P_CTRL" "$PY disparar_alerta.py 3 99.9"   # NAO envia Enter: fica pronto para voce apertar

# foca no painel de controle e abre
tmux select-pane -t "$P_CTRL"
tmux attach-session -t "$SESSION"
