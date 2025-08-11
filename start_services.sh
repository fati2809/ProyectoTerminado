#!/bin/bash
# Script para iniciar todos los microservicios del proyecto en Render
# El api_gateway escucha en el puerto asignado por Render (variable $PORT)
# Los otros servicios usan puertos internos fijos

PROJECT_DIR="$(pwd)"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

# Función para iniciar un servicio
start_service() {
    local service_dir=$1
    local service_name=$2
    local port=$3
    echo "Iniciando $service_name en el puerto $port..."
    cd "$PROJECT_DIR/$service_dir" || exit 1
    
    # Exportamos la variable PORT para que el servicio escuche en el puerto indicado
    export PORT=$port
    
    # Ejecutamos la app en segundo plano y guardamos logs y PID
    python3 app.py > "$LOG_DIR/$service_name.log" 2>&1 &
    echo "$!" > "$LOG_DIR/$service_name.pid"
    
    cd "$PROJECT_DIR"
}

# El api_gateway debe escuchar en el puerto que Render asigna para tráfico externo
if [ -z "$PORT" ]; then
    echo "Error: La variable de entorno PORT no está definida."
    echo "Render asigna esta variable automáticamente para el puerto público."
    exit 1
fi

# Iniciar api_gateway en el puerto asignado por Render
start_service "api_gateway" "api_gateway" "$PORT"

# Iniciar los microservicios internos en puertos fijos
start_service "auth_service" "auth_service" 5001
start_service "user_service" "user_service" 5002
start_service "task_service" "task_service" 5003

echo "Todos los microservicios han sido iniciados."
echo "Logs disponibles en $LOG_DIR"
echo "Para detener los servicios, usa el comando 'stop_services.sh'."
