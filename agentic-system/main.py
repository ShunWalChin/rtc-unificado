#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAT Tech - Sistema Agentico Unificado
Orquestra: RTC (3 calculadoras), Meta Ads BI, Clip-Watcher, Diagnóstico Ânima
"""

from __future__ import annotations
import os
import json
import asyncio
import uuid
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable, Union
from enum import Enum
from pathlib import Path
import logging
import subprocess
import requests
from datetime import datetime
import hashlib

# =============================================================================
# CONFIGURAÇÃO
# =============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s')
logger = logging.getLogger("fat-agentic")

CONFIG = {
    "apis": {
        "danfse": "http://localhost:8080",
        "simples": "http://localhost:8082",
        "regime": "http://localhost:8080"
    },
    "paths": {
        "rtc_base": "/e/rtc-unificado",
        "clip_watcher": "/f/clip-watcher",
        "meta_ads": "/e/rtc-unificado/calculadora-rtc-simples-nacional/../meta-ads",
        "anima_docs": "/h/Documentos/fat-ops/conhecimento/kit-master-anima"
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
    META_ADS = "meta_ads"
    CLIP_WATCHER = "clip_watcher"
    ANIMA = "anima"
    ANALYZER = "analyzer"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_APPROVAL = "needs_approval"

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
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    agent_type: AgentType = AgentType.ORCHESTRATOR
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    requires_approval: bool = False
    approval_reason: str = ""

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

    def set(self, agent: str, key: str, value: Any, tags: List[str] = None):
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

    def search(self, agent: str = None, tags: List[str] = None) -> List[MemoryEntry]:
        results = self.entries
        if agent:
            results = [e for e in results if e.agent == agent]
        if tags:
            results = [e for e in results if any(t in e.tags for t in tags)]
        return results

    def clear(self, agent: str = None):
        if agent:
            self.entries = [e for e in self.entries if e.agent != agent]
        else:
            self.entries = []
        self._save()

memory = AgentMemory(CONFIG["memory"]["path"])

# =============================================================================
# BARRAMENTO DE MENSAGENS
# =============================================================================

class MessageBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.history: List[AgentMessage] = []

    def subscribe(self, agent_name: str, handler: Callable):
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

    def request(self, from_agent: str, to_agent: str, payload: Dict) -> Any:
        msg = AgentMessage(from_agent=from_agent, to_agent=to_agent, payload=payload)
        self.publish(msg)
        # Para requests síncronos, aguardamos resposta (simplificado)
        return {"status": "sent", "message_id": msg.id}

message_bus = MessageBus()

# =============================================================================
# CLASSE BASE DE AGENTE
# =============================================================================

class BaseAgent(ABC):
    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type
        self.tools: Dict[str, Callable] = {}
        self.running = False
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

    def add_task(self, task: Task):
        task.agent_type = self.agent_type
        memory.set(self.name, f"task_{task.id}", asdict(task))

    def get_task(self, task_id: str) -> Optional[Task]:
        data = memory.get(self.name, f"task_{task_id}")
        return Task(**data) if data else None

    def update_task(self, task: Task):
        task.updated_at = datetime.now().isoformat()
        memory.set(self.name, f"task_{task.id}", asdict(task))

# =============================================================================
# FERRAMENTAS RTC
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

rtc_api = RTCAPI()

# =============================================================================
# AGENTE RTC
# =============================================================================

class RTCAgent(BaseAgent):
    def __init__(self):
        super().__init__("rtc_agent", AgentType.RTC)
        self.register_tool("health_check", self._health_check)
        self.register_tool("gerar_danfse", self._gerar_danfse)
        self.register_tool("calcular_simples", self._calcular_simples)
        self.register_tool("calcular_regime", self._calcular_regime)
        self.register_tool("listar_atividades", self._listar_atividades)
        self.register_tool("base_calculo", self._base_calculo)
        self.register_tool("validar_xml", self._validar_xml)

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

# =============================================================================
# FERRAMENTAS META ADS
# =============================================================================

class MetaAdsTools:
    def __init__(self):
        self.base_path = Path(CONFIG["paths"]["meta_ads"])

    def listar_contas(self) -> Dict:
        contas_file = self.base_path / "contas-monitoradas.json"
        if contas_file.exists():
            with open(contas_file, 'r', encoding='utf-8') as f:
                return {"ok": True, "data": json.load(f)}
        return {"ok": False, "error": "Arquivo de contas não encontrado"}

    def gerar_dashboard(self, account_id: str, dias: int = 15) -> Dict:
        script = self.base_path / "tools" / "bi_v2.py"
        if script.exists():
            try:
                result = subprocess.run(
                    ["python3", str(script), "manha", "--conta", account_id, "--dias", str(dias)],
                    capture_output=True, text=True, timeout=120, cwd=str(self.base_path)
                )
                return {"ok": result.returncode == 0, "output": result.stdout, "error": result.stderr}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Script bi_v2.py não encontrado"}

    def listar_dashboards(self, data: Optional[str] = None) -> Dict:
        dash_dir = self.base_path / "dashboards-bi"
        if data:
            dash_dir = dash_dir / data
        if dash_dir.exists():
            files = list(dash_dir.glob("*.html"))
            return {"ok": True, "dashboards": [f.name for f in files]}
        return {"ok": False, "error": "Diretório de dashboards não encontrado"}

meta_ads_tools = MetaAdsTools()

# =============================================================================
# AGENTE META ADS
# =============================================================================

class MetaAdsAgent(BaseAgent):
    def __init__(self):
        super().__init__("meta_ads_agent", AgentType.META_ADS)
        self.register_tool("listar_contas", self._listar_contas)
        self.register_tool("gerar_dashboard", self._gerar_dashboard)
        self.register_tool("listar_dashboards", self._listar_dashboards)
        self.register_tool("coletar_dados", self._coletar_dados)

    def process(self, payload: Dict) -> Dict:
        action = payload.get("action")
        if action in self.tools:
            return self.tools[action](payload.get("params", {}))
        return {"ok": False, "error": f"Ação desconhecida: {action}"}

    def _listar_contas(self, params: Dict) -> Dict:
        return meta_ads_tools.listar_contas()

    def _gerar_dashboard(self, params: Dict) -> Dict:
        return meta_ads_tools.gerar_dashboard(params["account_id"], params.get("dias", 15))

    def _listar_dashboards(self, params: Dict) -> Dict:
        return meta_ads_tools.listar_dashboards(params.get("data"))

    def _coletar_dados(self, params: Dict) -> Dict:
        script = Path(CONFIG["paths"]["meta_ads"]) / "tools" / "coleta_bi.py"
        if script.exists():
            try:
                result = subprocess.run(
                    ["python3", str(script), "--data", params.get("data", datetime.now().strftime("%Y-%m-%d")), "--dias", str(params.get("dias", 8))],
                    capture_output=True, text=True, timeout=180, cwd=str(Path(CONFIG["paths"]["meta_ads"]))
                )
                return {"ok": result.returncode == 0, "output": result.stdout}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Script de coleta não encontrado"}

# =============================================================================
# FERRAMENTAS CLIP WATCHER
# =============================================================================

class ClipWatcherTools:
    def __init__(self):
        self.base_path = Path(CONFIG["paths"]["clip_watcher"])

    def iniciar_gravacao(self, canal: str, editar: bool = True, texto: str = "", marca_dagua: str = "") -> Dict:
        runner = self.base_path / "clip_watcher_runner.py"
        if not runner.exists():
            runner = Path("/f/clip-watcher/clip_watcher_runner.py")
        if runner.exists():
            try:
                cmd = ["python3", str(runner), canal]
                if editar:
                    cmd.extend(["--editar"])
                if texto:
                    cmd.extend(["--texto", texto])
                if marca_dagua:
                    cmd.extend(["--marca-dagua", marca_dagua])
                
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return {"ok": True, "pid": proc.pid, "message": f"Gravação iniciada para {canal}"}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Runner não encontrado"}

    def testar_sistema(self) -> Dict:
        runner = self.base_path / "clip_watcher_runner.py"
        if not runner.exists():
            runner = Path("/f/clip-watcher/clip_watcher_runner.py")
        if runner.exists():
            try:
                result = subprocess.run(["python3", str(runner), "--teste"], capture_output=True, text=True, timeout=30)
                return {"ok": result.returncode == 0, "output": result.stdout}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Runner não encontrado"}

    def simular(self) -> Dict:
        runner = self.base_path / "clip_watcher_runner.py"
        if not runner.exists():
            runner = Path("/f/clip-watcher/clip_watcher_runner.py")
        if runner.exists():
            try:
                result = subprocess.run(["python3", str(runner), "--simular"], capture_output=True, text=True, timeout=60)
                return {"ok": result.returncode == 0, "output": result.stdout}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "Runner não encontrado"}

    def listar_clipes(self) -> Dict:
        clipes_dir = self.base_path / "clipes"
        if not clipes_dir.exists():
            clipes_dir = Path("/f/clip-watcher/clipes")
        if clipes_dir.exists():
            files = list(clipes_dir.glob("*.mp4"))
            verticais = list((clipes_dir / "verticais").glob("*.mp4")) if (clipes_dir / "verticais").exists() else []
            return {"ok": True, "clipes": [f.name for f in files], "verticais": [f.name for f in verticais]}
        return {"ok": False, "error": "Diretório de clipes não encontrado"}

    def parar_gravacao(self, pid: int) -> Dict:
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
            return {"ok": True, "message": f"Processo {pid} finalizado"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

clip_watcher_tools = ClipWatcherTools()

# =============================================================================
# AGENTE CLIP WATCHER
# =============================================================================

class ClipWatcherAgent(BaseAgent):
    def __init__(self):
        super().__init__("clip_watcher_agent", AgentType.CLIP_WATCHER)
        self.register_tool("iniciar_gravacao", self._iniciar_gravacao)
        self.register_tool("testar_sistema", self._testar_sistema)
        self.register_tool("simular", self._simular)
        self.register_tool("listar_clipes", self._listar_clipes)
        self.register_tool("parar_gravacao", self._parar_gravacao)

    def process(self, payload: Dict) -> Dict:
        action = payload.get("action")
        if action in self.tools:
            return self.tools[action](payload.get("params", {}))
        return {"ok": False, "error": f"Ação desconhecida: {action}"}

    def _iniciar_gravacao(self, params: Dict) -> Dict:
        return clip_watcher_tools.iniciar_gravacao(
            params["canal"],
            params.get("editar", True),
            params.get("texto", ""),
            params.get("marca_dagua", "")
        )

    def _testar_sistema(self, params: Dict) -> Dict:
        return clip_watcher_tools.testar_sistema()

    def _simular(self, params: Dict) -> Dict:
        return clip_watcher_tools.simular()

    def _listar_clipes(self, params: Dict) -> Dict:
        return clip_watcher_tools.listar_clipes()

    def _parar_gravacao(self, params: Dict) -> Dict:
        return clip_watcher_tools.parar_gravacao(params["pid"])

# =============================================================================
# FERRAMENTAS ÂNIMA
# =============================================================================

class AnimaTools:
    def __init__(self):
        self.base_path = Path(CONFIG["paths"]["anima_docs"])

    def carregar_typeform(self) -> Dict:
        # Procurar o typeform mais recente
        typeform_paths = [
            Path("/h/Users/WalfredoFigueiredoNe/AppData/Local/hermes/profiles/fat-dev/cache/scratch/typeform-diagnostico-supermercado.html"),
            Path("/e/rtc-unificado/typeform-diagnostico-supermercado.html")
        ]
        for p in typeform_paths:
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    return {"ok": True, "html": f.read(), "path": str(p)}
        return {"ok": False, "error": "Typeform não encontrado"}

    def processar_diagnostico(self, respostas: Dict) -> Dict:
        # Processa respostas do diagnóstico Ânima usando a lógica do Typeform
        try:
            # Cálculo de scores por dimensão
            dimensoes = {
                "Processo": [], "Dados": [], "Sistemas": [], "Pessoas": [], "Indicadores": []
            }
            # Simulação do cálculo baseado nas respostas
            for key, value in respostas.items():
                if isinstance(value, (int, float)) and 0 <= value <= 4:
                    # Mapear perguntas para dimensões (simplificado)
                    dimensoes["Processo"].append(value)
            
            scores = {}
            for dim, vals in dimensoes.items():
                scores[dim] = sum(vals) / len(vals) if vals else 0
            
            # ICE (Impacto, Confiança, Esforço) - Top 3
            ice_scores = {
                "CXA": scores.get("Processo", 0) * 100,
                "GES": scores.get("Dados", 0) * 100,
                "COM": scores.get("Sistemas", 0) * 100
            }
            
            return {"ok": True, "scores": scores, "ice": ice_scores}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def gerar_relatorio(self, diagnostico: Dict) -> Dict:
        try:
            scores = diagnostico.get("scores", {})
            html = f"""
<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8"><title>Relatório Ânima</title>
<style>body{{font-family:Arial;margin:2rem;background:#110F0D;color:#FAFAF9}}.card{{background:#1a1a2e;padding:1rem;border-radius:8px;margin:1rem 0;border-left:4px solid #F9AB00}}h1{{color:#F9AB00}}</style></head>
<body><h1>📊 Relatório de Diagnóstico - Ânima Supermercado</h1>
<div class="card"><h2>Scores de Maturidade</h2>
{chr(10).join(f'<p><strong>{k}:</strong> {v:.2f}/4.0</p>' for k,v in scores.items())}
</div><div class="card"><h2>Top 3 ICE</h2>
{chr(10).join(f'<p><strong>{k}:</strong> {v:.0f}</p>' for k,v in diagnostico.get("ice", {}).items())}
</div></body></html>
"""
            return {"ok": True, "html": html}
        except Exception as e:
            return {"ok": False, "error": str(e)}

anima_tools = AnimaTools()

# =============================================================================
# AGENTE ÂNIMA
# =============================================================================

class AnimaAgent(BaseAgent):
    def __init__(self):
        super().__init__("anima_agent", AgentType.ANIMA)
        self.register_tool("carregar_typeform", self._carregar_typeform)
        self.register_tool("processar_diagnostico", self._processar_diagnostico)
        self.register_tool("gerar_relatorio", self._gerar_relatorio)

    def process(self, payload: Dict) -> Dict:
        action = payload.get("action")
        if action in self.tools:
            return self.tools[action](payload.get("params", {}))
        return {"ok": False, "error": f"Ação desconhecida: {action}"}

    def _carregar_typeform(self, params: Dict) -> Dict:
        return anima_tools.carregar_typeform()

    def _processar_diagnostico(self, params: Dict) -> Dict:
        return anima_tools.processar_diagnostico(params["respostas"])

    def _gerar_relatorio(self, params: Dict) -> Dict:
        return anima_tools.gerar_relatorio(params["diagnostico"])

# =============================================================================
# AGENTE ANALISADOR
# =============================================================================

class AnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__("analyzer_agent", AgentType.ANALYZER)
        self.register_tool("analisar_tendencia", self._analisar_tendencia)
        self.register_tool("correlacionar", self._correlacionar)
        self.register_tool("resumir", self._resumir)

    def process(self, payload: Dict) -> Dict:
        action = payload.get("action")
        if action in self.tools:
            return self.tools[action](payload.get("params", {}))
        return {"ok": False, "error": f"Ação desconhecida: {action}"}

    def _analisar_tendencia(self, params: Dict) -> Dict:
        data = params.get("data", [])
        if not data:
            return {"ok": False, "error": "Dados vazios"}
        # Análise simples de tendência
        nums = [float(x) for x in data if isinstance(x, (int, float))]
        if len(nums) < 2:
            return {"ok": True, "tendencia": "insuficiente", "media": nums[0] if nums else 0}
        diff = nums[-1] - nums[0]
        tendencia = "alta" if diff > 0 else "baixa" if diff < 0 else "estavel"
        return {"ok": True, "tendencia": tendencia, "variacao": diff, "media": sum(nums)/len(nums)}

    def _correlacionar(self, params: Dict) -> Dict:
        x = params.get("x", [])
        y = params.get("y", [])
        if len(x) != len(y) or len(x) < 2:
            return {"ok": False, "error": "Dados incompatíveis"}
        n = len(x)
        sum_x, sum_y = sum(x), sum(y)
        sum_xy = sum(a*b for a,b in zip(x,y))
        sum_x2, sum_y2 = sum(a*a for a in x), sum(b*b for b in y)
        denom = ((n*sum_x2 - sum_x**2) * (n*sum_y2 - sum_y**2))**0.5
        if denom == 0:
            return {"ok": True, "correlacao": 0}
        r = (n*sum_xy - sum_x*sum_y) / denom
        return {"ok": True, "correlacao": round(r, 4)}

    def _resumir(self, params: Dict) -> Dict:
        text = params.get("text", "")
        # Resumo simples: primeiras 3 frases
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        return {"ok": True, "resumo": '. '.join(sentences[:3]) + '.'}

# =============================================================================
# ORQUESTRADOR PRINCIPAL
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
        # Usado internamente
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
                # Passar resultado para próximo step se necessário
                if step.get("pass_to_next"):
                    step_params["previous_result"] = result
            else:
                results[f"{agent_name}.{action}"] = {"ok": False, "error": f"Agente {agent_name} não encontrado"}
        return {"ok": True, "results": results}

    def _chat(self, params: Dict) -> Dict:
        message = params.get("message", "").lower()
        
        # Roteamento inteligente baseado em palavras-chave
        if any(kw in message for kw in ["danfse", "xml", "nfse", "pdf"]):
            return self._route_to_agent("rtc_agent", "gerar_danfse", params)
        elif any(kw in message for kw in ["simples", "cbs", "ibs", "anexo"]):
            return self._route_to_agent("rtc_agent", "calcular_simples", params)
        elif any(kw in message for kw in ["regime", "regular", "imposto seletivo"]):
            return self._route_to_agent("rtc_agent", "calcular_regime", params)
        elif any(kw in message for kw in ["status", "serviço", "servico", "health", "online", "rtc"]):
            return self._route_to_agent("rtc_agent", "health_check", params)
        elif any(kw in message for kw in ["meta", "ads", "dashboard", "campanha", "anúncio", "anuncio"]):
            return self._route_to_agent("meta_ads_agent", "listar_dashboards", params)
        elif any(kw in message for kw in ["twitch", "live", "clip", "corte", "shorts", "reels", "gravação", "gravacao"]):
            return self._route_to_agent("clip_watcher_agent", "listar_clipes", params)
        elif any(kw in message for kw in ["ânima", "anima", "diagnóstico", "diagnostico", "supermercado", "typeform"]):
            return self._route_to_agent("anima_agent", "carregar_typeform", params)
        else:
            return {"ok": True, "response": "Olá! Sou o orquestrador da FAT Tech. Posso ajudar com:\n- Calculadoras RTC (DANFSe, Simples Nacional, Regime Regular)\n- Dashboards Meta Ads\n- Clip-Watcher Twitch\n- Diagnóstico Ânima\n\nO que você precisa?"}

    def _route_to_agent(self, agent_name: str, action: str, params: Dict) -> Dict:
        if agent_name in self.agents:
            # Extrair parâmetros relevantes da mensagem
            result = self.agents[agent_name].process({"action": action, "params": params.get("params", {})})
            return {"ok": True, "agent": agent_name, "action": action, "result": result}
        return {"ok": False, "error": f"Agente {agent_name} não disponível"}

# =============================================================================
# SISTEMA PRINCIPAL
# =============================================================================

class AgenticSystem:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self._setup_agents()

    def _setup_agents(self):
        # Criar e registrar todos os agentes
        agents = [
            RTCAgent(),
            MetaAdsAgent(),
            ClipWatcherAgent(),
            AnimaAgent(),
            AnalyzerAgent()
        ]
        for agent in agents:
            self.orchestrator.register_agent(agent)

    def run_cli(self):
        print("""
╔══════════════════════════════════════════════════════════════╗
║     FAT TECH - SISTEMA AGENTICO UNIFICADO                   ║
║     RTC | Meta Ads | Clip-Watcher | Ânima                   ║
╚══════════════════════════════════════════════════════════════╝
Digite 'sair' para encerrar | 'ajuda' para comandos
""")
        while True:
            try:
                user_input = input("\n🤖 FAT Agentic > ").strip()
                if user_input.lower() in ['sair', 'exit', 'quit']:
                    print("Encerrando...")
                    break
                elif user_input.lower() in ['ajuda', 'help']:
                    self._show_help()
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

    def _show_help(self):
        print("""
COMANDOS DISPONÍVEIS:
  status          - Mostra status de todos os agentes
  ajuda           - Mostra esta ajuda
  sair            - Encerra o sistema

EXEMPLOS DE PERGUNTAS:
  "Gerar DANFSe do arquivo notas.xml"
  "Calcular Simples Nacional para estes itens: [...]"
  "Calcular Regime Regular para NCM 24021000"
  "Mostrar dashboards Meta Ads de hoje"
  "Iniciar gravação da live do alanzoka"
  "Listar clipes gerados"
  "Carregar diagnóstico Ânima"
  "Analisar tendência dos dados: [1,2,3,4,5]"
""")

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
        import urllib.parse

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
                    self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass

        print(f"API rodando em http://{host}:{port}")
        HTTPServer((host, port), APIHandler).serve_forever()

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys
    system = AgenticSystem()
    
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        system.run_api()
    else:
        system.run_cli()