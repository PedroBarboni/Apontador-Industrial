from datetime import datetime, timedelta


def calcular_tempo(inicio: str, fim: str) -> str:
    try:
        fmt = "%H:%M"
        t_ini = datetime.strptime((inicio or "00:00").strip(), fmt)
        t_fim = datetime.strptime((fim or "00:00").strip(), fmt)
        if t_fim < t_ini:
            t_fim += timedelta(days=1)
        minutos = int((t_fim - t_ini).total_seconds() // 60)
        return minutos_para_tempo(minutos)
    except Exception:
        return "00:00"


def tempo_para_minutos(tempo: str) -> int:
    try:
        h, m = (tempo or "00:00").strip().split(":")[:2]
        return int(h) * 60 + int(m)
    except Exception:
        return 0


def minutos_para_tempo(minutos: int) -> str:
    minutos = max(0, int(minutos or 0))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def calcular_resumo(hora_inicio: str, hora_fim: str, paradas: list) -> dict:
    total_min = tempo_para_minutos(calcular_tempo(hora_inicio, hora_fim))
    parado_min = 0
    for p in paradas or []:
        parado_min += tempo_para_minutos(calcular_tempo(p.get("inicio", "00:00"), p.get("fim", "00:00")))
    produzindo_min = max(0, total_min - parado_min)
    return {
        "tempo_total": minutos_para_tempo(total_min),
        "tempo_parado": minutos_para_tempo(parado_min),
        "tempo_produzindo": minutos_para_tempo(produzindo_min),
        "tempo_total_min": total_min,
        "tempo_parado_min": parado_min,
        "tempo_produzindo_min": produzindo_min,
    }


def calcular_pecas_boas(quantidade: int, perda: int) -> int:
    return max(0, int(quantidade or 0) - int(perda or 0))


def calcular_percentual_perda(quantidade: int, perda: int) -> float:
    qtd = int(quantidade or 0)
    if qtd <= 0:
        return 0.0
    return round((int(perda or 0) / qtd) * 100, 2)


def is_pre_acabado(maquina: str, produto: str) -> bool:
    maq = (maquina or "").upper().strip()
    prod = (produto or "").upper().strip()
    if maq in ("SOLDA 1", "SOLDA 2"):
        return True
    if maq.startswith("LAMI") and "P. CABO" in prod and "LAMINA" in prod:
        return True
    if maq.startswith("CNC") and "TERMINAL AT" in prod and "USINAGEM" in prod:
        return True
    return False


def formatar_data_br(data_iso: str) -> str:
    try:
        return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return data_iso or ""


def data_br_para_iso(data_br: str) -> str:
    try:
        return datetime.strptime(data_br, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return data_br or ""


def data_hoje_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")
