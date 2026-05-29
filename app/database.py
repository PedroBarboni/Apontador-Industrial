import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:\Users\pedro.barboni\Desktop\Testes\dashboard_amt\producao.db")


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _cols(cursor, tabela):
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {r[1] for r in cursor.fetchall()}


def _add_col_if_missing(cursor, tabela, coluna, definicao):
    if coluna not in _cols(cursor, tabela):
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def init_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS maquinas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS operadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            peso_unitario REAL DEFAULT 0.0,
            processo_padrao TEXT DEFAULT '',
            prod_hora INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS motivos_parada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL UNIQUE,
            ativo INTEGER DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            hora_inicio TEXT DEFAULT '06:00',
            hora_fim TEXT DEFAULT '14:00',
            horas_produtivas REAL DEFAULT 8.80,
            ativo INTEGER DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS apontamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            maquina TEXT NOT NULL,
            op TEXT DEFAULT '', 
            produto TEXT NOT NULL,
            processo TEXT NOT NULL,
            operador TEXT NOT NULL,
            turno TEXT NOT NULL DEFAULT 'Turno A',
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            quantidade INTEGER DEFAULT 0,
            perda INTEGER DEFAULT 0,
            observacao TEXT DEFAULT '',
            tempo_produzindo TEXT DEFAULT '00:00',
            tempo_parado TEXT DEFAULT '00:00',
            tempo_total TEXT DEFAULT '00:00',
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS paradas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apontamento_id INTEGER NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fim TEXT NOT NULL,
            motivo TEXT DEFAULT '', 
            tempo_parado TEXT DEFAULT '00:00',
            FOREIGN KEY (apontamento_id) REFERENCES apontamentos(id) ON DELETE CASCADE
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    # Migração para bancos já existentes
    _add_col_if_missing(cur, "produtos", "prod_hora", "INTEGER DEFAULT 0")
    _add_col_if_missing(cur, "turnos", "horas_produtivas", "REAL DEFAULT 8.80")
    conn.commit()
    _inserir_dados_iniciais(cur, conn)
    conn.close()


def _inserir_dados_iniciais(cur, conn):
    maquinas = [
        "CNC 1", "CNC 2", "CNC 3", "CNC 4", "CNC 5",
        "FORJA 1", "FORJA 2", "FORJA 3", "FORJA 4",
        "LAMI. 1", "PH 1", "PH 2", "PP 80", "PP 110",
        "SERRA 1", "SOLDA 1", "SOLDA 2", "TORNO"
    ]
    for m in maquinas:
        cur.execute("INSERT OR IGNORE INTO maquinas (nome) VALUES (?)", (m,))

    operadores = [
        "AGUINALDO", "ALEX", "ANDERSON", "CLAUDINEI", "DANIEL",
        "DHIEGO", "EDILSON", "EDMAR", "FABIO", "GABRIEL HENRIQUE",
        "GABRIEL OLIVEIRA", "JEFERSON", "JOAO LOPES", "JOÃO BATISTA",
        "JOÃO EDUARDO", "JOÃO PEDRO", "KILBER", "LEANDRO", "MATEUS",
        "PATRICIA", "RAFAEL", "RAÍ", "REGINALDO", "RENATO", "SANDRO",
        "THIAGO ELIAS", "TIAGO", "VAGNER", "VALMIR", "VINICIUS", "WILSON"
    ]
    for o in operadores:
        cur.execute("INSERT OR IGNORE INTO operadores (nome) VALUES (?)", (o,))

    produtos_padrao = [
        # Produto, Peso unitário KG, Processo, Produção por hora
        # Pesos atualizados conforme tabela informada. A coluna de código foi ignorada.

        ("GRAMPO 160 (CORTE)", 0.270, "CORTE", 550),
        ("GRAMPO 160 (FORJA)", 0.270, "FORJA", 180),
        ("GRAMPO 160 (REBARBA)", 0.216, "REBARBA", 284),
        ("GRAMPO 160 (USINAGEM)", 0.175, "USINAGEM", 176),
        ("GRAMPO 160 (SOLDA)", 0.253, "SOLDA", 189),

        ("SPADE 160 (CORTE)", 0.323, "CORTE", 340),
        ("SPADE 160 (FORJA)", 0.323, "FORJA", 180),
        ("SPADE 160 (REBARBA)", 0.256, "REBARBA", 284),
        ("SPADE 160 (USINAGEM)", 0.214, "USINAGEM", 112),
        ("SPADE 160 (SOLDA)", 0.292, "SOLDA", 171),

        ("GRAMPO 400 (CORTE)", 0.596, "CORTE", 460),
        ("GRAMPO 400 (FORJA)", 0.596, "FORJA", 180),
        ("GRAMPO 400 (REBARBA)", 0.481, "REBARBA", 0),
        ("GRAMPO 400 (USINAGEM)", 0.376, "USINAGEM", 144),
        ("GRAMPO 400 (SOLDA)", 0.637, "SOLDA", 133),

        ("SPADE 400 (CORTE)", 0.804, "CORTE", 200),
        ("SPADE 400 (FORJA)", 0.804, "FORJA", 180),
        ("SPADE 400 (REBARBA)", 0.700, "REBARBA", 0),
        ("SPADE 400 (USINAGEM)", 0.599, "USINAGEM", 88),
        ("SPADE 400 (SOLDA)", 0.854, "SOLDA", 100),

        ("SPADE 800 (CORTE)", 2.254, "CORTE", 0),
        ("SPADE 800 (FORJA)", 2.254, "FORJA", 60),
        ("SPADE 800 (REBARBA)", 1.941, "REBARBA", 60),
        ("SPADE 800 (USINAGEM)", 1.530, "USINAGEM", 32),
        ("SPADE 800 (SOLDA)", 2.366, "SOLDA", 39),

        ("HASTE 160 (CORTE)", 0.076, "CORTE", 39),
        ("HASTE 160 (LAMINAÇÃO)", 0.076, "LAMINAÇÃO", 1000),
        ("HASTE 400 (CORTE)", 0.259, "CORTE", 0),
        ("HASTE 400 (LAMINAÇÃO)", 0.259, "LAMINAÇÃO", 800),
        ("HASTE 800 (CORTE)", 0.796, "CORTE", 32),
        ("HASTE 800 (LAMINAÇÃO)", 0.796, "LAMINAÇÃO", 39),

        ("PRESILHA L (CORTE)", 0.000, "CORTE", 800),
        ("PRESILHA INFERIOR (CORTE)", 0.000, "CORTE", 1160),

        ("P. CABO AT (CORTE)", 0.141, "CORTE", 0),
        ("P. CABO AT (REBAIXO)", 0.107, "REBAIXO", 350),
        ("P. CABO AT (FORJA)", 0.107, "FORJA", 180),
        ("P. CABO AT (REBARBA)", 0.098, "REBARBA", 0),
        ("P. CABO AT (FURO)", 0.085, "FURO", 270),
        ("P. CABO AT (LAMINAÇÃO)", 0.085, "LAMINAÇÃO", 900),

        ("P. CABO BT 160 (CORTE)", 0.262, "CORTE", 700),
        ("P. CABO BT 160 (REBAIXO)", 0.156, "REBAIXO", 222),
        ("P. CABO BT 160 (FORJA)", 0.156, "FORJA", 180),
        ("P. CABO BT 160 (REBARBA)", 0.124, "REBARBA", 180),
        ("P. CABO BT 160 (FURO)", 0.093, "FURO", 270),
        ("P. CABO BT 160 (LAMINAÇÃO)", 0.093, "LAMINAÇÃO", 900),

        ("P. CABO BT 400 (CORTE)", 0.470, "CORTE", 0),
        ("P. CABO BT 400 (REBAIXO)", 0.325, "REBAIXO", 140),
        ("P. CABO BT 400 (FORJA)", 0.325, "FORJA", 180),
        ("P. CABO BT 400 (REBARBA)", 0.219, "REBARBA", 180),
        ("P. CABO BT 400 (FURO)", 0.221, "FURO", 180),
        ("P. CABO BT 400 (LAMINAÇÃO)", 0.221, "LAMINAÇÃO", 0),

        ("TERMINAL AT (CORTE)", 0.415, "CORTE", 640),
        ("TERMINAL AT (FORJA)", 0.415, "FORJA", 144),
        ("TERMINAL AT (REBARBA)", 0.365, "REBARBA", 0),
        ("TERMINAL AT (USINAGEM)", 0.282, "USINAGEM", 120),

        ("PINO CONDUTOR (CORTE)", 0.120, "CORTE", 520),
        ("PINO CONDUTOR (REBAIXO)", 0.082, "REBAIXO", 0),
        ("PINO CONDUTOR (FORJA)", 0.082, "FORJA", 0),
        ("PINO CONDUTOR (REBARBA)", 0.063, "REBARBA", 144),
        ("PINO CONDUTOR (LAMINAÇÃO)", 0.063, "LAMINAÇÃO", 227),

        ("PRESILHA L", 0.000, "PRENSAGEM", 1000),
        ("PRESILHA INFERIOR", 0.000, "PRENSAGEM", 570),
    ]
    for nome, peso, processo, prod_hora in produtos_padrao:
        cur.execute("""
            INSERT INTO produtos (nome, peso_unitario, processo_padrao, prod_hora)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(nome) DO UPDATE SET
                peso_unitario=excluded.peso_unitario,
                processo_padrao=excluded.processo_padrao,
                prod_hora=excluded.prod_hora
        """, (nome, peso, processo, prod_hora))

    motivos = [
        "TROCA DE FERRAMENTA", "AJUSTE DE PROGRAMA", "FALTA DE MATERIAL",
        "MANUTENÇÃO CORRETIVA", "MANUTENÇÃO PREVENTIVA", "SETUP",
        "FALTA DE OPERADOR", "AGUARDANDO QUALIDADE", "RETRABALHO",
        "LIMPEZA DE MÁQUINA", "REUNIÃO", "INTERVALO"
    ]
    for m in motivos:
        cur.execute("INSERT OR IGNORE INTO motivos_parada (descricao) VALUES (?)", (m,))

    turnos = [("Turno A", "06:00", "16:00", 8.80), ("Turno B", "21:00", "06:00", 7.80)]
    for nome, hi, hf, hp in turnos:
        cur.execute("""
            INSERT INTO turnos (nome, hora_inicio, hora_fim, horas_produtivas)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(nome) DO UPDATE SET
                hora_inicio=excluded.hora_inicio,
                hora_fim=excluded.hora_fim,
                horas_produtivas=excluded.horas_produtivas
        """, (nome, hi, hf, hp))

    configs = {"meta_diaria": "1700", "planilha_path": "Apontamento_Producao.xlsx", "usuario": "Administrador", "versao": "2.0.0"}
    for k, v in configs.items():
        cur.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)", (k, v))
    conn.commit()


def _listar(tabela, campo="nome", apenas_ativos=True):
    conn = get_connection()
    where = "WHERE ativo=1" if apenas_ativos else ""
    rows = conn.execute(f"SELECT * FROM {tabela} {where} ORDER BY {campo}").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def listar_maquinas(apenas_ativas=True): return _listar("maquinas", "nome", apenas_ativas)
def listar_operadores(apenas_ativas=True): return _listar("operadores", "nome", apenas_ativas)
def listar_produtos(apenas_ativos=True): return _listar("produtos", "nome", apenas_ativos)
def listar_motivos_parada(): return _listar("motivos_parada", "descricao", True)
def listar_turnos(apenas_ativos=True): return _listar("turnos", "id", apenas_ativos)


def inserir_maquina(nome): _insert_nome("maquinas", nome)
def inserir_operador(nome): _insert_nome("operadores", nome)
def inserir_motivo_parada(descricao): _insert_nome("motivos_parada", descricao, "descricao")


def _insert_nome(tabela, valor, campo="nome"):
    conn = get_connection(); conn.execute(f"INSERT INTO {tabela} ({campo}) VALUES (?)", (valor,)); conn.commit(); conn.close()


def buscar_produto_por_nome(nome):
    conn = get_connection(); row = conn.execute("SELECT * FROM produtos WHERE nome=?", (nome,)).fetchone(); conn.close()
    return dict(row) if row else None


def buscar_turno_por_nome(nome):
    conn = get_connection(); row = conn.execute("SELECT * FROM turnos WHERE nome=?", (nome,)).fetchone(); conn.close()
    return dict(row) if row else None


def inserir_produto(nome, peso_unitario, processo_padrao, prod_hora=0):
    conn = get_connection()
    conn.execute("INSERT INTO produtos (nome, peso_unitario, processo_padrao, prod_hora) VALUES (?, ?, ?, ?)", (nome, peso_unitario, processo_padrao, prod_hora))
    conn.commit(); conn.close()


def atualizar_produto(id_, nome, peso_unitario, processo_padrao, prod_hora, ativo=1):
    conn = get_connection()
    conn.execute("UPDATE produtos SET nome=?, peso_unitario=?, processo_padrao=?, prod_hora=?, ativo=? WHERE id=?", (nome, peso_unitario, processo_padrao, prod_hora, ativo, id_))
    conn.commit(); conn.close()


def excluir_produto(id_):
    conn = get_connection(); conn.execute("DELETE FROM produtos WHERE id=?", (id_,)); conn.commit(); conn.close()


def inserir_turno(nome, hora_inicio, hora_fim, horas_produtivas=8.80):
    conn = get_connection(); conn.execute("INSERT INTO turnos (nome, hora_inicio, hora_fim, horas_produtivas) VALUES (?, ?, ?, ?)", (nome, hora_inicio, hora_fim, horas_produtivas)); conn.commit(); conn.close()


def atualizar_turno(id_, nome, hora_inicio, hora_fim, horas_produtivas, ativo=1):
    conn = get_connection(); conn.execute("UPDATE turnos SET nome=?, hora_inicio=?, hora_fim=?, horas_produtivas=?, ativo=? WHERE id=?", (nome, hora_inicio, hora_fim, horas_produtivas, ativo, id_)); conn.commit(); conn.close()


def inserir_apontamento(dados: dict) -> int:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO apontamentos
        (data, maquina, op, produto, processo, operador, turno, hora_inicio, hora_fim, quantidade, perda, observacao, tempo_produzindo, tempo_parado, tempo_total)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (dados["data"], dados["maquina"], dados["op"], dados["produto"], dados["processo"], dados["operador"], dados.get("turno", "Turno A"), dados["hora_inicio"], dados["hora_fim"], dados.get("quantidade", 0), dados.get("perda", 0), dados.get("observacao", ""), dados.get("tempo_produzindo", "00:00"), dados.get("tempo_parado", "00:00"), dados.get("tempo_total", "00:00")))
    apt_id = cur.lastrowid
    for p in dados.get("paradas", []):
        cur.execute("INSERT INTO paradas (apontamento_id, hora_inicio, hora_fim, motivo, tempo_parado) VALUES (?, ?, ?, ?, ?)", (apt_id, p["inicio"], p["fim"], p.get("motivo", ""), p.get("tempo", "00:00")))
    conn.commit(); conn.close(); return apt_id


def atualizar_apontamento(id_: int, dados: dict):
    conn = get_connection(); agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE apontamentos SET data=?, maquina=?, op=?, produto=?, processo=?, operador=?, turno=?, hora_inicio=?, hora_fim=?, quantidade=?, perda=?, observacao=?, tempo_produzindo=?, tempo_parado=?, tempo_total=?, atualizado_em=? WHERE id=?
    """, (dados["data"], dados["maquina"], dados["op"], dados["produto"], dados["processo"], dados["operador"], dados.get("turno", "Turno A"), dados["hora_inicio"], dados["hora_fim"], dados.get("quantidade", 0), dados.get("perda", 0), dados.get("observacao", ""), dados.get("tempo_produzindo", "00:00"), dados.get("tempo_parado", "00:00"), dados.get("tempo_total", "00:00"), agora, id_))
    conn.execute("DELETE FROM paradas WHERE apontamento_id=?", (id_,))
    for p in dados.get("paradas", []):
        conn.execute("INSERT INTO paradas (apontamento_id, hora_inicio, hora_fim, motivo, tempo_parado) VALUES (?, ?, ?, ?, ?)", (id_, p["inicio"], p["fim"], p.get("motivo", ""), p.get("tempo", "00:00")))
    conn.commit(); conn.close()


def excluir_apontamento(id_):
    conn = get_connection(); conn.execute("DELETE FROM apontamentos WHERE id=?", (id_,)); conn.commit(); conn.close()


def listar_apontamentos(data=None, turno=None, maquina=None, limit=200):
    conn = get_connection(); q = "SELECT * FROM apontamentos WHERE 1=1"; params = []
    if data: q += " AND data=?"; params.append(data)
    if turno: q += " AND turno=?"; params.append(turno)
    if maquina: q += " AND maquina=?"; params.append(maquina)
    q += " ORDER BY criado_em DESC LIMIT ?"; params.append(limit)
    rows = conn.execute(q, params).fetchall(); conn.close(); return [dict(r) for r in rows]


def buscar_apontamento_por_id(id_):
    conn = get_connection(); row = conn.execute("SELECT * FROM apontamentos WHERE id=?", (id_,)).fetchone(); conn.close(); return dict(row) if row else None


def listar_paradas_do_apontamento(apontamento_id):
    conn = get_connection(); rows = conn.execute("SELECT * FROM paradas WHERE apontamento_id=? ORDER BY hora_inicio", (apontamento_id,)).fetchall(); conn.close(); return [dict(r) for r in rows]


def get_config(chave, padrao=""):
    conn = get_connection(); row = conn.execute("SELECT valor FROM configuracoes WHERE chave=?", (chave,)).fetchone(); conn.close(); return row["valor"] if row else padrao


def set_config(chave, valor):
    conn = get_connection(); conn.execute("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, str(valor))); conn.commit(); conn.close()


def listar_apontamentos_para_excel(data, turno=None):
    conn = get_connection(); q = "SELECT * FROM apontamentos WHERE data=?"; params = [data]
    if turno: q += " AND turno=?"; params.append(turno)
    q += " ORDER BY maquina, hora_inicio"
    rows = conn.execute(q, params).fetchall(); result = []
    for row in rows:
        apt = dict(row)
        ps = conn.execute("SELECT * FROM paradas WHERE apontamento_id=? ORDER BY hora_inicio", (apt["id"],)).fetchall()
        apt["paradas"] = [dict(p) for p in ps]
        result.append(apt)
    conn.close(); return result
