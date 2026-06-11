# 📦 sistema de inventario — Sistema de Controle de Estoque

Sistema completo de almoxarifado com visual corporativo ERP.  
Backend: Python (Flask) · Banco: **SQLite** (embutido, sem instalação) · Frontend: HTML + CSS puro.

---

## Estrutura

```
Startup/
├── app.py
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── itens.html
    ├── form_item.html
    ├── movimentacoes.html
    └── mov_form.html
```

---

## Como Rodar

### 1. Instalar dependências (só Flask — sem MySQL!)
```bash
pip install flask
```

### 2. Iniciar o servidor
```bash
python app.py
```

> O banco de dados SQLite (`almoxarifado.db`) é criado **automaticamente** na primeira execução. Sem configuração necessária.

### 3. Acessar
**http://localhost:5000**

---

## Funcionalidades

| Tela             | O que faz                                        |
|------------------|--------------------------------------------------|
| Dashboard        | KPIs, últimas movimentações, estoque crítico     |
| Itens            | Lista com busca, filtro por categoria e status   |
| Cadastrar Item   | Formulário com unidade, mínimo, descrição        |
| Editar / Excluir | Gerencia itens existentes                        |
| Nova Entrada     | Aumenta estoque + registra no histórico          |
| Nova Saída       | Diminui estoque (valida saldo) + histórico       |
| Movimentações    | Histórico completo com filtro por tipo           |

---

## Notas técnicas

- **Banco**: SQLite 3 (embutido no Python), arquivo `almoxarifado.db` gerado na pasta do projeto
- **Sem dependências externas de banco de dados** — não precisa de MySQL, PostgreSQL nem Docker
- Trocar para MySQL é só substituir `sqlite3` por `mysql-connector-python` no `app.py` e ajustar a string de conexão
