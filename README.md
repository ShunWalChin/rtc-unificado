# RTC UNIFICADO - Dashboard de Calculadoras de Tributos da Receita Federal

Este repositório consolida os 3 projetos da Receita Federal em um único dashboard web interativo:

| Projeto | Tecnologia | Porta | Função |
|---------|-----------|-------|--------|
| **gerador-danfse** | Go | 8080 | Gera PDF do DANFSe a partir de XML de NFS-e |
| **simples-nacional** | Java/Spring Boot | 8082 | Calcula CBS e IBS - Regime Simples Nacional |
| **regime-regular** | Java/Spring Boot | 8080 | Calcula CBS, IBS e Imposto Seletivo - Regime Regular |

---

## 📁 Estrutura

```
rtc-unificado/
├── index.html                      # Dashboard principal (abrir no navegador)
├── start-all.sh                    # Script de inicialização dos 3 serviços
├── verificar-ambiente.sh           # Verifica dependências (Java, Go, Docker)
├── calculadora-rtc-gerador-danfse/ # Repositório clonado (Go)
├── calculadora-rtc-simples-nacional/ # Repositório clonado (Java)
└── calculadora-rtc-regime-regular/ # Repositório clonado (Java)
```

---

## 🚀 Como Usar

### 1. Verificar Dependências

```bash
cd /e/rtc-unificado
./verificar-ambiente.sh
```

Você precisará de:
- **Java 21+** para os projetos Simples Nacional e Regime Regular
- **Go 1.27+** para o Gerador DANFSe
- **Docker** (opcional) para rodar via container

### 2. Iniciar os Serviços

```bash
cd /e/rtc-unificado
chmod +x start-all.sh
./start-all.sh
```

O script vai:
- Verificar se Java e Go estão instalados
- Iniciar os 3 serviços em background
- Abrir o dashboard automaticamente no navegador

### 3. Acessar o Dashboard

Abra o arquivo:
```
file:///e/rtc-unificado/index.html
```

Ou abra diretamente no navegador.

---

## 📋 Funcionalidades por Módulo

### 1. Gerador DANFSe (Porta 8080)
- Envia XML de NFS-e
- Gera PDF do DANFSe
- Parâmetros: STC (situação), canhoto (sim/não)
- Endpoint: `POST /api/danfse`

### 2. Simples Nacional (Porta 8082)
- Calcula CBS e IBS com observabilidade por item
- Consulta atividades vigentes por data
- Consulta códigos de erro VSN-
- Endpoints: `POST /calculadora/observabilidade/simples-nacional`

### 3. Regime Regular (Porta 8080)
- Calcula CBS, IBS e Imposto Seletivo
- Base de cálculo unificada (NF-e/NFS-e)
- Geração e validação de XML
- Consultas de dados abertos (NCM, NBS, alíquotas, CST)
- Endpoints: `POST /api/calculadora/regime-geral`

---

## 🛠️ Preparação dos Bancos de Dados (Java)

Os projetos Java (Simples Nacional e Regime Regular) exigem um banco de dados SQLite gerado via Flyway antes de iniciar.

**No diretório de cada projeto Java:**

```bash
# Linux/macOS
./mvnw flyway:migrate -Dflyway.configFiles=./flyway/flyway-pro.conf --batch-mode --errors

# Windows
mvnw.cmd flyway:migrate -Dflyway.configFiles=flyway\flyway-pro.conf --batch-mode --errors
```

Isso criará o arquivo `./calculadora/db/calculadora-pro.db` necessário para o perfil `offline`.

---

## 🧪 Testando

1. Abra o dashboard: `file:///e/rtc-unificado/index.html`
2. Clique em "Status dos Serviços" para verificar se as 3 APIs estão online
3. Preencha os formulários de cada módulo
4. Clique em "Calcular" ou "Gerar"
5. Visualize os resultados em tempo real

---

## 🤖 Sistema Agentico Unificado (NOVO)

O diretório `agentic-system/` contém um sistema completo de agentes inteligentes que orquestra **TODOS** os sistemas da FAT Tech:

| Agente | Domínio | Capacidades |
|--------|---------|-------------|
| `rtc_agent` | RTC | DANFSe, Simples Nacional, Regime Regular |
| `meta_ads_agent` | Meta Ads | Dashboards BI, coleta de dados, contas |
| `clip_watcher_agent` | Twitch | Gravação live, detecção picos, cortes, verticais |
| `anima_agent` | Ânima | Typeform diagnóstico, processamento, relatórios |
| `analyzer_agent` | Análise | Tendências, correlações, resumos |
| `orchestrator` | Orquestração | Roteamento, workflows, chat unificado |

### Inicialização do Sistema Agentico

```bash
cd /e/rtc-unificado/agentic-system
chmod +x run.sh
./run.sh
```

### Modos de Operação

1. **CLI Interativo** - Chat com linguagem natural
2. **API HTTP** (porta 8088) - Integração programática
3. **Status** - Verifica todos os agentes

### Exemplos de Uso (CLI)

```
🤖 FAT Agentic > status dos servicos rtc
🤖 FAT Agentic > calcular simples nacional para item NCM 24021000 base 1000
🤖 FAT Agentic > gerar danfse do arquivo notas.xml
🤖 FAT Agentic > mostrar dashboards meta ads de hoje
🤖 FAT Agentic > iniciar gravacao da live do alanzoka
🤖 FAT Agentic > listar clipes gerados
🤖 FAT Agentic > carregar diagnostico anima supermercado
🤖 FAT Agentic > analisar tendência: [10, 15, 12, 18, 22, 25]
```

### API HTTP

```bash
# Iniciar API
python3 main.py api

# Health check
curl http://localhost:8088/health

# Chat
curl -X POST http://localhost:8088/ \
  -H "Content-Type: application/json" \
  -d '{"action": "chat", "params": {"message": "status rtc", "params": {}}}'

# Workflow complexo
curl -X POST http://localhost:8088/ \
  -H "Content-Type: application/json" \
  -d '{
    "action": "executar_workflow",
    "params": {
      "workflow": [
        {"agent": "rtc_agent", "action": "health_check", "params": {"service": "all"}},
        {"agent": "meta_ads_agent", "action": "listar_dashboards", "params": {}},
        {"agent": "clip_watcher_agent", "action": "listar_clipes", "params": {}}
      ]
    }
  }'
```

### Arquitetura

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
                              │
                    ┌─────────▼─────────┐
                    │   MEMORY BUS      │
                    │  (JSON persistido)│
                    └───────────────────┘
```

---

## 📦 Arquivos do Projeto (ATUALIZADO)

| Arquivo | Descrição |
|---------|-----------|
| `index.html` | Dashboard único com todos os 3 módulos |
| `start-all.sh` | Script para iniciar todos os serviços |
| `verificar-ambiente.sh` | Verifica Java, Go, Docker |
| `agentic-system/` | **Sistema agentico completo** |
| `calculadora-rtc-gerador-danfse/` | Repositório original (Go) |
| `calculadora-rtc-simples-nacional/` | Repositório original (Java) |
| `calculadora-rtc-regime-regular/` | Repositório original (Java) |

---

## ⚠️ Observações

- Os 3 serviços devem estar rodando simultaneamente para o dashboard funcionar plenamente
- O bloco de JSON de entrada deve seguir o formato esperado por cada API (veja a documentação em cada repositório)
- Os bancos de dados SQLite devem ser gerados antes de iniciar os projetos Java
- Todas as comunicações são via HTTP localhost (não há envio de dados para servidores externos)

---

## 📄 Licença

Os códigos originais são da Receita Federal do Brasil, distribuídos sob licença MIT.
O dashboard de integração é de uso livre da FAT Tech.
