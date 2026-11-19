#!/bin/bash
# =============================================================================
# RTC UNIFICADO - Verificador de Ambiente
# Verifica se Java, Go e Docker estão disponíveis
# =============================================================================

echo "=============================================="
echo "  RTC UNIFICADO - Verificação de Ambiente"
echo "=============================================="
echo ""

ERROS=0

# Verificar Java
if command -v java &>/dev/null; then
    JAVA_VER=$(java -version 2>&1 | head -1)
    echo "[OK] Java: $JAVA_VER"
else
    echo "[FALTA] Java não encontrado"
    echo "        Instale: https://adoptium.net/"
    ERROS=$((ERROS + 1))
fi

# Verificar Maven Wrapper (já vem nos repos)
if [ -f "./calculadora-rtc-simples-nacional/mvnw" ]; then
    echo "[OK] Maven Wrapper (Simples Nacional): presente"
else
    echo "[FALTA] Maven Wrapper (Simples Nacional)"
    ERROS=$((ERROS + 1))
fi

if [ -f "./calculadora-rtc-regime-regular/mvnw" ]; then
    echo "[OK] Maven Wrapper (Regime Regular): presente"
else
    echo "[FALTA] Maven Wrapper (Regime Regular)"
    ERROS=$((ERROS + 1))
fi

# Verificar Go
if command -v go &>/dev/null; then
    GO_VER=$(go version 2>&1)
    echo "[OK] Go: $GO_VER"
else
    echo "[FALTA] Go não encontrado"
    echo "        Instale: https://go.dev/dl/"
    ERROS=$((ERROS + 1))
fi

# Verificar Docker
if command -v docker &>/dev/null; then
    echo "[OK] Docker: $(docker --version 2>&1 | head -1)"
else
    echo "[INFO] Docker não encontrado (opcional)"
fi

# Verificar Node.js (para servir o HTML se necessário)
if command -v node &>/dev/null; then
    echo "[OK] Node.js: $(node --version)"
else
    echo "[INFO] Node.js não encontrado (opcional - pode abrir o HTML diretamente)"
fi

echo ""
echo "=============================================="
if [ $ERROS -eq 0 ]; then
    echo "  Todas as dependências estão instaladas!"
    echo ""
    echo "Para iniciar:"
    echo "  ./start-all.sh"
else
    echo "  $ERROS dependência(s) faltando."
    echo ""
    echo "Instale o que faltar e rode novamente:"
    echo "  ./verificar-ambiente.sh"
fi
echo "=============================================="

exit $ERROS