import sys
from pathlib import Path

from PySide6.QtCore import Qt, QDate, QEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QMessageBox, QDateEdit, QFileDialog,
    QHeaderView, QTabWidget, QDialog, QFormLayout, QDoubleSpinBox, QCheckBox,
    QFrame,
)

from app import database as db
from app import excel_export
from app import totvs_api
from app.utils import (
    calcular_tempo,
    calcular_resumo,
    calcular_pecas_boas,
    calcular_percentual_perda,
    formatar_data_br,
)


# -----------------------------------------------------------------------------
# FUNÇÕES AUXILIARES DE HORA
# -----------------------------------------------------------------------------

def configurar_campo_hora(campo: QLineEdit, valor: str = "00:00"):
    campo.setInputMask("99:99;_")
    campo.setText(valor)
    campo.setPlaceholderText("00:00")
    campo.setMaximumWidth(95)


def limpar_hora(texto: str) -> str:
    texto = str(texto or "").replace("_", "0").replace(" ", "0")
    if ":" not in texto:
        texto = "00:00"
    partes = texto.split(":")
    hora = partes[0][:2].zfill(2) if len(partes) > 0 else "00"
    minuto = partes[1][:2].zfill(2) if len(partes) > 1 else "00"
    try:
        h = max(0, min(23, int(hora)))
        m = max(0, min(59, int(minuto)))
        return f"{h:02d}:{m:02d}"
    except Exception:
        return "00:00"


# -----------------------------------------------------------------------------
# VALIDAÇÃO DE MÁQUINA X PROCESSO
# -----------------------------------------------------------------------------

def _normalizar_validacao(texto: str) -> str:
    texto = str(texto or "").upper().strip()
    trocas = {
        "Á": "A", "À": "A", "Â": "A", "Ã": "A",
        "É": "E", "Ê": "E", "Í": "I",
        "Ó": "O", "Ô": "O", "Õ": "O",
        "Ú": "U", "Ç": "C",
    }
    for antigo, novo in trocas.items():
        texto = texto.replace(antigo, novo)
    return texto.replace(".", "").replace("-", " ").replace("_", " ")


def validar_processo_maquina(maquina: str, produto: str, processo: str):
    maq = _normalizar_validacao(maquina)
    prod = _normalizar_validacao(produto)
    proc = _normalizar_validacao(processo)
    base = f"{prod} {proc}"

    if maq.startswith("CNC"):
        permitidos = ["FURO", "USINAGEM", "REBAIXO"]
        if not any(p in base for p in permitidos):
            return False, "CNC só pode ter processo de FURO, USINAGEM ou REBAIXO."
    elif maq.startswith("FORJA"):
        if "FORJA" not in base:
            return False, "FORJA só pode ter processo de FORJA."
    elif maq.startswith("SOLDA"):
        if "SOLDA" not in base:
            return False, "SOLDA só pode ter processo de SOLDA."
    elif maq.startswith("LAMI") or "LAMINADORA" in maq:
        if "LAMINACAO" not in base and "LAMINACAO" not in proc:
            return False, "Laminadora só pode ter processo de LAMINAÇÃO."
    elif maq.startswith("SERRA"):
        if "CORTE" not in base:
            return False, "Serra só pode ter processo de CORTE."
    elif maq in ("PH 01", "PH 1", "PH01", "PH1", "PH 02", "PH 2", "PH02", "PH2",
                 "P110", "P 110", "PP110", "PP 110", "P80", "P 80", "PP80", "PP 80"):
        corte_haste = "CORTE" in base and "HASTE" in base
        rebarba = "REBARBA" in base
        flange = "FLANGE" in base
        presilha = "PRESILHA" in base
        if not (corte_haste or rebarba or flange or presilha):
            return (
                False,
                "PH 01, PH 02, P110 e P80 só podem fazer CORTE DE HASTE, REBARBA, FLANGE ou PRESILHA L.",
            )
    return True, ""


# =============================================================================
# DIÁLOGO DE CONFIGURAÇÕES
# =============================================================================

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.resize(950, 600)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._tab_meta()
        self._tab_produtos()
        self._tab_turnos()
        self._tab_motivos()           # ← NOVA ABA: Motivos de Parada
        self._tab_simples("Máquinas", "maquinas")
        self._tab_simples("Operadores", "operadores")

    # ------------------------------------------------------------------
    def _tab_meta(self):
        w = QWidget()
        lay = QFormLayout(w)
        self.meta = QDoubleSpinBox()
        self.meta.setMaximum(9999999)
        self.meta.setDecimals(3)
        self.meta.setValue(float(db.get_config("meta_diaria", "1700") or 1700))
        btn = QPushButton("Salvar meta")
        btn.clicked.connect(
            lambda: (
                db.set_config("meta_diaria", self.meta.value()),
                QMessageBox.information(self, "OK", "Meta salva."),
            )
        )
        lay.addRow("Meta diária (KG):", self.meta)
        lay.addRow(btn)
        self.tabs.addTab(w, "Meta")

    # ------------------------------------------------------------------
    def _tab_produtos(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QHBoxLayout()
        self.prod_nome = QLineEdit()
        self.prod_nome.setPlaceholderText("Produto")
        self.prod_peso = QDoubleSpinBox()
        self.prod_peso.setDecimals(4)
        self.prod_peso.setMaximum(99999)
        self.prod_proc = QLineEdit()
        self.prod_proc.setPlaceholderText("Processo")
        self.prod_hora = QSpinBox()
        self.prod_hora.setMaximum(999999)
        btn_add = QPushButton("Adicionar produto")
        btn_add.clicked.connect(self.add_produto)
        form.addWidget(self.prod_nome, 2)
        form.addWidget(QLabel("Peso kg:"))
        form.addWidget(self.prod_peso)
        form.addWidget(QLabel("Processo:"))
        form.addWidget(self.prod_proc)
        form.addWidget(QLabel("Prod. hora:"))
        form.addWidget(self.prod_hora)
        form.addWidget(btn_add)
        lay.addLayout(form)
        lay.addWidget(QLabel("Dica: novos produtos podem ser adicionados aqui."))
        self.tbl_prod = QTableWidget(0, 5)
        self.tbl_prod.setHorizontalHeaderLabels(["ID", "Produto", "Peso Unit.", "Processo", "Prod. Hora"])
        self.tbl_prod.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_prod)
        self.tabs.addTab(w, "Produtos")
        self.load_produtos()

    def load_produtos(self):
        rows = db.listar_produtos()
        self.tbl_prod.setRowCount(len(rows))
        for r, p in enumerate(rows):
            for c, v in enumerate([p.get("id"), p.get("nome"), p.get("peso_unitario"), p.get("processo_padrao"), p.get("prod_hora")]):
                self.tbl_prod.setItem(r, c, QTableWidgetItem(str(v)))

    def add_produto(self):
        try:
            nome = self.prod_nome.text().strip().upper()
            if not nome:
                return
            db.inserir_produto(nome, self.prod_peso.value(), self.prod_proc.text().strip().upper(), self.prod_hora.value())
            self.prod_nome.clear()
            self.prod_proc.clear()
            self.prod_peso.setValue(0)
            self.prod_hora.setValue(0)
            self.load_produtos()
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))

    # ------------------------------------------------------------------
    def _tab_turnos(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        self.turno_nome = QLineEdit()
        self.turno_nome.setPlaceholderText("Turno A")
        self.turno_ini = QLineEdit()
        self.turno_fim = QLineEdit()
        configurar_campo_hora(self.turno_ini, "06:00")
        configurar_campo_hora(self.turno_fim, "16:00")
        self.turno_horas = QDoubleSpinBox()
        self.turno_horas.setDecimals(2)
        self.turno_horas.setMaximum(24)
        self.turno_horas.setValue(8.80)
        btn = QPushButton("Adicionar turno")
        btn.clicked.connect(self.add_turno)
        row.addWidget(self.turno_nome)
        row.addWidget(QLabel("Início"))
        row.addWidget(self.turno_ini)
        row.addWidget(QLabel("Fim"))
        row.addWidget(self.turno_fim)
        row.addWidget(QLabel("Horas produtivas"))
        row.addWidget(self.turno_horas)
        row.addWidget(btn)
        lay.addLayout(row)
        self.tbl_turnos = QTableWidget(0, 5)
        self.tbl_turnos.setHorizontalHeaderLabels(["ID", "Turno", "Início", "Fim", "Horas produtivas"])
        self.tbl_turnos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_turnos)
        self.tabs.addTab(w, "Turnos")
        self.load_turnos()

    def load_turnos(self):
        rows = db.listar_turnos()
        self.tbl_turnos.setRowCount(len(rows))
        for r, t in enumerate(rows):
            for c, v in enumerate([t.get("id"), t.get("nome"), t.get("hora_inicio"), t.get("hora_fim"), t.get("horas_produtivas")]):
                self.tbl_turnos.setItem(r, c, QTableWidgetItem(str(v)))

    def add_turno(self):
        try:
            nome = self.turno_nome.text().strip()
            if not nome:
                return
            db.inserir_turno(nome, limpar_hora(self.turno_ini.text()), limpar_hora(self.turno_fim.text()), self.turno_horas.value())
            self.turno_nome.clear()
            self.load_turnos()
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))

    # ------------------------------------------------------------------
    # ABA: Motivos de Parada
    # ------------------------------------------------------------------
    def _tab_motivos(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        form = QHBoxLayout()
        self.mot_codigo = QLineEdit()
        self.mot_codigo.setPlaceholderText("Código (ex: 13)")
        self.mot_codigo.setMaximumWidth(100)
        self.mot_desc = QLineEdit()
        self.mot_desc.setPlaceholderText("Descrição do motivo")
        self.mot_ativo = QCheckBox("Ativo")
        self.mot_ativo.setChecked(True)
        btn_add = QPushButton("Adicionar motivo")
        btn_add.clicked.connect(self.add_motivo)
        btn_del = QPushButton("Excluir selecionado")
        btn_del.clicked.connect(self.del_motivo)

        form.addWidget(QLabel("Código:"))
        form.addWidget(self.mot_codigo)
        form.addWidget(QLabel("Descrição:"))
        form.addWidget(self.mot_desc, 3)
        form.addWidget(self.mot_ativo)
        form.addWidget(btn_add)
        form.addWidget(btn_del)
        lay.addLayout(form)

        lbl = QLabel("Os motivos cadastrados aqui ficam disponíveis no apontamento de paradas.")
        lbl.setStyleSheet("color: #52616f;")
        lay.addWidget(lbl)

        self.tbl_motivos = QTableWidget(0, 4)
        self.tbl_motivos.setHorizontalHeaderLabels(["ID", "Código", "Descrição", "Ativo"])
        self.tbl_motivos.setColumnHidden(0, True)
        self.tbl_motivos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.tbl_motivos)

        self.tabs.addTab(w, "Motivos de Parada")
        self.load_motivos()

    def load_motivos(self):
        rows = db.listar_motivos_parada(apenas_ativos=False)
        self.tbl_motivos.setRowCount(len(rows))
        for r, m in enumerate(rows):
            self.tbl_motivos.setItem(r, 0, QTableWidgetItem(str(m.get("id"))))
            self.tbl_motivos.setItem(r, 1, QTableWidgetItem(str(m.get("codigo", ""))))
            self.tbl_motivos.setItem(r, 2, QTableWidgetItem(str(m.get("descricao", ""))))
            self.tbl_motivos.setItem(r, 3, QTableWidgetItem("Sim" if m.get("ativo") else "Não"))

    def add_motivo(self):
        codigo = self.mot_codigo.text().strip()
        desc = self.mot_desc.text().strip()
        if not codigo or not desc:
            QMessageBox.warning(self, "Atenção", "Informe o código e a descrição.")
            return
        try:
            db.inserir_motivo_parada(codigo, desc, 1 if self.mot_ativo.isChecked() else 0)
            self.mot_codigo.clear()
            self.mot_desc.clear()
            self.mot_ativo.setChecked(True)
            self.load_motivos()
        except Exception as e:
            QMessageBox.warning(self, "Erro", str(e))

    def del_motivo(self):
        row = self.tbl_motivos.currentRow()
        if row < 0:
            return
        id_item = self.tbl_motivos.item(row, 0)
        if not id_item:
            return
        if QMessageBox.question(self, "Confirmar", "Deseja excluir o motivo selecionado?") == QMessageBox.Yes:
            db.excluir_motivo_parada(int(id_item.text()))
            self.load_motivos()

    # ------------------------------------------------------------------
    def _tab_simples(self, titulo, tipo):
        w = QWidget()
        lay = QVBoxLayout(w)
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setPlaceholderText(f"Novo item de {titulo}")
        btn = QPushButton("Adicionar")
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["ID", titulo])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        def carregar():
            dados = db.listar_maquinas() if tipo == "maquinas" else db.listar_operadores()
            table.setRowCount(len(dados))
            for r, item in enumerate(dados):
                table.setItem(r, 0, QTableWidgetItem(str(item["id"])))
                table.setItem(r, 1, QTableWidgetItem(item["nome"]))

        def add():
            try:
                nome = edit.text().strip().upper()
                if not nome:
                    return
                (db.inserir_maquina if tipo == "maquinas" else db.inserir_operador)(nome)
                edit.clear()
                carregar()
            except Exception as e:
                QMessageBox.warning(self, "Erro", str(e))

        btn.clicked.connect(add)
        row.addWidget(edit)
        row.addWidget(btn)
        lay.addLayout(row)
        lay.addWidget(table)
        self.tabs.addTab(w, titulo)
        carregar()


# =============================================================================
# JANELA PRINCIPAL
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        db.init_database()
        self.paradas = []
        self.editando_id = None
        self.setWindowTitle("Apontamento de Produção")
        self.resize(1500, 900)

        self.build_ui()
        self.load_combos()
        self.novo()
        self.carregar_lancamentos()

    # -------------------------------------------------------------------------
    def build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        # Barra de título + botões
        top = QHBoxLayout()
        title = QLabel("APONTAMENTO DE PRODUÇÃO")
        title.setObjectName("title")
        top.addWidget(title)
        top.addStretch()
        for txt, fn in [
            ("SALVAR (F5)", self.salvar),
            ("NOVO (F2)", self.novo),
            ("LIMPAR (F3)", self.limpar),
            ("EXPORTAR EXCEL", self.exportar_excel),
            ("CONFIGURAÇÕES", self.configuracoes),
        ]:
            b = QPushButton(txt)
            b.clicked.connect(fn)
            top.addWidget(b)
        main.addLayout(top)

        # ── Linha 1: OP (topo) ────────────────────────────────────────────
        g_op = QGroupBox("ORDEM DE PRODUÇÃO")
        f_op = QHBoxLayout(g_op)
        main.addWidget(g_op)

        self.op = QLineEdit()
        self.op.setPlaceholderText("Número da OP (somente números)")
        self.op.setMaximumWidth(200)
        # Aceita apenas dígitos
        from PySide6.QtGui import QIntValidator
        self.op.setValidator(QIntValidator(0, 9999999, self))

        self.btn_buscar_op = QPushButton("🔍 Pesquisar OP")
        self.btn_buscar_op.setObjectName("btn_op")
        self.btn_buscar_op.clicked.connect(self.pesquisar_op)
        self.op.returnPressed.connect(self.pesquisar_op)

        self.lbl_op_status = QLabel("")
        self.lbl_op_status.setFixedWidth(20)
        self.lbl_op_status.setFixedHeight(20)
        self.lbl_op_status.setAlignment(Qt.AlignCenter)
        self.lbl_op_status.setStyleSheet("border-radius: 10px; background: transparent;")

        self.lbl_op_produto = QLabel("")
        self.lbl_op_produto.setObjectName("lbl_op_info")
        self.lbl_op_descricao = QLabel("")
        self.lbl_op_descricao.setObjectName("lbl_op_info")
        self.lbl_op_unidade = QLabel("")
        self.lbl_op_unidade.setObjectName("lbl_op_info")

        f_op.addWidget(QLabel("OP:"))
        f_op.addWidget(self.op)
        f_op.addWidget(self.btn_buscar_op)
        f_op.addWidget(self.lbl_op_status)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        f_op.addWidget(sep)

        f_op.addWidget(QLabel("Produto:"))
        f_op.addWidget(self.lbl_op_produto)
        f_op.addWidget(QLabel("  Descrição:"))
        f_op.addWidget(self.lbl_op_descricao)
        f_op.addWidget(QLabel("  Unidade:"))
        f_op.addWidget(self.lbl_op_unidade)
        f_op.addStretch()

        # ── Linha 2: Dados Gerais + Apontamento de Produção ───────────────
        line1 = QHBoxLayout()
        main.addLayout(line1)

        g1 = QGroupBox("DADOS GERAIS")
        f1 = QGridLayout(g1)
        line1.addWidget(g1, 1)

        self.maquina = QComboBox()
        self.turno = QComboBox()
        self.data = QDateEdit()
        self.data.setCalendarPopup(True)
        self.produto = QComboBox()
        self.produto.setEditable(True)
        self.processo = QLineEdit()
        self.operador = QComboBox()
        self.operador.setEditable(True)

        f1.addWidget(QLabel("Máquina:"), 0, 0)
        f1.addWidget(self.maquina, 0, 1)
        f1.addWidget(QLabel("Data:"), 0, 2)
        f1.addWidget(self.data, 0, 3)
        f1.addWidget(QLabel("Turno:"), 0, 4)
        f1.addWidget(self.turno, 0, 5)
        f1.addWidget(QLabel("Produto:"), 1, 0)
        f1.addWidget(self.produto, 1, 1, 1, 5)
        f1.addWidget(QLabel("Processo:"), 2, 0)
        f1.addWidget(self.processo, 2, 1, 1, 2)
        f1.addWidget(QLabel("Operador:"), 2, 3)
        f1.addWidget(self.operador, 2, 4, 1, 2)

        self.produto.currentTextChanged.connect(self.preencher_processo)
        self.turno.currentTextChanged.connect(self.preencher_horario_turno)

        g2 = QGroupBox("APONTAMENTO DE PRODUÇÃO")
        f2 = QGridLayout(g2)
        line1.addWidget(g2, 1)

        self.h_ini = QLineEdit()
        self.h_fim = QLineEdit()
        configurar_campo_hora(self.h_ini, "00:00")
        configurar_campo_hora(self.h_fim, "00:00")
        self.qtd = QSpinBox()
        self.qtd.setMaximum(999999)
        self.perda = QSpinBox()
        self.perda.setMaximum(999999)
        self.obs = QTextEdit()
        self.obs.setFixedHeight(70)

        f2.addWidget(QLabel("Início:"), 0, 0)
        f2.addWidget(self.h_ini, 0, 1)
        f2.addWidget(QLabel("Fim:"), 0, 2)
        f2.addWidget(self.h_fim, 0, 3)
        f2.addWidget(QLabel("Qtd Realizada:"), 0, 4)
        f2.addWidget(self.qtd, 0, 5)
        f2.addWidget(QLabel("Perda:"), 0, 6)
        f2.addWidget(self.perda, 0, 7)
        f2.addWidget(QLabel("Observação:"), 1, 0)
        f2.addWidget(self.obs, 1, 1, 1, 7)

        # ── Linha 3: Paradas + Resumo ─────────────────────────────────────
        mid = QHBoxLayout()
        main.addLayout(mid)

        g3 = QGroupBox("APONTAMENTO DE PARADAS")
        f3 = QGridLayout(g3)
        mid.addWidget(g3, 3)

        self.p_ini = QLineEdit()
        self.p_fim = QLineEdit()
        configurar_campo_hora(self.p_ini, "00:00")
        configurar_campo_hora(self.p_fim, "00:00")
        self.p_ini.installEventFilter(self)
        self.p_fim.installEventFilter(self)

        # Campos de código e motivo
        self.p_codigo = QLineEdit()
        self.p_codigo.setPlaceholderText("Cód.")
        self.p_codigo.setMaximumWidth(60)
        self.p_codigo.textChanged.connect(self._preencher_motivo_por_codigo)

        self.p_motivo = QLineEdit()
        self.p_motivo.setPlaceholderText("Motivo da Parada")
        self.p_motivo.setReadOnly(True)
        self.p_motivo.setStyleSheet("background: #f0f0f0;")

        addp = QPushButton("ADICIONAR PARADA")
        addp.clicked.connect(self.add_parada)
        remp = QPushButton("REMOVER SELECIONADA")
        remp.clicked.connect(self.rem_parada)

        dica = QLabel("Informe o código para buscar o motivo automaticamente.")
        dica.setStyleSheet("color: #52616f; font-weight: normal;")

        f3.addWidget(QLabel("Início"), 0, 0)
        f3.addWidget(QLabel("Fim"), 0, 1)
        f3.addWidget(QLabel("Cód."), 0, 2)
        f3.addWidget(QLabel("Motivo"), 0, 3)
        f3.addWidget(dica, 0, 4, 1, 2)
        f3.addWidget(self.p_ini, 1, 0)
        f3.addWidget(self.p_fim, 1, 1)
        f3.addWidget(self.p_codigo, 1, 2)
        f3.addWidget(self.p_motivo, 1, 3)
        f3.addWidget(addp, 1, 4)
        f3.addWidget(remp, 1, 5)

        # Tabela de paradas: Início | Fim | Cód. | Motivo | Tempo
        self.tbl_paradas = QTableWidget(0, 5)
        self.tbl_paradas.setHorizontalHeaderLabels(["Início", "Fim", "Cód.", "Motivo da Parada", "Tempo"])
        self.tbl_paradas.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        f3.addWidget(self.tbl_paradas, 2, 0, 1, 6)

        g4 = QGroupBox("RESUMO")
        v4 = QVBoxLayout(g4)
        mid.addWidget(g4, 1)

        self.res_labels = {}
        for k in ["Tempo Produzindo", "Tempo Parado", "Tempo Total",
                   "Qtde Realizada", "Perda", "% Perda", "Peças Boas"]:
            lab = QLabel(f"{k}: -")
            v4.addWidget(lab)
            self.res_labels[k] = lab
        btn_calc = QPushButton("ATUALIZAR RESUMO")
        btn_calc.clicked.connect(self.atualizar_resumo)
        v4.addWidget(btn_calc)
        v4.addStretch()

        # ── Linha 4: Registros Salvos ─────────────────────────────────────
        g5 = QGroupBox("REGISTROS SALVOS")
        v5 = QVBoxLayout(g5)
        main.addWidget(g5)

        filt = QHBoxLayout()
        self.filtro_data = QDateEdit()
        self.filtro_data.setCalendarPopup(True)
        self.filtro_turno = QComboBox()
        self.filtro_turno.addItem("Todos")
        btn_f = QPushButton("Filtrar")
        btn_f.clicked.connect(self.carregar_lancamentos)
        filt.addWidget(QLabel("Data:"))
        filt.addWidget(self.filtro_data)
        filt.addWidget(QLabel("Turno:"))
        filt.addWidget(self.filtro_turno)
        filt.addWidget(btn_f)
        filt.addStretch()
        v5.addLayout(filt)

        # Colunas: ID | Data | Turno | OP | Máquina | Produto | Processo |
        #          Operador | Início | Fim | Qtd | Perda | Motivo Principal | Status Envio
        self.tbl = QTableWidget(0, 14)
        self.tbl.setHorizontalHeaderLabels([
            "ID", "Data", "Turno", "OP", "Máquina", "Produto", "Processo",
            "Operador", "Início", "Fim", "Qtd", "Perda",
            "Motivo Principal", "Status Envio",
        ])
        self.tbl.setColumnHidden(0, True)
        self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl.doubleClicked.connect(self.editar_selecionado)
        v5.addWidget(self.tbl)

        btns = QHBoxLayout()
        be = QPushButton("EDITAR SELECIONADO")
        be.clicked.connect(self.editar_selecionado)
        bx = QPushButton("EXCLUIR SELECIONADO")
        bx.clicked.connect(self.excluir_selecionado)
        br = QPushButton("🔄 REENVIAR SELECIONADO AO TOTVS")
        br.setObjectName("btn_reenviar")
        br.clicked.connect(self.reenviar_selecionado)
        bra = QPushButton("🔄 REENVIAR TODOS PENDENTES/ERRO")
        bra.setObjectName("btn_reenviar")
        bra.clicked.connect(self.reenviar_todos_pendentes)
        btns.addWidget(be)
        btns.addWidget(bx)
        btns.addWidget(br)
        btns.addWidget(bra)
        btns.addStretch()
        v5.addLayout(btns)

        self._aplicar_estilo()

    # -------------------------------------------------------------------------
    def _aplicar_estilo(self):
        self.setStyleSheet('''
            QMainWindow { background: #f4f6f8; }
            QLabel#title { font-size: 26px; font-weight: bold; color: #0b2b59; }
            QLabel#lbl_op_info { font-weight: bold; color: #0b2b59; font-size: 12px; }
            QGroupBox {
                font-weight: bold; color: #0b2b59;
                border: 1px solid #cfd6df; border-radius: 6px;
                margin-top: 10px; padding: 8px; background: white;
            }
            QPushButton {
                background: #123b75; color: white;
                padding: 9px 14px; border-radius: 5px; font-weight: bold;
            }
            QPushButton:hover { background: #1d559e; }
            QPushButton#btn_op {
                background: #2563a8; padding: 6px 12px;
            }
            QLineEdit, QComboBox, QSpinBox, QDateEdit, QTextEdit, QDoubleSpinBox {
                padding: 6px; border: 1px solid #b8c0cc;
                border-radius: 4px; background: white;
            }
            QTableWidget { background: white; gridline-color: #d4d8dd; }
            QPushButton#btn_reenviar {
                background: #b45309;
            }
            QPushButton#btn_reenviar:hover { background: #d97706; }
        ''')

    # =========================================================================
    # PESQUISA DE OP (integração futura com TOTVS Protheus)
    # =========================================================================

    def pesquisar_op(self):
        """Pesquisa a OP no TOTVS Protheus.

        INTEGRAÇÃO FUTURA:
            Aqui será feita uma chamada REST/SOAP ao Protheus para consultar
            a OP e retornar: produto, descrição e unidade.

            Exemplo de chamada futura:
                resp = requests.get(f"{TOTVS_URL}/api/mrp/v1/productionorders/{op}")
                dados = resp.json()

        Por enquanto, apenas valida se o campo não está vazio e exibe
        indicador visual de "não encontrado" (vermelho), pois ainda não
        há integração real.
        """
        op = self.op.text().strip()
        if not op:
            QMessageBox.warning(self, "OP", "Informe o número da OP.")
            return

        # ----------------------------------------------------------------
        # TODO: Implementar chamada ao TOTVS Protheus aqui
        # Quando implementado, substituir o bloco abaixo pelo retorno real.
        # ----------------------------------------------------------------
        # Simulação: OP encontrada apenas se começar com "1" (demonstração)
        # Remover este bloco ao implementar a integração real.
        op_encontrada = False  # alterar para True quando integração estiver pronta
        dados_op = {}          # preencher com retorno do TOTVS

        if op_encontrada:
            self._set_op_valida(dados_op)
        else:
            self._set_op_invalida()

    def _set_op_valida(self, dados: dict):
        """Preenche os campos com os dados retornados pelo TOTVS."""
        self.lbl_op_status.setStyleSheet(
            "border-radius: 10px; background: #22c55e;"
        )
        self.lbl_op_produto.setText(dados.get("produto", ""))
        self.lbl_op_descricao.setText(dados.get("descricao", ""))
        self.lbl_op_unidade.setText(dados.get("unidade", ""))
        # Preenche o combo de produto automaticamente, se existir
        idx = self.produto.findText(dados.get("produto", ""), Qt.MatchFixedString)
        if idx >= 0:
            self.produto.setCurrentIndex(idx)

    def _set_op_invalida(self):
        """Indica que a OP não foi encontrada."""
        self.lbl_op_status.setStyleSheet(
            "border-radius: 10px; background: #ef4444;"
        )
        self.lbl_op_produto.setText("")
        self.lbl_op_descricao.setText("OP não encontrada")
        self.lbl_op_unidade.setText("")

    def _limpar_op_status(self):
        self.lbl_op_status.setStyleSheet("border-radius: 10px; background: transparent;")
        self.lbl_op_produto.setText("")
        self.lbl_op_descricao.setText("")
        self.lbl_op_unidade.setText("")

    # =========================================================================
    # CÓDIGO DE MOTIVO → busca automática de descrição
    # =========================================================================

    def _preencher_motivo_por_codigo(self, codigo: str):
        """Ao digitar o código, busca a descrição automaticamente."""
        codigo = codigo.strip()
        if not codigo:
            self.p_motivo.setText("")
            return
        motivo = db.buscar_motivo_por_codigo(codigo)
        if motivo:
            self.p_motivo.setText(motivo["descricao"])
            self.p_motivo.setStyleSheet("background: #f0f9f0; border: 1px solid #22c55e; border-radius: 4px;")
        else:
            self.p_motivo.setText("")
            self.p_motivo.setStyleSheet("background: #fff0f0; border: 1px solid #ef4444; border-radius: 4px;")

    # =========================================================================
    # COMBOS / CARREGAR
    # =========================================================================

    def load_combos(self):
        self.maquina.clear()
        self.maquina.addItems([m["nome"] for m in db.listar_maquinas()])
        self.operador.clear()
        self.operador.addItems([o["nome"] for o in db.listar_operadores()])
        self.produto.clear()
        self.produto.addItems([p["nome"] for p in db.listar_produtos()])
        self.turno.blockSignals(True)
        self.turno.clear()
        self.turno.addItems([t["nome"] for t in db.listar_turnos()])
        self.turno.blockSignals(False)
        self.filtro_turno.clear()
        self.filtro_turno.addItem("Todos")
        self.filtro_turno.addItems([t["nome"] for t in db.listar_turnos()])
        self.preencher_horario_turno(self.turno.currentText())

    def preencher_horario_turno(self, turno_nome):
        turno_info = db.buscar_turno_por_nome(turno_nome)
        if not turno_info:
            self.h_ini.setText("00:00")
            self.h_fim.setText("00:00")
            return
        self.h_ini.setText(limpar_hora(turno_info.get("hora_inicio", "00:00")))
        self.h_fim.setText(limpar_hora(turno_info.get("hora_fim", "00:00")))
        self.atualizar_resumo()

    def preencher_processo(self, nome):
        p = db.buscar_produto_por_nome(nome.strip().upper())
        if p:
            self.processo.setText(p.get("processo_padrao", ""))

    # =========================================================================
    # NOVO / LIMPAR
    # =========================================================================

    def novo(self):
        self.editando_id = None
        self.limpar()

    def limpar(self):
        hoje = QDate.currentDate()
        self.data.setDate(hoje)
        self.filtro_data.setDate(hoje)
        self.op.clear()
        self._limpar_op_status()
        self.preencher_horario_turno(self.turno.currentText())
        self.p_ini.setText("00:00")
        self.p_fim.setText("00:00")
        self.p_codigo.clear()
        self.p_motivo.clear()
        self.p_motivo.setStyleSheet("background: #f0f0f0;")
        self.qtd.setValue(0)
        self.perda.setValue(0)
        self.obs.clear()
        self.paradas = []
        self.atualizar_tabela_paradas()
        self.atualizar_resumo()

    # =========================================================================
    # PARADAS
    # =========================================================================

    def add_parada(self):
        ini = limpar_hora(self.p_ini.text())
        fim = limpar_hora(self.p_fim.text())
        if ini == "00:00" and fim == "00:00":
            QMessageBox.warning(self, "Atenção", "Informe o início e o fim da parada.")
            return

        codigo = self.p_codigo.text().strip()
        motivo = self.p_motivo.text().strip()

        # Valida se o código foi informado e é válido
        if codigo and not motivo:
            QMessageBox.warning(self, "Atenção", f"Código '{codigo}' não encontrado. Verifique o cadastro de motivos.")
            return

        tempo = calcular_tempo(ini, fim)
        self.paradas.append({
            "inicio": ini,
            "fim": fim,
            "codigo_motivo": codigo,
            "motivo": motivo,
            "tempo": tempo,
        })

        self.p_ini.setText("00:00")
        self.p_fim.setText("00:00")
        self.p_codigo.clear()
        self.p_motivo.clear()
        self.p_motivo.setStyleSheet("background: #f0f0f0;")
        self.p_ini.setFocus()
        self.p_ini.selectAll()

        self.atualizar_tabela_paradas()
        self.atualizar_resumo()

    def rem_parada(self):
        r = self.tbl_paradas.currentRow()
        if r >= 0:
            self.paradas.pop(r)
            self.atualizar_tabela_paradas()
            self.atualizar_resumo()

    def atualizar_tabela_paradas(self):
        self.tbl_paradas.setRowCount(len(self.paradas))
        for r, p in enumerate(self.paradas):
            vals = [
                p["inicio"],
                p["fim"],
                p.get("codigo_motivo", ""),
                p.get("motivo", ""),
                p.get("tempo", "00:00"),
            ]
            for c, v in enumerate(vals):
                self.tbl_paradas.setItem(r, c, QTableWidgetItem(str(v)))

    # =========================================================================
    # RESUMO
    # =========================================================================

    def resumo_calc(self):
        return calcular_resumo(
            limpar_hora(self.h_ini.text()),
            limpar_hora(self.h_fim.text()),
            self.paradas,
        )

    def atualizar_resumo(self):
        res = self.resumo_calc()
        qtd = self.qtd.value()
        perda = self.perda.value()
        vals = {
            "Tempo Produzindo": res["tempo_produzindo"],
            "Tempo Parado": res["tempo_parado"],
            "Tempo Total": res["tempo_total"],
            "Qtde Realizada": qtd,
            "Perda": perda,
            "% Perda": f"{calcular_percentual_perda(qtd, perda):.2f}%",
            "Peças Boas": calcular_pecas_boas(qtd, perda),
        }
        for k, v in vals.items():
            self.res_labels[k].setText(f"{k}: {v}")
        return res

    # =========================================================================
    # MONTAR DADOS / SALVAR
    # =========================================================================

    def montar_dados(self):
        self.h_ini.setText(limpar_hora(self.h_ini.text()))
        self.h_fim.setText(limpar_hora(self.h_fim.text()))
        res = self.atualizar_resumo()

        # Motivo principal = primeiro motivo da lista de paradas
        motivo_principal = ""
        if self.paradas:
            p0 = self.paradas[0]
            cod = p0.get("codigo_motivo", "")
            mot = p0.get("motivo", "")
            motivo_principal = f"{cod} - {mot}" if cod and mot else mot or cod

        return {
            "data": self.data.date().toString("yyyy-MM-dd"),
            "maquina": self.maquina.currentText(),
            "op": self.op.text().strip(),
            "produto": self.produto.currentText().strip().upper(),
            "processo": self.processo.text().strip().upper(),
            "operador": self.operador.currentText().strip().upper(),
            "turno": self.turno.currentText(),
            "hora_inicio": limpar_hora(self.h_ini.text()),
            "hora_fim": limpar_hora(self.h_fim.text()),
            "quantidade": self.qtd.value(),
            "perda": self.perda.value(),
            "observacao": self.obs.toPlainText(),
            "tempo_produzindo": res["tempo_produzindo"],
            "tempo_parado": res["tempo_parado"],
            "tempo_total": res["tempo_total"],
            "status_envio_totvs": "PENDENTE",
            "motivo_principal": motivo_principal,
            "paradas": self.paradas,
        }

    def salvar(self):
        dados = self.montar_dados()

        # Validações
        if not dados["op"]:
            QMessageBox.warning(self, "Atenção", "O campo Ordem de Produção (OP) é obrigatório.")
            self.op.setFocus()
            return
        if not dados["produto"] or not dados["operador"]:
            QMessageBox.warning(self, "Atenção", "Preencha produto e operador.")
            return

        valido, erro = validar_processo_maquina(dados["maquina"], dados["produto"], dados["processo"])
        if not valido:
            QMessageBox.warning(self, "Erro de apontamento", erro)
            return

        try:
            if self.editando_id:
                db.atualizar_apontamento(self.editando_id, dados)
                apt_id = self.editando_id
                msg_local = "Registro atualizado."
            else:
                apt_id = db.inserir_apontamento(dados)
                msg_local = "Registro salvo."
        except Exception as e:
            QMessageBox.critical(self, "Erro ao salvar", str(e))
            return

        # ── Envio automático ao TOTVS ──────────────────────────────────────
        resultado = totvs_api.enviar_apontamento(apt_id)

        if resultado["sucesso"]:
            QMessageBox.information(
                self, "OK",
                f"{msg_local}\n\n✅ Enviado ao TOTVS com sucesso.",
            )
        else:
            QMessageBox.warning(
                self, "Salvo — Falha no TOTVS",
                f"{msg_local}\n\n"
                f"⚠️ O apontamento foi salvo localmente, mas não foi enviado ao TOTVS:\n\n"
                f"{resultado['mensagem']}\n\n"
                f"O registro ficará como PENDENTE e poderá ser reenviado depois.",
            )

        self.novo()
        self.carregar_lancamentos()

    # =========================================================================
    # LISTA DE REGISTROS SALVOS
    # =========================================================================

    def carregar_lancamentos(self):
        data = (
            self.filtro_data.date().toString("yyyy-MM-dd")
            if hasattr(self, "filtro_data")
            else QDate.currentDate().toString("yyyy-MM-dd")
        )
        turno = (
            self.filtro_turno.currentText()
            if hasattr(self, "filtro_turno") and self.filtro_turno.currentText() != "Todos"
            else None
        )
        rows = db.listar_apontamentos(data=data, turno=turno, limit=200)
        self.tbl.setRowCount(len(rows))
        for r, a in enumerate(rows):
            # Motivo principal: busca na primeira parada do apontamento
            paradas = db.listar_paradas_do_apontamento(a["id"])
            motivo_principal = ""
            if paradas:
                p0 = paradas[0]
                cod = p0.get("codigo_motivo", "")
                mot = p0.get("motivo", "")
                motivo_principal = f"{cod} - {mot}" if cod and mot else mot or cod

            vals = [
                a["id"],
                formatar_data_br(a["data"]),
                a["turno"],
                a.get("op", ""),
                a["maquina"],
                a["produto"],
                a["processo"],
                a["operador"],
                a["hora_inicio"],
                a["hora_fim"],
                a["quantidade"],
                a["perda"],
                motivo_principal,
                a.get("status_envio_totvs", "PENDENTE"),
            ]
            for c, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                # Colorir coluna Status Envio
                if c == 13:
                    if str(v) == "ENVIADO":
                        item.setBackground(Qt.green)
                    elif str(v) == "ERRO":
                        item.setBackground(Qt.red)
                self.tbl.setItem(r, c, item)

    def editar_selecionado(self):
        r = self.tbl.currentRow()
        if r < 0:
            return
        id_ = int(self.tbl.item(r, 0).text())
        a = db.buscar_apontamento_por_id(id_)
        if not a:
            return

        self.editando_id = id_
        self.data.setDate(QDate.fromString(a["data"], "yyyy-MM-dd"))
        self.maquina.setCurrentText(a["maquina"])
        self.turno.setCurrentText(a["turno"])
        self.produto.setCurrentText(a["produto"])
        self.processo.setText(a["processo"])
        self.operador.setCurrentText(a["operador"])
        self.op.setText(a.get("op", ""))
        self._limpar_op_status()

        self.h_ini.setText(limpar_hora(a["hora_inicio"]))
        self.h_fim.setText(limpar_hora(a["hora_fim"]))
        self.qtd.setValue(int(a["quantidade"]))
        self.perda.setValue(int(a["perda"]))
        self.obs.setText(a.get("observacao", ""))

        self.paradas = [
            {
                "inicio": limpar_hora(p["hora_inicio"]),
                "fim": limpar_hora(p["hora_fim"]),
                "codigo_motivo": p.get("codigo_motivo", ""),
                "motivo": p.get("motivo", ""),
                "tempo": p["tempo_parado"],
            }
            for p in db.listar_paradas_do_apontamento(id_)
        ]
        self.atualizar_tabela_paradas()
        self.atualizar_resumo()

    def excluir_selecionado(self):
        r = self.tbl.currentRow()
        if r < 0:
            return
        id_ = int(self.tbl.item(r, 0).text())
        if QMessageBox.question(self, "Confirmar", "Deseja excluir o registro selecionado?") == QMessageBox.Yes:
            db.excluir_apontamento(id_)
            self.carregar_lancamentos()

    def reenviar_selecionado(self):
        r = self.tbl.currentRow()
        if r < 0:
            QMessageBox.warning(self, "Atenção", "Selecione um registro na tabela.")
            return
        id_ = int(self.tbl.item(r, 0).text())
        resultado = totvs_api.enviar_apontamento(id_)
        if resultado["sucesso"]:
            QMessageBox.information(self, "TOTVS", "✅ Enviado ao TOTVS com sucesso.")
        else:
            QMessageBox.warning(self, "Falha no envio", f"⚠️ {resultado['mensagem']}")
        self.carregar_lancamentos()

    def reenviar_todos_pendentes(self):
        resultado = totvs_api.reenviar_pendentes()
        QMessageBox.information(
            self, "Reenvio concluído",
            f"✅ Enviados: {resultado['enviados']}\n"
            f"❌ Com erro: {resultado['erros']}",
        )
        self.carregar_lancamentos()

    def exportar_excel(self):
        data = self.filtro_data.date().toString("yyyy-MM-dd")
        turno = self.filtro_turno.currentText()
        turno_arg = None if turno == "Todos" else turno
        nome = f"Apontamento_Producao_{data.replace('-', '')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Excel", str(Path.home() / nome), "Excel (*.xlsx)")
        if not path:
            return
        try:
            saida = excel_export.gerar_excel(data, turno_arg, path)
            QMessageBox.information(self, "Excel gerado", f"Planilha salva em:\n{saida}")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao gerar Excel", str(e))

    def configuracoes(self):
        dlg = ConfigDialog(self)
        dlg.exec()
        self.load_combos()

    # =========================================================================
    # EVENTOS DE TECLADO
    # =========================================================================

    def eventFilter(self, obj, event):
        if obj in (getattr(self, "p_ini", None), getattr(self, "p_fim", None)) and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                destino = self.p_fim if obj == self.p_ini else self.p_ini
                destino.setFocus()
                destino.selectAll()
                return True
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.add_parada()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.salvar()
        elif event.key() == Qt.Key_F2:
            self.novo()
        elif event.key() == Qt.Key_F3:
            self.limpar()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())