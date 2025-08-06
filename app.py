from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # Troque em produção!

# Configuração do banco de dados
DATABASE = 'pedidos.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'user'
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            itens TEXT NOT NULL,
            observacoes TEXT,
            status TEXT DEFAULT 'pendente',
            criado_por INTEGER,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (criado_por) REFERENCES usuarios (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            texto TEXT NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        ''')
        
        cursor.execute("SELECT * FROM usuarios WHERE email = 'admin@sys.com'")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                ('Admin', 'admin@sys.com', generate_password_hash('123'), 'admin')
            )
        
        conn.commit()
        conn.close()

# Rotas de autenticação
@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        conn = get_db_connection()
        usuario = conn.execute(
            'SELECT * FROM usuarios WHERE email = ?', (email,)
        ).fetchone()
        conn.close()
        
        if usuario and check_password_hash(usuario['senha'], senha):
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_tipo'] = usuario['tipo']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', erro='Credenciais inválidas!')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Rotas principais
@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/pedidos')
def listar_pedidos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if session['usuario_tipo'] == 'admin':
        pedidos = conn.execute('''
            SELECT p.*, u.nome as criador 
            FROM pedidos p
            JOIN usuarios u ON p.criado_por = u.id
            ORDER BY p.data_criacao DESC
        ''').fetchall()
    else:
        pedidos = conn.execute('''
            SELECT p.*, u.nome as criador 
            FROM pedidos p
            JOIN usuarios u ON p.criado_por = u.id
            WHERE p.criado_por = ?
            ORDER BY p.data_criacao DESC
        ''', (session['usuario_id'],)).fetchall()
    
    conn.close()
    return jsonify([dict(pedido) for pedido in pedidos])

@app.route('/pedidos/novo', methods=['GET', 'POST'])
def novo_pedido():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    if session['usuario_tipo'] != 'admin':
        return "Acesso não autorizado", 403
    
    if request.method == 'POST':
        cliente = request.form['cliente']
        itens = request.form['itens']
        observacoes = request.form['observacoes']
        
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO pedidos (cliente, itens, observacoes, criado_por) VALUES (?, ?, ?, ?)',
            (cliente, itens, observacoes, session['usuario_id'])
        )
        pedido_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'pedido_id': pedido_id})
    
    return render_template('novo_pedido.html')

# Rotas do chat
@app.route('/chat/<int:pedido_id>')
def chat(pedido_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    pedido = conn.execute(
        'SELECT * FROM pedidos WHERE id = ?', (pedido_id,)
    ).fetchone()
    
    if not pedido:
        conn.close()
        return "Pedido não encontrado", 404
    
    if session['usuario_tipo'] != 'admin' and pedido['criado_por'] != session['usuario_id']:
        conn.close()
        return "Acesso não autorizado", 403
    
    mensagens = conn.execute('''
        SELECT m.*, u.nome as usuario_nome 
        FROM mensagens m
        JOIN usuarios u ON m.usuario_id = u.id
        WHERE m.pedido_id = ?
        ORDER BY m.data
    ''', (pedido_id,)).fetchall()
    
    conn.close()
    return render_template('chat.html', pedido=dict(pedido), mensagens=[dict(msg) for msg in mensagens])

@app.route('/chat/<int:pedido_id>/mensagens', methods=['GET', 'POST'])
def mensagens(pedido_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        texto = request.form['texto']
        
        conn.execute(
            'INSERT INTO mensagens (pedido_id, usuario_id, texto) VALUES (?, ?, ?)',
            (pedido_id, session['usuario_id'], texto)
        )
        conn.commit()
        
        mensagem = conn.execute(
            'SELECT m.*, u.nome as usuario_nome FROM mensagens m JOIN usuarios u ON m.usuario_id = u.id WHERE m.id = last_insert_rowid()'
        ).fetchone()
        conn.close()
        
        return jsonify(dict(mensagem))
    
    else:
        mensagens = conn.execute('''
            SELECT m.*, u.nome as usuario_nome 
            FROM mensagens m
            JOIN usuarios u ON m.usuario_id = u.id
            WHERE m.pedido_id = ?
            ORDER BY m.data
        ''', (pedido_id,)).fetchall()
        conn.close()
        return jsonify([dict(msg) for msg in mensagens])

if __name__ == '__main__':
    init_db()
    app.run(debug=True)