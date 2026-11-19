#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificação de saúde do sistema agentico FAT Tech.
Executa health checks de todos os componentes.
"""

import sys
import subprocess
import requests
from pathlib import Path


def check_python_imports() -> bool:
    """Verifica se todos os imports do main.py funcionam."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from main import (
            AgenticSystem, OrchestratorAgent, RTCAgent, MetaAdsAgent,
            ClipWatcherAgent, AnimaAgent, AnalyzerAgent,
            AgentType, TaskStatus, AgentMessage, Task, MemoryEntry,
            BaseAgent, MessageBus, AgentMemory, RTCAPI, memory, message_bus
        )
        print("✓ Imports do main.py OK")
        return True
    except Exception as e:
        print(f"✗ Erro nos imports: {e}")
        return False


def check_agent_registration() -> bool:
    """Verifica se todos os 6 agentes são registrados."""
    try:
        from main import AgenticSystem
        system = AgenticSystem()
        agents = list(system.orchestrator.agents.keys())
        expected = [
            "rtc_agent", "meta_ads_agent", "clip_watcher_agent",
            "anima_agent", "analyzer_agent", "orchestrator"
        ]
        missing = set(expected) - set(agents)
        extra = set(agents) - set(expected)
        
        if missing:
            print(f"✗ Agentes faltando: {missing}")
            return False
        if extra:
            print(f"⚠ Agentes extras: {extra}")
        
        print(f"✓ Todos os {len(agents)} agentes registrados: {agents}")
        return True
    except Exception as e:
        print(f"✗ Erro no registro de agentes: {e}")
        return False


def check_agent_tools() -> bool:
    """Verifica se cada agente tem as ferramentas esperadas."""
    try:
        from main import AgenticSystem
        system = AgenticSystem()
        
        expected_tools = {
            "rtc_agent": ["health_check", "gerar_danfse", "calcular_simples",
                           "calcular_regime", "listar_atividades", "base_calculo", "validar_xml"],
            "meta_ads_agent": ["listar_contas", "gerar_dashboard", "listar_dashboards", "coletar_dados"],
            "clip_watcher_agent": ["iniciar_gravacao", "testar_sistema", "simular", "listar_clipes", "parar_gravacao"],
            "anima_agent": ["carregar_typeform", "processar_diagnostico", "gerar_relatorio"],
            "analyzer_agent": ["analisar_tendencia", "correlacionar", "resumir"],
            "orchestrator": ["registrar_agente", "executar_workflow", "status_sistema", "chat"],
        }
        
        all_ok = True
        for agent_name, tools in expected_tools.items():
            if agent_name in system.orchestrator.agents:
                agent = system.orchestrator.agents[agent_name]
                missing = set(tools) - set(agent.tools.keys())
                if missing:
                    print(f"✗ {agent_name}: ferramentas faltando: {missing}")
                    all_ok = False
                else:
                    print(f"✓ {agent_name}: {len(tools)} ferramentas OK")
            else:
                print(f"✗ {agent_name}: agente não encontrado")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"✗ Erro na verificação de ferramentas: {e}")
        return False


def check_memory_persistence() -> bool:
    """Verifica se a memória persiste corretamente."""
    try:
        from main import AgenticSystem, memory
        system = AgenticSystem()
        
        # Teste de escrita/leitura
        test_key = "test_verify_" + str(__import__('uuid').uuid4())[:8]
        test_value = {"test": True, "timestamp": "2026-11-19"}
        
        memory.set("verify_agent", test_key, test_value, tags=["test"])
        retrieved = memory.get("verify_agent", test_key)
        
        if retrieved and retrieved.get("test") is True:
            print("✓ Memória persistente: escrita/leitura OK")
            # Limpar
            entries_before = len(memory.entries)
            memory.clear("verify_agent")
            print(f"✓ Memória: limpeza OK ({entries_before} → {len(memory.entries)} entries)")
            return True
        else:
            print("✗ Memória: falha na leitura após escrita")
            return False
    except Exception as e:
        print(f"✗ Erro na memória: {e}")
        return False


def check_message_bus() -> bool:
    """Verifica se o message bus funciona."""
    try:
        from main import message_bus, AgentMessage
        
        received = []
        def handler(msg):
            received.append(msg)
        
        message_bus.subscribe("test_agent", handler)
        msg = AgentMessage(from_agent="test", to_agent="test_agent", type="request", payload={"test": True})
        message_bus.publish(msg)
        
        if len(received) == 1 and received[0].payload.get("test") is True:
            print("✓ MessageBus: pub/sub OK")
            return True
        else:
            print("✗ MessageBus: falha no pub/sub")
            return False
    except Exception as e:
        print(f"✗ Erro no MessageBus: {e}")
        return False


def check_rtc_services() -> bool:
    """Verifica se os serviços RTC estão respondendo (opcional)."""
    try:
        from main import RTCAPI
        api = RTCAPI()
        results = {}
        for service in ["danfse", "simples", "regime"]:
            results[service] = api.health_check(service)
        
        online = sum(1 for r in results.values() if r.get("ok"))
        print(f"⚠ RTC Services: {online}/3 online (danfse: {results['danfse'].get('ok')}, simples: {results['simples'].get('ok')}, regime: {results['regime'].get('ok')})")
        print("  (Inicie com ./start-all.sh se estiverem offline)")
        return True  # Não falha se offline - apenas avisa
    except Exception as e:
        print(f"✗ Erro ao verificar RTC: {e}")
        return False


def check_file_structure() -> bool:
    """Verifica estrutura de arquivos esperada."""
    base = Path(__file__).parent.parent
    required = [
        "main.py",
        "requirements.txt",
        "run.sh",
        "README.md",
        "memory/agent_memory.json",
    ]
    
    all_ok = True
    for f in required:
        path = base / f
        if path.exists():
            print(f"✓ {f} existe")
        else:
            print(f"✗ {f} NÃO ENCONTRADO")
            all_ok = False
    
    # Verifica se run.sh é executável
    run_sh = base / "run.sh"
    if run_sh.exists():
        import stat
        if run_sh.stat().st_mode & stat.S_IXUSR:
            print("✓ run.sh é executável")
        else:
            print("⚠ run.sh não é executável (rode: chmod +x run.sh)")
    
    return all_ok


def check_dependencies() -> bool:
    """Verifica dependências Python."""
    try:
        import requests
        print(f"✓ requests {requests.__version__}")
    except ImportError:
        print("✗ requests não instalado (pip install requests)")
        return False
    
    try:
        import dotenv
        print(f"✓ python-dotenv {dotenv.__version__}")
    except ImportError:
        print("⚠ python-dotenv não instalado (opcional)")
    
    return True


def main() -> int:
    """Executa todas as verificações."""
    print("=" * 60)
    print("FAT TECH - VERIFICAÇÃO DO SISTEMA AGENTICO")
    print("=" * 60)
    
    checks = [
        ("Estrutura de arquivos", check_file_structure),
        ("Dependências Python", check_dependencies),
        ("Imports do main.py", check_python_imports),
        ("Registro de agentes", check_agent_registration),
        ("Ferramentas dos agentes", check_agent_tools),
        ("Memória persistente", check_memory_persistence),
        ("Message Bus", check_message_bus),
        ("Serviços RTC (opcional)", check_rtc_services),
    ]
    
    results = []
    for name, check_fn in checks:
        print(f"\n--- {name} ---")
        try:
            ok = check_fn()
            results.append((name, ok))
        except Exception as e:
            print(f"✗ Erro inesperado em {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("RESUMO")
    print("=" * 60)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} verificações passaram")
    
    if passed == total:
        print("\n✓ SISTEMA AGENTICO PRONTO PARA USO")
        return 0
    else:
        print("\n✗ ALGUMAS VERIFICAÇÕES FALHARAM")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```