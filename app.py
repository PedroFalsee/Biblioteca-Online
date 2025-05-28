from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

USUARIOS_FILE = 'usuarios.json'
LIVROS_FILE = 'livros.json'

UPLOAD_FOLDER = os.path.join('static', 'capas')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def carregar_usuarios():
    if not os.path.exists(USUARIOS_FILE):
        return []
    with open(USUARIOS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_usuarios(usuarios):
    with open(USUARIOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(usuarios, f, indent=4, ensure_ascii=False)

def carregar_livros():
    if not os.path.exists(LIVROS_FILE):
        return []
    with open(LIVROS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def salvar_livros(livros):
    with open(LIVROS_FILE, 'w', encoding='utf-8') as f:
        json.dump(livros, f, indent=4, ensure_ascii=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET','POST'])
def login():
    erro = None
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        usuarios = carregar_usuarios()
        for u in usuarios:
            if u['usuario'] == usuario and u['senha'] == senha:
                session['usuario'] = usuario
                session['admin'] = u.get('admin', False)
                return redirect(url_for('livros'))
        erro = 'Usuário ou senha inválidos'
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/registrar_usuario', methods=['GET','POST'])
def registrar_usuario():
    erro = None
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        usuarios = carregar_usuarios()
        if any(u['usuario'] == usuario for u in usuarios):
            erro = 'Usuário já existe'
        else:
            usuarios.append({'usuario': usuario, 'senha': senha, 'admin': False})
            salvar_usuarios(usuarios)
            return redirect(url_for('login'))
    return render_template('registrar_usuario.html', erro=erro)

@app.route('/livros')
def livros():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    livros = carregar_livros()
    return render_template('livros.html', livros=livros)

@app.route('/livro/<int:id>')
def livro_detalhes(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livro = livros[id]
    return render_template('detalhes.html', livro=livro, id=id)

@app.route('/alugar/<int:id>')
def alugar(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    if not livros[id]['disponivel']:
        return "Livro já alugado", 400
    livros[id]['disponivel'] = False
    salvar_livros(livros)
    return redirect(url_for('livros'))

@app.route('/devolver/<int:id>')
def devolver(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livros[id]['disponivel'] = True
    salvar_livros(livros)
    return redirect(url_for('livros'))

@app.route('/registrar', methods=['GET','POST'])
def registrar():
    if 'usuario' not in session or not session.get('admin', False):
        return "Acesso negado", 403

    if request.method == 'POST':
        livros = carregar_livros()
        imagem = request.files.get('imagem')
        imagem_url = ''

        if imagem and imagem.filename != '':
            filename = secure_filename(imagem.filename)
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagem.save(caminho)
            imagem_url = f'capas/{filename}'  # caminho relativo para uso no HTML

        novo = {
            'titulo': request.form['titulo'],
            'autor': request.form['autor'],
            'ano': request.form['ano'],
            'imagem_url': imagem_url,
            'disponivel': True
        }
        livros.append(novo)
        salvar_livros(livros)
        return redirect(url_for('livros'))

    return render_template('registrar.html')

@app.route('/editar/<int:id>', methods=['GET','POST'])
def editar(id):
    if 'usuario' not in session or not session.get('admin', False):
        return "Acesso negado", 403
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    if request.method == 'POST':
        livros[id]['titulo'] = request.form['titulo']
        livros[id]['autor'] = request.form['autor']
        livros[id]['ano'] = request.form['ano']
        salvar_livros(livros)
        return redirect(url_for('livros'))
    return render_template('editar.html', livro=livros[id], id=id)

@app.route('/remover/<int:id>')
def remover(id):
    if 'usuario' not in session or not session.get('admin', False):
        return "Acesso negado", 403
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livros.pop(id)
    salvar_livros(livros)
    return redirect(url_for('livros'))

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

if __name__ == '__main__':
    app.run(debug=True)
