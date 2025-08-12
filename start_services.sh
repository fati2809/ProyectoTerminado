#!/bin/bash
# Script para iniciar todos los microservicios en Render

PROJECT_DIR="$(pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Verificar que PORT está definida
if [ -z "$PORT" ]; then
    echo "Error: La variable de entorno PORT no está definida."
    exit 1
fi

# Iniciar servicios
echo "Iniciando microservicios..."

# API Gateway (Render usará este puerto)
PORT=$PORT python3 "$PROJECT_DIR/api_gateway/app.py" > "$LOG_DIR/api_gateway.log" 2>&1 &

# Otros microservicios con puertos fijos
PORT=5001 python3 "$PROJECT_DIR/auth_service/app.py" > "$LOG_DIR/auth_service.log" 2>&1 &
PORT=5002 python3 "$PROJECT_DIR/user_service/app.py" > "$LOG_DIR/user_service.log" 2>&1 &
PORT=5003 python3 "$PROJECT_DIR/task_service/app.py" > "$LOG_DIR/task_service.log" 2>&1 &

# Evitar que Render mate el contenedor (mantener en primer plano el API Gateway)
wait
