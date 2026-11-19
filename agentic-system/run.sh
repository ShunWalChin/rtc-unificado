#!/bin/bash
# =============================================================================
# FAT TECH - SISTEMA AGENTICO UNIFICADO
# Script de inicialização completa
# =============================================================================

set -e

BASE_DIR="/e/rtc-unificado"
AGENTIC_DIR="$BASE_DIR/agentic-system"

echo "=============================================="
echo "  FAT TECH - SISTEMA AGENTICO UNIFICADO"
echo "=============================================="
echo ""

# Verificar Python
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] Python 3 não encontrado"
    exit 1
fi
echo "[OK] Python: $(python3 --version)"

# Verificar dependências
cd "$AGENTIC_DIR"
if [ -f "requirements.txt" ]; then
    echo "[INFO] Instalando dependências Python..."
    pip3 install -q -r requirements.txt 2>/dev/null || pip3 install -q requests python-dotenv 2>/dev/null
fi

# Verificar serviços RTC
echo ""
echo "=============================================="
echo "  Verificando Serviços RTC..."
echo "=============================================="

check_service() {
    local name="$1"
    local url="$2"
    if curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 3 2>/dev/null | grep -q "200\|302\|401"; then
        echo "  [OK] $name respondendo em $url"
        return 0
    else
        echo "  [AVISO] $name NÃO respondendo em $url"
        return 1
    fi
}

RTC_OK=0
check_service "DANFSe (Go)" "http://localhost:8080/health/live" && RTC_OK=$((RTC_OK+1))
check_service "Simples Nacional (Java)" "http://localhost:8082/versao" && RTC_OK=$((RTC_OK+1))
check_service "Regime Regular (Java)" "http://localhost:8080/api/calculadora/versao" && RTC_OK=$((RTC_OK+1))

echo ""
if [ $RTC_OK -eq 3 ]; then
    echo "[OK] Todos os 3 serviços RTC estão online!"
else
    echo "[AVISO] $RTC_OK/3 serviços RTC online."
    echo "        Execute ./start-all.sh para iniciar os serviços."
fi

# Verificar outros componentes
echo ""
echo "=============================================="
echo "  Verificando Componentes Integrados..."
echo "=============================================="

[ -d "/h/Documentos/fat-ops/projetos/meta-ads" ] && echo "[OK] Meta Ads BI encontrado" || echo "[AVISO] Meta Ads BI não encontrado"
[ -d "/f/clip-watcher" ] && echo "[OK] Clip-Watcher encontrado" || echo "[AVISO] Clip-Watcher não encontrado"
[ -f "/h/Users/WalfredoFigueiredoNe/AppData/Local/hermes/profiles/fat-dev/cache/scratch/typeform-diagnostico-supermercado.html" ] && echo "[OK] Typeform Ânima encontrado" || echo "[AVISO] Typeform Ânima não encontrado"

echo ""
echo "=============================================="
echo "  Iniciando Sistema Agentico..."
echo "=============================================="
echo ""
echo "Modos disponíveis:"
echo "  1) CLI Interativo (padrão)"
echo "  2) API HTTP (porta 8088)"
echo "  3) Verificar status e sair"
echo ""
read -p "Escolha [1-3]: " modo

case $modo in
    2)
        echo "Iniciando API HTTP na porta 8088..."
        python3 main.py api
        ;;
    3)
        python3 -c "
import sys
sys.path.insert(0, '.')
from main import AgenticSystem
system = AgenticSystem()
result = system.orchestrator.process({'action': 'status_sistema', 'params': {}})
import json
print(json.dumps(result, ensure_ascii=False, indent=2))
"
        ;;
    *)
        echo "Iniciando CLI interativo..."
        python3 main.py
        ;;
esac