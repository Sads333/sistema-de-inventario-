from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'almoxarifado2025'

DB_PATH = os.path.join(os.path.dirname(__file__), 'almoxarifado.db')


# ── Credenciais (ajuste conforme necessário) ───────────────────────────────────

USUARIOS = {
    'admin':       'admin123',
    'almoxarife':  'estoque2025',
}


# ── Helper: protege rotas ──────────────────────────────────────────────────────

def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('usuario'):
            flash('Faça login para continuar.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ── Login / Logout ─────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('usuario'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha   = request.form.get('senha', '')
        if USUARIOS.get(usuario) == senha:
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha incorretos.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Sessão encerrada com sucesso.', 'success')
    return redirect(url_for('login'))


# ── Banco de dados ─────────────────────────────────────────────────────────────

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn, conn.cursor()

def init_db():
    conn, cur = db()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS itens (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              TEXT NOT NULL,
            categoria         TEXT NOT NULL,
            unidade           TEXT NOT NULL DEFAULT 'Und',
            quantidade        INTEGER NOT NULL DEFAULT 0,
            quantidade_minima INTEGER NOT NULL DEFAULT 5,
            descricao         TEXT DEFAULT ''
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id     INTEGER NOT NULL,
            tipo        TEXT NOT NULL CHECK(tipo IN ('entrada','saida')),
            quantidade  INTEGER NOT NULL,
            responsavel TEXT DEFAULT '',
            observacao  TEXT DEFAULT '',
            data        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES itens(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()


# ── Filtro de data ─────────────────────────────────────────────────────────────

@app.template_filter('fmt_date')
def fmt_date(value, fmt='%d/%m/%Y %H:%M'):
    if not value:
        return ''
    if isinstance(value, str):
        for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, f).strftime(fmt)
            except ValueError:
                pass
        return value
    if hasattr(value, 'strftime'):
        return value.strftime(fmt)
    return str(value)


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route('/')
@login_requerido
def dashboard():
    conn, cur = db()
    cur.execute('SELECT COUNT(*) AS total FROM itens')
    total_itens = cur.fetchone()['total']

    cur.execute('SELECT COALESCE(SUM(quantidade), 0) AS total FROM itens')
    total_estoque = cur.fetchone()['total']

    cur.execute('SELECT COUNT(*) AS total FROM itens WHERE quantidade < quantidade_minima')
    alertas = cur.fetchone()['total']

    cur.execute('SELECT COUNT(*) AS total FROM movimentacoes')
    total_mov = cur.fetchone()['total']

    cur.execute('''
        SELECT m.tipo, i.nome, m.quantidade, i.unidade, m.data
        FROM movimentacoes m JOIN itens i ON m.item_id = i.id
        ORDER BY m.data DESC LIMIT 8
    ''')
    recentes = cur.fetchall()

    cur.execute('''
        SELECT nome, quantidade, quantidade_minima, unidade
        FROM itens WHERE quantidade < quantidade_minima ORDER BY quantidade ASC LIMIT 6
    ''')
    criticos = cur.fetchall()

    conn.close()
    return render_template('dashboard.html',
        total_itens=total_itens, total_estoque=int(total_estoque or 0),
        alertas=alertas, total_mov=total_mov,
        recentes=recentes, criticos=criticos)


# ── Itens ──────────────────────────────────────────────────────────────────────

@app.route('/itens')
@login_requerido
def itens():
    conn, cur = db()
    busca = request.args.get('busca', '')
    categoria = request.args.get('categoria', '')

    sql = 'SELECT * FROM itens WHERE 1=1'
    params = []
    if busca:
        sql += ' AND nome LIKE ?'
        params.append(f'%{busca}%')
    if categoria:
        sql += ' AND categoria = ?'
        params.append(categoria)
    sql += ' ORDER BY nome'

    cur.execute(sql, params)
    lista = cur.fetchall()

    cur.execute('SELECT DISTINCT categoria FROM itens ORDER BY categoria')
    categorias = [r['categoria'] for r in cur.fetchall()]

    conn.close()
    return render_template('itens.html', itens=lista, categorias=categorias,
                           busca=busca, categoria_sel=categoria)


@app.route('/itens/novo', methods=['GET', 'POST'])
@login_requerido
def novo_item():
    if request.method == 'POST':
        conn, cur = db()
        cur.execute('''
            INSERT INTO itens (nome, categoria, unidade, quantidade, quantidade_minima, descricao)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            request.form['nome'], request.form['categoria'],
            request.form['unidade'], int(request.form['quantidade']),
            int(request.form['quantidade_minima']), request.form.get('descricao', '')
        ))
        conn.commit()
        conn.close()
        flash('Item cadastrado com sucesso!', 'success')
        return redirect(url_for('itens'))
    return render_template('form_item.html', item=None)


@app.route('/itens/editar/<int:id>', methods=['GET', 'POST'])
@login_requerido
def editar_item(id):
    conn, cur = db()
    if request.method == 'POST':
        cur.execute('''
            UPDATE itens SET nome=?, categoria=?, unidade=?,
            quantidade=?, quantidade_minima=?, descricao=? WHERE id=?
        ''', (
            request.form['nome'], request.form['categoria'],
            request.form['unidade'], int(request.form['quantidade']),
            int(request.form['quantidade_minima']), request.form.get('descricao', ''), id
        ))
        conn.commit()
        conn.close()
        flash('Item atualizado!', 'success')
        return redirect(url_for('itens'))
    cur.execute('SELECT * FROM itens WHERE id = ?', (id,))
    item = cur.fetchone()
    conn.close()
    return render_template('form_item.html', item=item)


@app.route('/itens/excluir/<int:id>')
@login_requerido
def excluir_item(id):
    conn, cur = db()
    cur.execute('DELETE FROM itens WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Item removido.', 'info')
    return redirect(url_for('itens'))


# ── Movimentações ──────────────────────────────────────────────────────────────

@app.route('/movimentacoes')
@login_requerido
def movimentacoes():
    conn, cur = db()
    tipo = request.args.get('tipo', '')
    sql = '''SELECT m.id, m.tipo, i.nome, m.quantidade, i.unidade,
                    m.responsavel, m.observacao, m.data
             FROM movimentacoes m JOIN itens i ON m.item_id = i.id WHERE 1=1'''
    params = []
    if tipo:
        sql += ' AND m.tipo = ?'
        params.append(tipo)
    sql += ' ORDER BY m.data DESC LIMIT 100'
    cur.execute(sql, params)
    lista = cur.fetchall()
    conn.close()
    return render_template('movimentacoes.html', movimentacoes=lista, tipo_sel=tipo)


@app.route('/entrada', methods=['GET', 'POST'])
@login_requerido
def entrada():
    conn, cur = db()
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        qtd = int(request.form['quantidade'])
        cur.execute('UPDATE itens SET quantidade = quantidade + ? WHERE id = ?', (qtd, item_id))
        cur.execute('''INSERT INTO movimentacoes (item_id, tipo, quantidade, responsavel, observacao)
                       VALUES (?, 'entrada', ?, ?, ?)''',
                    (item_id, qtd, request.form.get('responsavel', ''), request.form.get('observacao', '')))
        conn.commit()
        conn.close()
        flash('Entrada registrada com sucesso!', 'success')
        return redirect(url_for('movimentacoes'))
    cur.execute('SELECT id, nome, unidade FROM itens ORDER BY nome')
    itens = cur.fetchall()
    conn.close()
    return render_template('mov_form.html', tipo='entrada', itens=itens)


@app.route('/saida', methods=['GET', 'POST'])
@login_requerido
def saida():
    conn, cur = db()
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        qtd = int(request.form['quantidade'])
        cur.execute('SELECT quantidade FROM itens WHERE id = ?', (item_id,))
        atual = cur.fetchone()['quantidade']
        if qtd > atual:
            flash('Estoque insuficiente!', 'error')
            cur.execute('SELECT id, nome, unidade, quantidade FROM itens ORDER BY nome')
            itens = cur.fetchall()
            conn.close()
            return render_template('mov_form.html', tipo='saida', itens=itens)
        cur.execute('UPDATE itens SET quantidade = quantidade - ? WHERE id = ?', (qtd, item_id))
        cur.execute('''INSERT INTO movimentacoes (item_id, tipo, quantidade, responsavel, observacao)
                       VALUES (?, 'saida', ?, ?, ?)''',
                    (item_id, qtd, request.form.get('responsavel', ''), request.form.get('observacao', '')))
        conn.commit()
        conn.close()
        flash('Saída registrada com sucesso!', 'success')
        return redirect(url_for('movimentacoes'))
    cur.execute('SELECT id, nome, unidade, quantidade FROM itens ORDER BY nome')
    itens = cur.fetchall()
    conn.close()
    return render_template('mov_form.html', tipo='saida', itens=itens)


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
