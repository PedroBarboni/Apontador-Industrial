# Dashboard Industrial AMT

Sistema de monitoramento de produção — Manufacturing Execution System (MES)

## ⚡ Como executar

```bash
# 1. Instale as dependências
pip install flask

# 2. Execute o servidor
python app.py

# 3. Acesse no navegador
http://localhost:5000
```

## 🗂 Estrutura do Projeto

```
dashboard_amt/
├── app.py                    # Backend Flask + APIs SQLite
├── producao.db               # Banco de dados SQLite (criado automaticamente)
├── templates/
│   └── dashboard.html        # Template principal
└── static/
    ├── css/
    │   └── style.css         # Estilos completos
    ├── js/
    │   └── dashboard.js      # Lógica frontend, gráficos, filtros
    └── img/
        └── logo.png          # ← SUBSTITUA pela logo da empresa
```

## 🖼 Trocar a Logo

Basta substituir o arquivo:
```
static/img/logo.png
```

A logo aparecerá automaticamente na **sidebar** e na **tela de carregamento**.

## 📊 Banco de Dados

O sistema usa `producao.db` com a tabela `apontamentos`:

| Campo             | Tipo    | Descrição              |
|-------------------|---------|------------------------|
| data              | TEXT    | Data do apontamento    |
| turno             | TEXT    | Manhã / Tarde / Noite  |
| maquina           | TEXT    | Código da máquina      |
| produto           | TEXT    | Código do produto      |
| processo          | TEXT    | Tipo de processo       |
| operador          | TEXT    | Nome do operador       |
| quantidade        | INTEGER | Peças produzidas       |
| perda             | INTEGER | Peças com defeito      |
| tempo_produzindo  | REAL    | Horas em operação      |
| tempo_parado      | REAL    | Horas paradas          |
| tempo_total       | REAL    | Total de horas         |

Se o banco estiver vazio, dados de demonstração são gerados automaticamente.

## 🎨 Identidade Visual

| Cor          | Hex       | Uso                    |
|--------------|-----------|------------------------|
| Azul Escuro  | `#123B75` | Header, sidebar, títulos |
| Azul Médio   | `#1D559E` | Botões, gráficos, links |
| Azul Claro   | `#BDD7EE` | Detalhes, bordas       |
| Fundo        | `#F0F3F8` | Background geral       |
| Verde        | `#16a34a` | Bom desempenho         |
| Vermelho     | `#dc2626` | Perdas / alertas       |
| Amarelo      | `#ca8a04` | Atenção                |

## 🔄 Atualização Automática

O dashboard atualiza automaticamente a cada **5 minutos**.
Use o botão **↻ Atualizar** para forçar atualização imediata.

## 📦 Exportar Dados

Clique em **Exportar** para baixar os apontamentos filtrados em CSV.
