#!/bin/bash
# =============================================================================
# RTC UNIFICADO - Script de Inicialização
# Inicia os 3 serviços da Receita Federal e abre o dashboard
# =============================================================================

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEN_DANFSE="$BASE_DIR/calculadora-rtc-gerador-danfse"
SIMPLES_NACIONAL="$BASE_DIR/calculadora-rtc-simples-nacional"
REGIME_REGULAR="$BASE_DIR/calculadora-rtc-regime-regular"

echo "=============================================="
echo "  RTC UNIFICADO - Iniciando Serviços"
echo "=============================================="
echo ""

# Verificar se Java está disponível
JAVA_CMD=""
if command -v java &>/dev/null; then
    JAVA_VER=$(java -version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
    echo "[OK] Java encontrado: $JAVA_VER"
    JAVA_CMD="java"
else
    echo "[WARN] Java não encontrado. Os projetos Java (Simples Nacional e Regime Regular) não funcionarão."
    echo "       Instale o Java 21+: https://adoptium.net/"
    echo ""
fi

# Verificar se Go está disponível
GO_CMD=""
if command -v go &>/dev/null; then
    GO_VER=$(go version 2>&1 | grep -oE 'go[0-9]+\.[0-9]+' | head -1)
    echo "[OK] Go encontrado: $GO_VER"
    GO_CMD="go"
else
    echo "[WARN] Go não encontrado. O Gerador DANFSe não funcionará."
    echo "       Instale o Go 1.27+: https://go.dev/dl/"
    echo ""
fi

# Verificar Docker
DOCKER_CMD=""
if command -v docker &>/dev/null; then
    echo "[OK] Docker encontrado"
    DOCKER_CMD="docker"
else
    echo "[INFO] Docker não encontrado (opcional - pode rodar os serviços via Docker)"
fi

echo ""
echo "=============================================="
echo "  Iniciando Serviços..."
echo "=============================================="

# Função para iniciar serviço em background
start_service() {
    local name="$1"
    local dir="$2"
    local cmd="$3"
    local port="$4"
    echo "[INFO] Iniciando $name em $dir..."
    cd "$dir" || { echo "[ERRO] Diretório não encontrado: $dir"; return 1; }
    eval "$cmd" > "/tmp/rtc-$name.log" 2>&1 &
    local pid=$!
    echo "       PID: $pid (log: /tmp/rtc-$name.log)"
    echo "$pid" > "/tmp/rtc-$name.pid"
}

# Iniciar Gerador DANFSe (Go)
if [ -n "$GO_CMD" ]; then
    start_service "danfse" "$GEN_DANFSE" "go run ./cmd/danfse" "8080"
else
    echo "[SKIP] Gerador DANFSe - Go não instalado"
fi

# Iniciar Simples Nacional (Java)
if [ -n "$JAVA_CMD" ]; then
    start_service "simples" "$SIMPLES_NACIONAL" "./mvnw spring-boot:run -Dspring-boot.run.profiles=offline" "8082"
else
    echo "[SKIP] Simples Nacional - Java não instalado"
fi

# Iniciar Regime Regular (Java)
if [ -n "$JAVA_CMD" ]; then
    start_service "regime" "$REGIME_REGULAR" "./mvnw spring-boot:run -Dspring-boot.run.profiles=offline" "8080"
else
    echo "[SKIP] Regime Regular - Java não instalado"
fi

echo ""
echo "=============================================="
echo "  Aguardando serviços inicializarem..."
echo "=============================================="

sleep 8

# Verificar se os serviços estão respondendo
echo ""
echo "=============================================="
echo "  Status dos Serviços"
echo "=============================================="

check_service() {
    local name="$1"
    local url="$2"
    if curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 5 2>/dev/null | grep -q "200\|302\|401"; then
        echo "  [OK] $name está respondendo em $url"
    else
        echo "  [WARN] $name não respondeu em $url (pode estar iniciando)"
    fi
}

check_service "Gerador DANFSe" "http://localhost:8080/health/live"
check_service "Simples Nacional" "http://localhost:8082/versao"
check_service "Regime Regular" "http://localhost:8080/api/calculadora/versao"

echo ""
echo "=============================================="
echo "  Dashboard Web"
echo "=============================================="
echo "Abra o arquivo: file://$BASE_DIR/index.html"
echo ""
echo "Ou abra diretamente no navegador:"
echo "  file://$(pwd)/index.html"
echo ""
echo "=============================================="
echo "  Para parar os serviços:"
echo "  kill \$(cat /tmp/rtc-*.pid)"
echo "=============================================="

# Tentar abrir o dashboard no navegador
if command -v xdg-open &>/dev/null; then
    xdg-open "file://$(pwd)/index.html" &
elif command -v open &>/dev/null; then
    open "file://$(pwd)/index.html" &
elif command -v start &>/dev/null; then
    start "file://$(pwd)/index.html" &
fi

echo ""
echo "Pressione Enter para sair..."
read -r