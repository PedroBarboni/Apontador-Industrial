"""
totvs_api.py - Integração com TOTVS Protheus (MATA250 - Produções)

CONFIGURAÇÃO:


        TOTVS_URL      → Endereço do servidor REST
        TOTVS_USUARIO  → Usuário de acesso à API
        TOTVS_SENHA    → Senha de acesso à API

COMO FUNCIONA:
    Ao salvar um apontamento, o sistema chama `enviar_apontamento()`.
    Se o envio for bem-sucedido  → status = ENVIADO
    Se falhar (rede, TOTVS fora) → status = ERRO  (salvo localmente, pode reenviar depois)
"""

import requests
from app import database as db

TOTVS_URL     = ""   # Ex: "http://192.168.1.10:8080"
TOTVS_USUARIO = ""   # Ex: "admin"
TOTVS_SENHA   = ""   # Ex: "totvs123"

TIMEOUT_SEGUNDOS = 10

# =============================================================================
# FUNÇÕES INTERNAS
# =============================================================================

def _configurado() -> bool:
    """Verifica se as configurações mínimas foram preenchidas."""
    return bool(TOTVS_URL and TOTVS_USUARIO and TOTVS_SENHA)


def _headers() -> dict:
    """Monta os headers da requisição.

    O TOTVS REST aceita Basic Auth (usuário + senha).
    Se o seu ambiente usar Token/API Key, o TI vai informar o header correto,
    e você substitui esta função.

    Exemplo com Token:
        return {"Authorization": "Bearer SEU_TOKEN", "Content-Type": "application/json"}
    """
    import base64
    credencial = base64.b64encode(f"{TOTVS_USUARIO}:{TOTVS_SENHA}".encode()).decode()
    return {
        "Authorization": f"Basic {credencial}",
        "Content-Type": "application/json",
    }


def _montar_payload(apontamento_id: int) -> dict:
    """Monta o payload com os campos exigidos pelo TOTVS (MATA250).

    Campos enviados (conforme tela Produções - INCLUIR):
        Ord Producao  → op
        Quantidade    → quantidade
        Perda         → perda

    Caso o TI informe nomes de campos diferentes, ajuste apenas aqui.
    """
    apt = db.buscar_apontamento_por_id(apontamento_id)
    if not apt:
        raise ValueError(f"Apontamento ID {apontamento_id} não encontrado no banco local.")

    return {
        "D3_OP":   str(apt.get("op", "")).strip(),
        "D3_QUANT": float(apt.get("quantidade", 0)),
        "D3_PERDA": float(apt.get("perda", 0)),
    }


# =============================================================================
# FUNÇÃO PRINCIPAL — chamada pelo main.py ao salvar
# =============================================================================

def enviar_apontamento(apontamento_id: int) -> dict:
    """Envia o apontamento ao TOTVS Protheus via REST.

    Retorna:
        {"sucesso": True,  "mensagem": "Enviado com sucesso."}
        {"sucesso": False, "mensagem": "Descrição do erro."}

    O status no banco é atualizado automaticamente:
        ENVIADO → sucesso
        ERRO    → falha
    """

    # 1. Verifica se foi configurado
    if not _configurado():
        db.marcar_status_totvs(apontamento_id, "ERRO")
        return {
            "sucesso": False,
            "mensagem": (
                "TOTVS não configurado.\n"
                "Preencha TOTVS_URL, TOTVS_USUARIO e TOTVS_SENHA no arquivo totvs_api.py."
            ),
        }

    # 2. Monta o payload
    try:
        payload = _montar_payload(apontamento_id)
    except Exception as e:
        db.marcar_status_totvs(apontamento_id, "ERRO")
        return {"sucesso": False, "mensagem": f"Erro ao montar dados: {e}"}

    # 3. Envia ao TOTVS
    url = f"{TOTVS_URL.rstrip('/')}/rest/movpro/v1/producoes"

    try:
        resposta = requests.post(
            url,
            json=payload,
            headers=_headers(),
            timeout=TIMEOUT_SEGUNDOS,
        )

        if resposta.status_code in (200, 201):
            db.marcar_status_totvs(apontamento_id, "ENVIADO")
            return {"sucesso": True, "mensagem": "Apontamento enviado ao TOTVS com sucesso."}

        # TOTVS retornou erro HTTP
        try:
            detalhe = resposta.json().get("errorMessage") or resposta.text
        except Exception:
            detalhe = resposta.text

        db.marcar_status_totvs(apontamento_id, "ERRO")
        return {
            "sucesso": False,
            "mensagem": f"TOTVS retornou erro {resposta.status_code}:\n{detalhe}",
        }

    except requests.exceptions.ConnectionError:
        db.marcar_status_totvs(apontamento_id, "ERRO")
        return {
            "sucesso": False,
            "mensagem": (
                "Não foi possível conectar ao TOTVS.\n"
                "Verifique se o servidor está acessível e o endereço está correto."
            ),
        }
    except requests.exceptions.Timeout:
        db.marcar_status_totvs(apontamento_id, "ERRO")
        return {
            "sucesso": False,
            "mensagem": f"Tempo de resposta excedido ({TIMEOUT_SEGUNDOS}s). O TOTVS pode estar lento.",
        }
    except Exception as e:
        db.marcar_status_totvs(apontamento_id, "ERRO")
        return {"sucesso": False, "mensagem": f"Erro inesperado: {e}"}


# =============================================================================
# REENVIO DE PENDENTES — para usar no botão "Reenviar para TOTVS"
# =============================================================================

def reenviar_pendentes() -> dict:
    """Tenta reenviar todos os apontamentos com status PENDENTE ou ERRO.

    Retorna:
        {"enviados": 3, "erros": 1, "detalhes": [...]}
    """
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT id FROM apontamentos WHERE status_envio_totvs IN ('PENDENTE','ERRO') ORDER BY criado_em"
    ).fetchall()
    conn.close()

    enviados = 0
    erros = 0
    detalhes = []

    for row in rows:
        resultado = enviar_apontamento(row["id"])
        if resultado["sucesso"]:
            enviados += 1
        else:
            erros += 1
        detalhes.append({"id": row["id"], **resultado})

    return {"enviados": enviados, "erros": erros, "detalhes": detalhes}