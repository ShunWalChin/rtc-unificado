# FAT Tech — RTC Unificado + Sistema Agentico

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Java](https://img.shields.io/badge/Java-21+-red.svg)](https://adoptium.net)
[![Go](https://img.shields.io/badge/Go-1.27+-cyan.svg)](https://go.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

> **Sistema unificado que orquestra as 3 calculadoras da Receita Federal** através de um sistema agentico inteligente com interface de linguagem natural (CLI + API HTTP).

---

## 🎯 O que é este projeto?

Este repositório consolida **as 3 calculadoras oficiais da Receita Federal** em um único sistema:

| Calculadora | Repositório Original | Tecnologia | Porta | Função |
|-------------|---------------------|------------|-------|--------|
| **Gerador DANFSe** | `ReceitaFederal/calculadora-rtc-gerador-danfse` | Go | 8080 | Gera PDF do DANFSe a partir de XML de NFS-e |
| **Simples Nacional** | `ReceitaFederal/calculadora-rtc-simples-nacional` | Java/Spring Boot | 8082 | Calcula CBS e IBS - Regime Simples Nacional |
| **Regime Regular** | `ReceitaFederal/calculadora-rtc-regime-regular` | Java/Spring Boot | 8080 | Calcula CBS, IBS e Imposto Seletivo - Regime Regular |

**O sistema agentico não substitui — ele ORQUESTRA.** O agente RTC chama as APIs REST das 3 calculadoras via `requests`, mantendo a separação de responsabilidades.

---

## 🤖 Arquitetura do Sistema Agentico (RTC Only)

```
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                               │
│  • Roteamento NL (palavras-chave → agente RTC + ação)          │
│  • Workflows multi-step (execução sequencial)                  │
│  • Status agregado / health check dos 3 serviços               │
│  • Chat unificado com ajuda contextual                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    RTC AGENT      │
                    │  (Único agente)   │
                    │                   │
                    │ • health_check    │
                    │ • gerar_danfse    │
                    │ • calcular_simples│
                    │ • calcular_regime │
                    │ • listar_atividades│
                    │ • base_calculo    │
                    │ • validar_xml     │
                    │ • gerar_xml       │
                    └────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌────────────┐  ┌────────────┐
        │ DANFSe   │  │ Simples    │  │ Regime     │
        │ (Go)     │  │ Nacional   │  │ Regular    │
        │ :8080    │  │ (Java)     │  │ (Java)     │
        │          │  │ :8082      │  │ :8080      │
        └──────────┘  └────────────┘  └────────────┘
                             │
                    ┌─────────▼─────────┐
                    │   MEMORY BUS      │
                    │  (JSON persistido)│
                    └───────────────────┘
```

### Agentes Implementados

| Agente | Tipo | Ferramentas | Responsabilidade |
|--------|------|-------------|------------------|
| `orchestrator` | ORCHESTRATOR | `chat`, `executar_workflow`, `status_sistema`, `registrar_agente` | Núcleo central, roteamento NL |
| `rtc_agent` | RTC | 8 ferramentas (health_check, gerar_danfse, calcular_simples, calcular_regime, listar_atividades, base_calculo, validar_xml, gerar_xml) | Opera as 3 calculadoras |

---

## 🚀 Início Rápido

### Pré-requisitos

```bash
# Verificar ambiente
cd /e/rtc-unificado
./verificar-ambiente.sh
```

| Ferramenta | Versão | Para quê |
|------------|--------|----------|
| **Python** | 3.10+ | Sistema agentico |
| **Java** | 21+ | Simples Nacional, Regime Regular |
| **Go** | 1.27+ | Gerador DANFSe |
| **Docker** | (opcional) | Containers |

### 1. Iniciar Serviços RTC (Terminal 1)

```bash
cd /e/rtc-unificado
chmod +x start-all.sh
./start-all.sh
```
Inicia os 3 serviços em background:
- **DANFSe** → `http://localhost:8080`
- **Simples Nacional** → `http://localhost:8082`
- **Regime Regular** → `http://localhost:8080`

### 2. Iniciar Sistema Agentico (Terminal 2)

```bash
cd /e/rtc-unificado/agentic-system
chmod +x run.sh
./run.sh
```

**Escolha o modo:**
```
1) CLI Interativo      # Chat com linguagem natural
2) API HTTP (8088)     # Integração programática
3) Status              # Verifica todos os agentes
```

---

## 💬 Exemplos de Uso (CLI)

### Health Check
```
🤖 RTC Agentic > status dos servicos rtc
🤖 RTC Agentic > status do sistema
🤖 RTC Agentic > health check
```

### Gerador DANFSe (Porta 8080)
```
🤖 RTC Agentic > gerar danfse do arquivo /tmp/nota.xml
🤖 RTC Agentic > gerar danfse notas.xml stc 1 canhoto false
🤖 RTC Agentic > status do danfse
```

### Simples Nacional (Porta 8082)
```
🤖 RTC Agentic > calcular simples nacional para item NCM 24021000 base 1000
🤖 RTC Agentic > calcular simples nacional itens: [{"ncm":"24021000","baseCalculo":"1000.00"}]
🤖 RTC Agentic > listar atividades simples nacional para 2026-01-15
```

### Regime Regular (Porta 8080)
```
🤖 RTC Agentic > calcular regime regular para NCM 24021000 valor 5000
🤖 RTC Agentic > calcular regime regular itens: [{"ncm":"24021000","baseCalculo":"5000.00"}] municipio 4314902
🤖 RTC Agentic > validar xml da nfe
🤖 RTC Agentic > gerar xml regime regular
```

---

## 🌐 API HTTP (Porta 8088)

```bash
# Iniciar API
python3 main.py api
```

### Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/health` | Health check |
| `POST` | `/` | Executar ação no orquestrador |

### Chat via API

```bash
curl -X POST http://localhost:8088/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "chat",
    "params": {
      "message": "status dos servicos rtc",
      "params": {}
    }
  }'
```

### Workflow Multi-Step

```bash
curl -X POST http://localhost:8088/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "executar_workflow",
    "params": {
      "workflow": [
        {"agent": "rtc_agent", "action": "health_check", "params": {"service": "all"}},
        {"agent": "rtc_agent", "action": "calcular_simples", "params": {"itens": [{"ncm":"24021000","baseCalculo":"1000"}]}},
        {"agent": "rtc_agent", "action": "calcular_regime", "params": {"itens": [{"ncm":"24021000","baseCalculo":"5000"}] }}
      ]
    }
  }'
```

### Status do Sistema

```bash
curl -X POST http://localhost:8088/ \
  -H "Content-Type: application/json" \
  -d '{"action": "status_sistema", "params": {}}'
```

---

## 📁 Estrutura do Repositório

```
rtc-unificado/
├── index.html                      # Dashboard web RTC (abrir no navegador)
├── start-all.sh                    # Inicia 3 serviços RTC
├── verificar-ambiente.sh           # Verifica Java, Go, Docker, Python
├── .gitignore                      # Exclui submódulos, cache, memory
├── README.md                       # Este arquivo
├── LICENSE                         # MIT
│
├── calculadora-rtc-gerador-danfse/  # Submódulo (Go) - Receita Federal
├── calculadora-rtc-simples-nacional/ # Submódulo (Java) - Receita Federal
├── calculadora-rtc-regime-regular/  # Submódulo (Java) - Receita Federal
│
└── agentic-system/                 # SISTEMA AGENTICO RTC
    ├── main.py                     # ~570 linhas - Orchestrator + RTC Agent
    ├── requirements.txt            # requests
    ├── run.sh                      # Inicialização (CLI/API/Status)
    ├── README.md                   # Documentação técnica
    └── memory/
        └── agent_memory.json       # Memória persistente entre sessões
```

---

## ⚙️ Configuração

Edite `agentic-system/main.py` na seção `CONFIG`:

```python
CONFIG = {
    "apis": {
        "danfse": "http://localhost:8080",
        "simples": "http://localhost:8082",
        "regime": "http://localhost:8080"
    },
    "memory": {
        "path": "/e/rtc-unificado/agentic-system/memory/agent_memory.json",
        "max_entries": 1000
    }
}
```

---

## 🧠 Memória Persistente

O sistema mantém estado entre sessões:

```python
# No código dos agentes
memory.set("rtc_agent", "ultimo_calculo", {"dados": "valor"}, tags=["calculo"])
valor = memory.get("rtc_agent", "ultimo_calculo")
resultados = memory.search(agent="rtc_agent", tags=["calculo"])
```

Arquivo: `/e/rtc-unificado/agentic-system/memory/agent_memory.json`

---

## 🔐 Segurança & Boas Práticas

- ✅ **Todas as APIs em localhost** — não expostas externamente
- ✅ **Submódulos Git** — repositórios originais não commitados no pai
- ✅ **Memória ≠ Log** — persistência estruturada, não debug

---

## 🛠️ Desenvolvimento

### Testes

```bash
# Verificar imports e health checks
cd /e/rtc-unificado/agentic-system
python3 -c "
from main import RTCAgenticSystem
system = RTCAgenticSystem()
print(system.orchestrator.process({'action': 'status_sistema', 'params': {}}))
"
```

---

## 📋 Checklist de Produção

- [x] 2 agentes registrados (orchestrator + rtc_agent)
- [x] CLI funcional (ajuda, status, sair, chat NL)
- [x] API HTTP respondendo em `/health` e `POST /`
- [x] Memória persistindo em `memory/agent_memory.json`
- [x] Health check agregado dos 3 serviços funcionando
- [x] Roteamento NL testado para os 3 domínios RTC
- [x] Integração verificada com cada calculadora Receita Federal
- [x] `.gitignore` exclui `__pycache__/`, `memory/`, submódulos
- [x] README com exemplos CLI e API
- [x] `run.sh` executável com 3 modos

---

## 🤝 Contribuindo

1. Fork o repositório
2. Crie branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'feat: descrição da feature'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra Pull Request

---

## 📄 Licença

| Componente | Licença |
|------------|---------|
| **Sistema Agentico (este repo)** | MIT |
| **Calculadoras RTC (Receita Federal)** | MIT |

---

## 📞 Suporte & Contato

- **Issues**: [GitHub Issues](https://github.com/ShunWalChin/rtc-unificado/issues)
- **FAT Tech**: [fattech.com.br](https://fattech.com.br)
- **Documentação Agentic**: [`agentic-system/README.md`](agentic-system/README.md)

---

## 🏷️ Tags & Topics

`agentic-system` `orchestrator` `rtc` `receita-federal` `calculadora-tributos` `danfse` `simples-nacional` `regime-regular` `python` `java` `go` `microservices` `multi-agent` `llm-agents`

---

> **Desenvolvido pela FAT Tech** — Unificando as 3 calculadoras oficiais da Receita Federal (DANFSe, Simples Nacional, Regime Regular) em um único sistema agentico inteligente com linguagem natural.