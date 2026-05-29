from flask import Flask, render_template, jsonify, request
import sqlite3
import os
from datetime import datetime, date, timedelta
import random

app = Flask(__name__)
DB_PATH = "producao.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_filters(args):
    conditions = []
    params = []

    dt_ini = args.get("dt_ini")
    dt_fim = args.get("dt_fim")
    turno = args.get("turno")
    maquina = args.get("maquina")
    operador = args.get("operador")
    produto = args.get("produto")
    processo = args.get("processo")

    if dt_ini:
        conditions.append("data >= ?")
        params.append(dt_ini)
    if dt_fim:
        conditions.append("data <= ?")
        params.append(dt_fim)
    if turno and turno != "todos":
        conditions.append("turno = ?")
        params.append(turno)
    if maquina and maquina != "todos":
        conditions.append("maquina = ?")
        params.append(maquina)
    if operador and operador != "todos":
        conditions.append("operador = ?")
        params.append(operador)
    if produto and produto != "todos":
        conditions.append("produto = ?")
        params.append(produto)
    if processo and processo != "todos":
        conditions.append("processo = ?")
        params.append(processo)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where, params


def seed_demo_data():
    """Popula o banco com dados de exemplo se estiver vazio."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS apontamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            turno TEXT,
            maquina TEXT,
            produto TEXT,
            processo TEXT,
            operador TEXT,
            quantidade INTEGER,
            perda INTEGER,
            tempo_produzindo REAL,
            tempo_parado REAL,
            tempo_total REAL
        )
    """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM apontamentos")
    count = cur.fetchone()[0]

    if count == 0:
        turnos = ["Manhã", "Tarde", "Noite"]
        maquinas = ["CNC-01", "CNC-02", "TORNO-01", "TORNO-02", "FRESA-01", "FRESA-02", "RETIF-01"]
        produtos = ["EIXO-A10", "EIXO-B22", "FLANGE-X5", "BUCHA-M8", "PINO-G3", "TAMPA-H7", "ENGR-Z9", "PLACA-K1"]
        processos = ["Torneamento", "Fresamento", "Retificação", "Furação", "Rosqueamento"]
        operadores = ["Carlos Silva", "Ana Souza", "João Oliveira", "Maria Lima", "Pedro Santos", "Luiza Ferreira"]

        rows = []
        today = date.today()
        for days_back in range(30):
            d = today - timedelta(days=days_back)
            for _ in range(random.randint(8, 20)):
                tp = round(random.uniform(1.0, 7.5), 2)
                tpar = round(random.uniform(0.0, 2.5), 2)
                qtd = random.randint(50, 500)
                perda = random.randint(0, max(1, int(qtd * 0.12)))
                rows.append((
                    d.strftime("%Y-%m-%d"),
                    random.choice(turnos),
                    random.choice(maquinas),
                    random.choice(produtos),
                    random.choice(processos),
                    random.choice(operadores),
                    qtd, perda, tp, tpar, round(tp + tpar, 2)
                ))

        cur.executemany("""
            INSERT INTO apontamentos
            (data, turno, maquina, produto, processo, operador, quantidade, perda, tempo_produzindo, tempo_parado, tempo_total)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        conn.commit()

    conn.close()


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/status")
def status():
    try:
        conn = get_db()
        conn.execute("SELECT 1")
        conn.close()
        return jsonify({"status": "ok", "db": DB_PATH})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/filtros")
def filtros():
    conn = get_db()
    cur = conn.cursor()
    def distinct(col):
        cur.execute(f"SELECT DISTINCT {col} FROM apontamentos WHERE {col} IS NOT NULL ORDER BY {col}")
        return [r[0] for r in cur.fetchall()]

    data = {
        "turnos": distinct("turno"),
        "maquinas": distinct("maquina"),
        "operadores": distinct("operador"),
        "produtos": distinct("produto"),
        "processos": distinct("processo"),
    }
    conn.close()
    return jsonify(data)


@app.route("/api/resumo")
def resumo():
    where, params = build_filters(request.args)
    today_str = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    cur = conn.cursor()

    def q(sql, p=None):
        cur.execute(sql, p or params)
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else 0

    total_qtd = q(f"SELECT SUM(quantidade) FROM apontamentos {where}")
    total_perda = q(f"SELECT SUM(perda) FROM apontamentos {where}")
    total_boas = max(0, total_qtd - total_perda)
    pct_perda = round((total_perda / total_qtd * 100), 2) if total_qtd > 0 else 0
    eficiencia = round(100 - pct_perda, 2)

    tp_prod = q(f"SELECT SUM(tempo_produzindo) FROM apontamentos {where}")
    tp_par = q(f"SELECT SUM(tempo_parado) FROM apontamentos {where}")

    # Apontamentos do dia
    where_today = f"WHERE data = '{today_str}'"
    apto_dia = q(f"SELECT COUNT(*) FROM apontamentos {where_today}", [])
    prod_dia = q(f"SELECT SUM(quantidade) FROM apontamentos {where_today}", [])

    # Máquinas ativas
    maq_where = where + (" AND " if where else "WHERE ") + f"data = '{today_str}'"
    cur.execute(f"SELECT COUNT(DISTINCT maquina) FROM apontamentos {maq_where}", params)
    row = cur.fetchone()
    maq_ativas = row[0] if row else 0

    # Meta simulada: 110% do realizado médio
    meta = round(total_qtd * 1.1)

    conn.close()
    return jsonify({
        "producao_total": int(total_qtd),
        "pecas_boas": int(total_boas),
        "perdas": int(total_perda),
        "pct_perda": pct_perda,
        "tempo_produzindo": round(float(tp_prod), 1),
        "tempo_parado": round(float(tp_par), 1),
        "eficiencia": eficiencia,
        "meta": meta,
        "maquinas_ativas": int(maq_ativas),
        "apontamentos_dia": int(apto_dia),
        "producao_dia": int(prod_dia),
    })


@app.route("/api/graficos")
def graficos():
    where, params = build_filters(request.args)

    conn = get_db()
    cur = conn.cursor()

    def rows(sql, p=None):
        cur.execute(sql, p if p is not None else params)
        return cur.fetchall()

    # Produção por máquina
    r = rows(f"SELECT maquina, SUM(quantidade), SUM(perda) FROM apontamentos {where} GROUP BY maquina ORDER BY SUM(quantidade) DESC")
    prod_maquina = {"labels": [x[0] for x in r], "producao": [x[1] for x in r], "perda": [x[2] for x in r]}

    # Produção por turno
    r = rows(f"SELECT turno, SUM(quantidade), SUM(perda) FROM apontamentos {where} GROUP BY turno ORDER BY SUM(quantidade) DESC")
    prod_turno = {"labels": [x[0] for x in r], "producao": [x[1] for x in r], "perda": [x[2] for x in r]}

    # Produção por operador
    r = rows(f"SELECT operador, SUM(quantidade), SUM(perda) FROM apontamentos {where} GROUP BY operador ORDER BY SUM(quantidade) DESC LIMIT 10")
    prod_operador = {"labels": [x[0] for x in r], "producao": [x[1] for x in r], "perda": [x[2] for x in r]}

    # Evolução diária
    r = rows(f"SELECT data, SUM(quantidade), SUM(perda) FROM apontamentos {where} GROUP BY data ORDER BY data LIMIT 30")
    evolucao = {"labels": [x[0] for x in r], "producao": [x[1] for x in r], "perda": [x[2] for x in r]}

    # Top produtos
    r = rows(f"SELECT produto, SUM(quantidade) FROM apontamentos {where} GROUP BY produto ORDER BY SUM(quantidade) DESC LIMIT 10")
    top_produtos = {"labels": [x[0] for x in r], "valores": [x[1] for x in r]}

    # Tempo parado x produzindo por máquina
    r = rows(f"SELECT maquina, SUM(tempo_produzindo), SUM(tempo_parado) FROM apontamentos {where} GROUP BY maquina ORDER BY maquina")
    tempo_maquina = {"labels": [x[0] for x in r], "produzindo": [round(x[1], 1) for x in r], "parado": [round(x[2], 1) for x in r]}

    # Meta x Realizado por máquina
    total_qtd_val = sum(prod_maquina["producao"]) if prod_maquina["producao"] else 0
    meta_val = round(total_qtd_val * 1.1)
    meta_x_realizado = {
        "meta": meta_val,
        "realizado": total_qtd_val
    }

    # Ranking operadores (eficiência)
    r = rows(f"""SELECT operador, SUM(quantidade), SUM(perda) FROM apontamentos {where}
               GROUP BY operador ORDER BY SUM(quantidade) DESC LIMIT 8""")
    ranking_op = []
    for row in r:
        qtd = row[1] or 0
        perda = row[2] or 0
        ef = round((1 - perda / qtd) * 100, 1) if qtd > 0 else 0
        ranking_op.append({"nome": row[0], "producao": qtd, "eficiencia": ef})

    # Ranking máquinas
    r = rows(f"""SELECT maquina, SUM(quantidade), SUM(perda) FROM apontamentos {where}
               GROUP BY maquina ORDER BY SUM(quantidade) DESC""")
    ranking_maq = []
    for row in r:
        qtd = row[1] or 0
        perda = row[2] or 0
        ef = round((1 - perda / qtd) * 100, 1) if qtd > 0 else 0
        ranking_maq.append({"nome": row[0], "producao": qtd, "eficiencia": ef})

    conn.close()
    return jsonify({
        "prod_maquina": prod_maquina,
        "prod_turno": prod_turno,
        "prod_operador": prod_operador,
        "evolucao": evolucao,
        "top_produtos": top_produtos,
        "tempo_maquina": tempo_maquina,
        "meta_x_realizado": meta_x_realizado,
        "ranking_operadores": ranking_op,
        "ranking_maquinas": ranking_maq,
    })


@app.route("/api/tabelas")
def tabelas():
    where, params = build_filters(request.args)

    conn = get_db()
    cur = conn.cursor()

    # Últimos apontamentos
    cur.execute(f"""SELECT data, turno, maquina, produto, processo, operador, quantidade, perda, tempo_produzindo, tempo_parado
                   FROM apontamentos {where} ORDER BY data DESC, id DESC LIMIT 20""", params)
    ultimos = [dict(r) for r in cur.fetchall()]

    # Máquinas com maior perda
    cur.execute(f"""SELECT maquina, SUM(quantidade) as total, SUM(perda) as perdas,
                   ROUND(SUM(perda)*100.0/NULLIF(SUM(quantidade),0),2) as pct_perda
                   FROM apontamentos {where} GROUP BY maquina ORDER BY perdas DESC LIMIT 10""", params)
    maq_perda = [dict(r) for r in cur.fetchall()]

    # Operadores mais produtivos
    cur.execute(f"""SELECT operador, SUM(quantidade) as total, SUM(perda) as perdas,
                   ROUND((1-SUM(perda)*1.0/NULLIF(SUM(quantidade),0))*100,2) as eficiencia
                   FROM apontamentos {where} GROUP BY operador ORDER BY total DESC LIMIT 10""", params)
    op_prod = [dict(r) for r in cur.fetchall()]

    # Produtos mais fabricados
    cur.execute(f"""SELECT produto, SUM(quantidade) as total, SUM(perda) as perdas,
                   COUNT(*) as apontamentos
                   FROM apontamentos {where} GROUP BY produto ORDER BY total DESC LIMIT 10""", params)
    produtos = [dict(r) for r in cur.fetchall()]

    conn.close()
    return jsonify({
        "ultimos_apontamentos": ultimos,
        "maquinas_perda": maq_perda,
        "operadores_produtivos": op_prod,
        "produtos_fabricados": produtos,
    })


if __name__ == "__main__":
    seed_demo_data()
    print("="*60)
    print("  Dashboard Industrial AMT")
    print("  Acesse: http://localhost:5000")
    print("="*60)
    app.run(debug=True, port=5000)
