from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import json
import os
import zipfile
import tempfile
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

USUARIOS_FILE = 'usuarios.json'
LIVROS_FILE = 'livros.json'

UPLOAD_FOLDER = os.path.join('static', 'capas')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configurações de paginação
LIVROS_POR_PAGINA = 20

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

def get_user_prestige(usuario):
    usuarios = carregar_usuarios()
    for u in usuarios:
        if u['usuario'] == usuario:
            return u.get('prestigio', 0)
    return 0

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
                session['prestigio'] = u.get('prestigio', 0)
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
            usuarios.append({'usuario': usuario, 'senha': senha, 'admin': False, 'prestigio': 0})
            salvar_usuarios(usuarios)
            return redirect(url_for('login'))
    return render_template('registrar_usuario.html', erro=erro)

@app.route('/livros')
@app.route('/livros/<int:pagina>')
def livros(pagina=1):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    livros = carregar_livros()
    total_livros = len(livros)
    total_paginas = (total_livros + LIVROS_POR_PAGINA - 1) // LIVROS_POR_PAGINA
    
    inicio = (pagina - 1) * LIVROS_POR_PAGINA
    fim = inicio + LIVROS_POR_PAGINA
    livros_pagina = livros[inicio:fim]
    
    return render_template('livros.html', 
                         livros=livros_pagina, 
                         pagina_atual=pagina,
                         total_paginas=total_paginas,
                         prestigio=session.get('prestigio', 0))

@app.route('/livro/<int:id>')
def livro_detalhes(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livro = livros[id]
    return render_template('detalhes.html', livro=livro, id=id, prestigio=session.get('prestigio', 0))

@app.route('/alugar/<int:id>')
def alugar(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 1:
        return "Acesso negado - Prestígio insuficiente", 403
    
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
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 1:
        return "Acesso negado - Prestígio insuficiente", 403
    
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livros[id]['disponivel'] = True
    salvar_livros(livros)
    return redirect(url_for('livros'))

@app.route('/registrar', methods=['GET','POST'])
def registrar():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 2:
        return "Acesso negado - Prestígio insuficiente", 403

    if request.method == 'POST':
        livros = carregar_livros()
        imagem = request.files.get('imagem')
        imagem_url = ''

        if imagem and imagem.filename != '':
            filename = secure_filename(imagem.filename)
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagem.save(caminho)
            imagem_url = f'capas/{filename}'

        novo = {
            'titulo': request.form['titulo'],
            'autor': request.form['autor'],
            'ano': request.form['ano'],
            'sinopse': request.form.get('sinopse', ''),
            'imagem_url': imagem_url,
            'disponivel': True
        }
        livros.append(novo)
        salvar_livros(livros)
        return redirect(url_for('livros'))

    return render_template('registrar.html')

@app.route('/editar/<int:id>', methods=['GET','POST'])
def editar(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 2:
        return "Acesso negado - Prestígio insuficiente", 403
    
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    if request.method == 'POST':
        livros[id]['titulo'] = request.form['titulo']
        livros[id]['autor'] = request.form['autor']
        livros[id]['ano'] = request.form['ano']
        livros[id]['sinopse'] = request.form.get('sinopse', '')
        salvar_livros(livros)
        return redirect(url_for('livros'))
    return render_template('editar.html', livro=livros[id], id=id)

@app.route('/remover/<int:id>')
def remover(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 2:
        return "Acesso negado - Prestígio insuficiente", 403
    
    livros = carregar_livros()
    if id < 0 or id >= len(livros):
        return "Livro não encontrado", 404
    livros.pop(id)
    salvar_livros(livros)
    return redirect(url_for('livros'))

@app.route('/gerenciar_usuarios')
def gerenciar_usuarios():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 3:
        return "Acesso negado - Prestígio insuficiente", 403
    
    usuarios = carregar_usuarios()
    return render_template('gerenciar_usuarios.html', usuarios=usuarios)

@app.route('/alterar_prestigio/<usuario>', methods=['POST'])
def alterar_prestigio(usuario):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 3:
        return "Acesso negado - Prestígio insuficiente", 403
    
    novo_prestigio = int(request.form['prestigio'])
    usuarios = carregar_usuarios()
    
    for u in usuarios:
        if u['usuario'] == usuario:
            u['prestigio'] = novo_prestigio
            break
    
    salvar_usuarios(usuarios)
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/remover_usuario/<usuario>')
def remover_usuario(usuario):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 3:
        return "Acesso negado - Prestígio insuficiente", 403
    
    # Não permitir que o usuário se remova
    if usuario == session['usuario']:
        return "Não é possível remover sua própria conta", 400
    
    usuarios = carregar_usuarios()
    usuarios = [u for u in usuarios if u['usuario'] != usuario]
    salvar_usuarios(usuarios)
    return redirect(url_for('gerenciar_usuarios'))

@app.route('/exportar_dados')
def exportar_dados():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 2:
        return "Acesso negado - Prestígio insuficiente", 403
    
    # Criar arquivo temporário ZIP
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, 'biblioteca_backup.zip')
    
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        # Adicionar arquivos JSON
        if os.path.exists(LIVROS_FILE):
            zipf.write(LIVROS_FILE, 'livros.json')
        if os.path.exists(USUARIOS_FILE):
            zipf.write(USUARIOS_FILE, 'usuarios.json')
        
        # Adicionar pasta de capas
        capas_dir = os.path.join('static', 'capas')
        if os.path.exists(capas_dir):
            for root, dirs, files in os.walk(capas_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, 'static')
                    zipf.write(file_path, arcname)
    
    return send_file(zip_path, as_attachment=True, download_name='biblioteca_backup.zip')

@app.route('/importar_dados', methods=['GET', 'POST'])
def importar_dados():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    prestigio = session.get('prestigio', 0)
    if prestigio < 2:
        return "Acesso negado - Prestígio insuficiente", 403
    
    if request.method == 'POST':
        arquivo = request.files.get('arquivo')
        if arquivo and arquivo.filename.endswith('.zip'):
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, 'upload.zip')
            arquivo.save(zip_path)
            
            try:
                with zipfile.ZipFile(zip_path, 'r') as zipf:
                    # Extrair arquivos JSON
                    if 'livros.json' in zipf.namelist():
                        zipf.extract('livros.json', temp_dir)
                        shutil.move(os.path.join(temp_dir, 'livros.json'), LIVROS_FILE)
                    
                    if 'usuarios.json' in zipf.namelist():
                        zipf.extract('usuarios.json', temp_dir)
                        shutil.move(os.path.join(temp_dir, 'usuarios.json'), USUARIOS_FILE)
                    
                    # Extrair capas
                    for file_info in zipf.infolist():
                        if file_info.filename.startswith('capas/'):
                            zipf.extract(file_info, 'static')
                
                flash('Dados importados com sucesso!', 'success')
            except Exception as e:
                flash(f'Erro ao importar dados: {str(e)}', 'error')
            finally:
                shutil.rmtree(temp_dir)
        else:
            flash('Por favor, selecione um arquivo .zip válido', 'error')
    
    return render_template('importar_dados.html')

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

if __name__ == '__main__':
    app.run(debug=True)