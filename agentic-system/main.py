#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAT Tech - Sistema Agentico RTC Unificado
Orquestra exclusivamente as 3 calculadoras da Receita Federal:
- calculadora-rtc-gerador-danfse (Go, porta 8080)
- calculadora-rtc-simples-nacional (Java, porta 8082)
- calculadora-rtc-regime-regular (Java, porta 8080)
"""

from __future__ import annotations
import os
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
from pathlib import Path
import logging
import requests
from datetime import datetime

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
logger = logging.getLogger("fat-rtc-agentic")

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

# =============================================================================
# MODELOS DE DADOS
# =============================================================================

class AgentType(Enum):
    ORCHESTRATOR = "orchestrator"
    RTC = "rtc"

@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_agent: str = ""
    to_agent: str = ""
    type: str = "request"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    correlation_id: str = ""

@dataclass
class MemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    agent: str = ""
    key: str = ""
    value: Any = None
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0

# =============================================================================
# MEMÓRIA PERSISTENTE
# =============================================================================

class AgentMemory:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[MemoryEntry] = []
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.entries = [MemoryEntry(**e) for e in data]
            except Exception as e:
                logger.warning(f"Erro ao carregar memória: {e}")

    def _save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in self.entries], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erro ao salvar memória: {e}")

    def set(self, agent: str, key: str, value: Any, tags: Optional[List[str]] = None):
        entry = MemoryEntry(agent=agent, key=key, value=value, tags=tags or [])
        self.entries.append(entry)
        if len(self.entries) > CONFIG["memory"]["max_entries"]:
            self.entries = self.entries[-CONFIG["memory"]["max_entries"]:]
        self._save()

    def get(self, agent: str, key: str) -> Any:
        for e in reversed(self.entries):
            if e.agent == agent and e.key == key:
                e.access_count += 1
                self._save()
                return e.value
        return None

    def search(self, agent: Optional[str] = None, tags: Optional[List[str]] = None) -> List[MemoryEntry]:
        results = self.entries
        if agent:
            results = [e for e in results if e.agent == agent]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        return results

memory = AgentMemory(CONFIG["memory"]["path"])

# =============================================================================
# BARRAMENTO DE MENSAGENS
# =============================================================================

class MessageBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.history: List[AgentMessage] = []

    def subscribe(self, agent_name: str, handler: Callable[[AgentMessage], None]):
        if agent_name not in self.subscribers:
            self.subscribers[agent_name] = []
        self.subscribers[agent_name].append(handler)

    def publish(self, message: AgentMessage):
        self.history.append(message)
        if message.to_agent in self.subscribers:
            for handler in self.subscribers[message.to_agent]:
                try:
                    handler(message)
                except Exception as e:
                    logger.error(f"Erro no handler de {message.to_agent}: {e}")

message_bus = MessageBus()

# =============================================================================
# CLASSE BASE DE AGENTE
# =============================================================================

class BaseAgent(ABC):
    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type
        self.tools: Dict[str, Callable] = {}
        message_bus.subscribe(name, self._handle_message)

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    def _handle_message(self, message: AgentMessage):
        if message.type == "request":
            response = self.process(message.payload)
            if message.correlation_id:
                message_bus.publish(AgentMessage(
                    from_agent=self.name,
                    to_agent=message.from_agent,
                    type="response",
                    payload=response,
                    correlation_id=message.correlation_id
                ))

    @abstractmethod
    def process(self, payload: Dict) -> Dict:
        pass

# =============================================================================
# CLIENTE API RTC
# =============================================================================

class RTCAPI:
    def __init__(self):
        self.base_urls = CONFIG["apis"]

    def health_check(self, service: str) -> Dict:
        url = self.base_urls.get(service)
        if not url:
            return {"ok": False, "error": f"Serviço {service} não configurado"}
        try:
            endpoints = {
                "danfse": "/health/live",
                "simples": "/versao",
                "regime": "/api/calculadora/versao"
            }
            resp = requests.get(f"{url}{endpoints.get(service, '/health/live')}", timeout=5)
            return {"ok": resp.ok, "status": resp.status_code, "service": service}
        except Exception as e:
            return {"ok": False, "error": str(e), "service": service}

    def gerar_danfse(self, xml_path: str, stc: int = 0, canhoto: bool = True) -> Dict:
        try:
            with open(xml_path, 'rb') as f:
                files = {'file': (os.path.basename(xml_path), f, 'application/xml')}
                resp = requests.post(
                    f"{self.base_urls['danfse']}/api/danfse",
                    params={'stc': stc, 'cano': str(canhoto).lower()},
                    files=files,
                    timeout=30
                )
            if resp.ok:
                return {"ok": True, "pdf": resp.content, "size": len(resp.content)}
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def calcular_simples(self, itens: List[Dict]) -> Dict:
        try:
            resp = requests.post(
                f"{self.base_urls['simples']}/calculadora/observabilidade/simples-nacional",
                json=itens,
                timeout=30
            )
            if resp.ok:
                return {"ok": True, "data": resp.json()}
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def calcular_regime(self, itens: List[Dict], municipio: str = "4314902", uf: str = "RS", tp_doc: str = "55") -> Dict:
        try:
            resp = requests.post(
                f"{self.base_urls['regime']}/api/calculadora/observabilidade/regime-geral",
                params={'municipio': municipio, 'uf': uf, 'tpDoc': tp_doc},
                json=itens,
                timeout=30
            )
            if resp.ok:
                return {"ok": True, "data": resp.json()}
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def listar_atividades_simples(self, data: str) -> Dict:
        try:
            resp = requests.get(f"{self.base_urls['simples']}/calculadora/simples-nacional/atividades", params={'data': data}, timeout=10)
            if resp.ok:
                return {"ok": True, "data": resp.json()}
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def base_calculo_unificada(self, payload: Dict) -> Dict:
        try:
            resp = requests.post(f"{self.base_urls['regime']}/api/calculadora/base-calculo/base-calculo-unificada", json=payload, timeout=30)
            if resp.ok:
                return {"ok": True, "data": resp.json()}
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def validar_xml(self, xml: str, tipo: str = "nfe", subtipo: str = "grupo") -> Dict:
        try:
            resp = requests.post(
                f"{self.base_urls['regime']}/api/calculadora/xml/validate",
                params={'tipo': tipo, 'subtipo': subtipo},
                data=xml.encode('utf-8'),
                headers={'Content-Type': 'application/xml'},
                timeout=15
            )
            if resp.ok:
                return {"ok": True, "data": resp.json()}
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def gerar_xml(self, xml: str, tipo: str = "nfe") -> Dict:
        try:
            resp = requests.post(
                f"{self.base_urls['regime']}/api/calculadora/xml/generate",
                params={'tipo': tipo},
                data=xml.encode('utf-8'),
                headers={'Content-Type': 'application/xml'},
                timeout=15
            )
            if resp.ok:
                return {"ok": True, "data": resp.json()}
            return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

rtc_api = RTCAPI()

# =============================================================================
# AGENTE RTC (ÚNICO AGENTE ESPECIALIZADO)
# =============================================================================

class RTCAgent(BaseAgent):
    """Agente único que opera as 3 calculadoras da Receita Federal."""
    
    def __init__(self):
        super().__init__("rtc_agent", AgentType.RTC)
        self.register_tool("health_check", self._health_check)
        self.register_tool("gerar_danfse", self._gerar_danfse)
        self.register_tool("calcular_simples", self._calcular_simples)
        self.register_tool("calcular_regime", self._calcular_regime)
        self.register_tool("listar_atividades", self._listar_atividades)
        self.register_tool("base_calculo", self._base_calculo)
        self.register_tool("validar_xml", self._validar_xml)
        self.register_tool("gerar_xml", self._gerar_xml)

    def process(self, payload: Dict) -> Dict:
        action = payload.get("action")
        if action in self.tools:
            return self.tools[action](payload.get("params", {}))
        return {"ok": False, "error": f"Ação desconhecida: {action}"}

    def _health_check(self, params: Dict) -> Dict:
        service = params.get("service", "all")
        if service == "all":
            results = {}
            for s in ["danfse", "simples", "regime"]:
                results[s] = rtc_api.health_check(s)
            return {"ok": True, "results": results}
        return rtc_api.health_check(service)

    def _gerar_danfse(self, params: Dict) -> Dict:
        return rtc_api.gerar_danfse(
            params["xml_path"],
            params.get("stc", 0),
            params.get("canhoto", True)
        )

    def _calcular_simples(self, params: Dict) -> Dict:
        return rtc_api.calcular_simples(params["itens"])

    def _calcular_regime(self, params: Dict) -> Dict:
        return rtc_api.calcular_regime(
            params["itens"],
            params.get("municipio", "4314902"),
            params.get("uf", "RS"),
            params.get("tp_doc", "55")
        )

    def _listar_atividades(self, params: Dict) -> Dict:
        return rtc_api.listar_atividades_simples(params.get("data", ""))

    def _base_calculo(self, params: Dict) -> Dict:
        return rtc_api.base_calculo_unificada(params["payload"])

    def _validar_xml(self, params: Dict) -> Dict:
        return rtc_api.validar_xml(
            params["xml"],
            params.get("tipo", "nfe"),
            params.get("subtipo", "grupo")
        )

    def _gerar_xml(self, params: Dict) -> Dict:
        return rtc_api.gerar_xml(
            params["xml"],
            params.get("tipo", "nfe")
        )

# =============================================================================
# ORQUESTRADOR
# =============================================================================

class OrchestratorAgent(BaseAgent):
    def __init__(self):
        super().__init__("orchestrator", AgentType.ORCHESTRATOR)
        self.agents: Dict[str, BaseAgent] = {}
        self.register_tool("registrar_agente", self._registrar_agente)
        self.register_tool("executar_workflow", self._executar_workflow)
        self.register_tool("status_sistema", self._status_sistema)
        self.register_tool("chat", self._chat)

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name] = agent
        logger.info(f"Agente registrado: {agent.name}")

    def process(self, payload: Dict) -> Dict:
        action = payload.get("action")
        if action in self.tools:
            return self.tools[action](payload.get("params", {}))
        return {"ok": False, "error": f"Ação desconhecida: {action}"}

    def _registrar_agente(self, params: Dict) -> Dict:
        return {"ok": True, "agents": list(self.agents.keys())}

    def _status_sistema(self, params: Dict) -> Dict:
        status = {}
        for name, agent in self.agents.items():
            status[name] = {"type": agent.agent_type.value, "tools": list(agent.tools.keys())}
        return {"ok": True, "agents": status, "memory_entries": len(memory.entries)}

    def _executar_workflow(self, params: Dict) -> Dict:
        workflow = params.get("workflow", [])
        results = {}
        for step in workflow:
            agent_name = step.get("agent")
            action = step.get("action")
            step_params = step.get("params", {})
            
            if agent_name in self.agents:
                result = self.agents[agent_name].process({"action": action, "params": step_params})
                results[f"{agent_name}.{action}"] = result
            else:
                results[f"{agent_name}.{action}"] = {"ok": False, "error": f"Agente {agent_name} não encontrado"}
        return {"ok": True, "results": results}

    def _chat(self, params: Dict) -> Dict:
        message = params.get("message", "").lower()
        
        # Roteamento NL para RTC
        if any(kw in message for kw in ["status", "serviço", "servico", "health", "online", "rtc", "funcionando"]):
            return self._route_to_agent("rtc_agent", "health_check", params)
        elif any(kw in message for kw in ["danfse", "xml", "nfse", "pdf"]):
            return self._route_to_agent("rtc_agent", "gerar_danfse", params)
        elif any(kw in message for kw in ["simples", "cbs", "ibs", "anexo", "simples nacional"]):
            return self._route_to_agent("rtc_agent", "calcular_simples", params)
        elif any(kw in message for kw in ["regime", "regular", "imposto seletivo", "regime regular"]):
            return self._route_to_agent("rtc_agent", "calcular_regime", params)
        elif any(kw in message for kw in ["atividade", "atividades", "vigen", "cnae"]):
            return self._route_to_agent("rtc_agent", "listar_atividades", params)
        elif any(kw in message for kw in ["base calculo", "base de calculo", "unificada"]):
            return self._route_to_agent("rtc_agent", "base_calculo", params)
        elif any(kw in message for kw in ["validar xml", "validar", "validacao"]):
            return self._route_to_agent("rtc_agent", "validar_xml", params)
        elif any(kw in message for kw in ["gerar xml", "gerar xml"]):
            return self._route_to_agent("rtc_agent", "gerar_xml", params)
        else:
            return {"ok": True, "response": self._help_text()}

    def _route_to_agent(self, agent_name: str, action: str, params: Dict) -> Dict:
        if agent_name in self.agents:
            result = self.agents[agent_name].process({"action": action, "params": params.get("params", {})})
            return {"ok": True, "agent": agent_name, "action": action, "result": result}
        return {"ok": False, "error": f"Agente {agent_name} não disponível"}

    def _help_text(self) -> str:
        return """Olá! Sou o orquestrador do **RTC Unificado** (Receita Federal).

Posso ajudar com as 3 calculadoras:

**📄 Gerador DANFSe** (Go - porta 8080)
- "gerar danfse do arquivo notas.xml"
- "status do danfse"

**📊 Simples Nacional** (Java - porta 8082)
- "calcular simples nacional para item NCM 24021000 base 1000"
- "listar atividades simples nacional para 2026-01-15"

**⚖️ Regime Regular** (Java - porta 8080)
- "calcular regime regular para NCM 24021000 valor 5000"
- "validar xml da nfe"
- "gerar xml regime regular"

**🔧 Sistema**
- "status dos servicos rtc"
- "status do sistema"

O que você precisa?"""

# =============================================================================
# SISTEMA PRINCIPAL
# =============================================================================

class RTCAgenticSystem:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self._setup_agents()

    def _setup_agents(self):
        self.orchestrator.register_agent(RTCAgent())

    def run_cli(self):
        print("""
╔══════════════════════════════════════════════════════════════╗
║     FAT TECH - RTC UNIFICADO - SISTEMA AGENTICO             ║
║     3 Calculadoras Receita Federal: DANFSe | Simples | Regime║
╚══════════════════════════════════════════════════════════════╝
Digite 'sair' para encerrar | 'ajuda' para comandos
""")
        while True:
            try:
                user_input = input("\n🤖 RTC Agentic > ").strip()
                if user_input.lower() in ['sair', 'exit', 'quit']:
                    print("Encerrando...")
                    break
                elif user_input.lower() in ['ajuda', 'help']:
                    print(self.orchestrator._help_text())
                elif user_input.lower() == 'status':
                    result = self.orchestrator.process({"action": "status_sistema", "params": {}})
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    result = self.orchestrator.process({"action": "chat", "params": {"message": user_input, "params": {}}})
                    self._print_result(result)
            except KeyboardInterrupt:
                print("\nEncerrando...")
                break
            except Exception as e:
                print(f"Erro: {e}")

    def _print_result(self, result: Dict):
        if result.get("ok"):
            if "response" in result:
                print(f"\n{result['response']}")
            elif "result" in result:
                print(f"\n[{result.get('agent')}.{result.get('action')}]")
                print(json.dumps(result['result'], ensure_ascii=False, indent=2))
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n❌ Erro: {result.get('error')}")

    def run_api(self, host: str = "0.0.0.0", port: int = 8088):
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class APIHandler(BaseHTTPRequestHandler):
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    payload = json.loads(body)
                    result = system.orchestrator.process(payload)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode('utf-8'))

            def do_GET(self):
                if self.path == '/health':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "ok", "service": "rtc-agentic"}).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        print(f"API RTC rodando em http://{host}:{port}")
        HTTPServer((host, port), APIHandler).serve_forever()

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys
    system = RTCAgenticSystem()
    
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        system.run_api()
    else:
        system.run_cli()