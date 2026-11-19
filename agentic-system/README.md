# FAT Tech - Sistema Agentico Unificado

Sistema de agentes inteligentes que integra todas as ferramentas da FAT Tech:

| Domínio | Agente | Capacidades |
|---------|--------|-------------|
| **RTC** | `rtc_agent` | DANFSe, Simples Nacional, Regime Regular |
| **Meta Ads** | `meta_ads_agent` | Dashboards BI, coleta de dados, contas |
| **Twitch** | `clip_watcher_agent` | Gravação live, detecção picos, cortes, verticais |
| **Ânima** | `anima_agent` | Typeform diagnóstico, processamento, relatórios |
| **Análise** | `analyzer_agent` | Tendências, correlações, resumos |
| **Orquestrador** | `orchestrator` | Roteamento, workflows, chat unificado |

---

## 🚀 Início Rápido

```bash
# 1. Verificar e instalar dependências
cd /e/rtc-unificado/agentic-system
chmod +x run.sh

# 2. Iniciar serviços RTC (em outro terminal)
cd /e/rtc-unificado
./start-all.sh

# 3. Iniciar sistema agentico
cd /e/rtc-unificado/agentic-system
./run.sh
```

---

## 💬 Exemplos de Uso (CLI)

### Calculadoras RTC
```
🤖 FAT Agentic > Gerar DANFSe do arquivo /tmp/nota.xml com STC 1
🤖 FAT Agentic > Calcular Simples Nacional para itens: [{"ncm":"24021000","baseCalculo":"1000"}]
🤖 FAT Agentic > Calcular Regime Regular para NCM 24021000 valor 5000
🤖 FAT Agentic > Listar atividades Simples Nacional para 2026-01-15
```

### Meta Ads BI
```
🤖 FAT Agentic > Mostrar dashboards Meta Ads de hoje
🤖 FAT Agentic > Gerar dashboard para conta 123456789
🤖 FAT Agentic > Coletar dados dos últimos 15 dias
```

### Clip-Watcher Twitch
```
🤖 FAT Agentic > Iniciar gravação da live do alanzoka
🤖 FAT Agentic > Listar clipes gerados
🤖 FAT Agentic > Testar sistema clip-watcher
```

### Diagnóstico Ânima
```
🤖 FAT Agentic > Carregar diagnóstico Ânima supermercado
🤖 FAT Agentic > Processar respostas do typeform
```

### Análise
```
🤖 FAT Agentic > Analisar tendência: [10, 15, 12, 18, 22, 25]
🤖 FAT Agentic > Correlacionar X: [1,2,3,4] Y: [2,4,6,8]
```

---

## 🌐 API HTTP

Inicie no modo API:
```bash
./run.sh
# Escolha opção 2
```

Ou direto:
```bash
python3 main.py api
```

### Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/health` | Health check |
| `POST` | `/` | Executar ação no orquestrador |

### Exemplo de Request

```bash
curl -X POST http://localhost:8088/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "chat",
    "params": {
      "message": "Calcular Simples Nacional para item NCM 24021000 base 1000",
      "params": {}
    }
  }'
```

### Workflow Complexo (POST)

```bash
curl -X POST http://localhost:8088/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "executar_workflow",
    "params": {
      "workflow": [
        {"agent": "rtc_agent", "action": "health_check", "params": {"service": "all"}},
        {"agent": "meta_ads_agent", "action": "listar_dashboards", "params": {"data": "2026-11-15"}},
        {"agent": "clip_watcher_agent", "action": "listar_clipes", "params": {}}
      ]
    }
  }'
```

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                             │
│  (Roteamento inteligente, Workflows, Chat unificado)       │
└──────────┬──────────────┬──────────────┬────────────────────┘
           │              │              │
    ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌──────▼──────┐
    │  RTC Agent  │ │Meta Ads   │ │Clip       │ │ Ânima Agent │
    │             │ │Agent      │ │Watcher    │ │             │
    │ • DANFSe    │ │• BI       │ │Agent      │ │• Typeform   │
    │ • Simples   │ │• Contas   │ │• Gravação │ │• Scores     │
    │ • Regime    │ │• Coleta   │ │• Cortes   │ │• Relatórios │
    └─────────────┘ └───────────┘ └───────────┘ └─────────────┘
           │              │              │              │
           └──────────────┴──────────────┴──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   MEMORY BUS      │
                    │  (JSON persistido)│
                    └───────────────────┘
```

---

## 🔧 Configuração

Edite `main.py` na seção `CONFIG`:

```python
CONFIG = {
    "apis": {
        "danfse": "http://localhost:8080",
        "simples": "http://localhost:8082",
        "regime": "http://localhost:8080"
    },
    "paths": {
        "rtc_base": "/e/rtc-unificado",
        "clip_watcher": "/f/clip-watcher",
        "meta_ads": "/h/Documentos/fat-ops/projetos/meta-ads",
        "anima_docs": "/h/Documentos/fat-ops/conhecimento/kit-master-anima"
    }
}
```

---

## 🧠 Memória Persistente

O sistema mantém memória entre sessões em:
```
/e/rtc-unificado/agentic-system/memory/agent_memory.json
```

Cada agente pode armazenar/recuperar dados:
```python
memory.set("meu_agent", "chave", {"dados": "valor"}, tags=["importante"])
valor = memory.get("meu_agent", "chave")
```

---

## 📋 Pré-requisitos

| Componente | Necessário Para |
|------------|-----------------|
| Python 3.10+ | Sistema agentico |
| Java 21+ | Simples Nacional, Regime Regular |
| Go 1.27+ | Gerador DANFSe |
| requests | Cliente HTTP |
| Serviços RTC rodando | Calculadoras funcionando |

---

## 🔐 Segurança

- Todas as APIs rodam em **localhost** (não expostas externamente)
- Tokens OAuth ficam em `config.json` (gitignored)
- Nenhum dado sensível é logado
- Aprovação R2 necessária para ações destrutivas

---

## 📁 Estrutura de Arquivos

```
agentic-system/
├── main.py              # Sistema principal (900+ linhas)
├── requirements.txt     # Dependências Python
├── run.sh              # Script de inicialização
├── memory/             # Memória persistente
│   └── agent_memory.json
└── README.md           # Este arquivo
```

---

## 🤝 Integração com Sistemas Existentes

O sistema agentico **não substitui** os sistemas existentes, ele os **orquestra**:

| Sistema Original | Como é usado |
|------------------|--------------|
| `index.html` (dashboard RTC) | Interface visual, agentes chamam APIs |
| `start-all.sh` | Inicia serviços que agentes consomem |
| `clip_watcher_runner.py` | Chamado pelo `clip_watcher_agent` |
| `bi_v2.py` | Chamado pelo `meta_ads_agent` |
| `typeform-diagnostico-supermercado.html` | Carregado pelo `anima_agent` |

---

## 📝 Logs

Logs do sistema:
```
~/.fat-agentic.log
```

Logs dos serviços (via start-all.sh):
```
/tmp/rtc-danfse.log
/tmp/rtc-simples.log
/tmp/rtc-regime.log
```

---

## 🆘 Troubleshooting

**Agente não responde:**
```bash
# Verificar status
./run.sh  # Opção 3

# Ver logs
tail -f ~/.fat-agentic.log
```

**Serviços RTC offline:**
```bash
cd /e/rtc-unificado
./start-all.sh
```

**Erro de importação:**
```bash
cd /e/rtc-unificado/agentic-system
pip3 install -r requirements.txt
```

---

## 📄 Licença

Sistema proprietário FAT Tech. Componentes da Receita Federal sob licença MIT.