from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash  # flash para mensagens de feedback
import json
import os
import uuid  # usado para gerar IDs únicos (uuid4)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# chave necessária para utilizar `flash` e sessões
app.secret_key = "chave-super-secreta"

def carregar_usuarios():
    # Verifica se o arquivo 'usuarios.json' existe e carrega os dados
    try:
        if os.path.exists("usuarios.json"):
            with open("usuarios.json", "r", encoding="utf-8") as arquivo:
                return json.load(arquivo)
        else:
            return []  # Retorna uma lista vazia se o arquivo não existir
    except:
        return []  # Retorna uma lista vazia se ocorrer algum erro ao ler o arquivo

def salvar_usuario(usuario):
    # Carrega os usuários existentes
    usuarios = carregar_usuarios()

    try:
        # Adiciona o novo usuário à lista
        usuarios.append(usuario)

        # Salva a lista atualizada de usuários no arquivo 'usuarios.json'
        with open("usuarios.json", "w", encoding="utf-8") as arquivo:
            json.dump(usuarios, arquivo, indent=4)

        return True  # Retorna True se o salvamento for bem-sucedido
    except:
        return False  # Retorna False se ocorrer um erro ao salvar

def contar_usuarios():
    usuarios = buscar_usuarios()
    string_length = len(usuarios)
    return render_template('usuarios.html', length=string_length, text=usuarios)

def buscar_usuario_por_email(email):
    usuarios = carregar_usuarios()
    for usuario in usuarios:
        if usuario.get("email") == email:
            return usuario
    return None

def salvar_todos_usuarios(usuarios):
    try:
        with open("usuarios.json", "w", encoding="utf-8") as arquivo:
            json.dump(usuarios, arquivo, indent=4)
        return True
    except:
        return False

@app.route("/")
def home():
    # Renderiza a página inicial com o formulário de cadastro
    return render_template("index.html", campos={})

@app.route("/cadastro-usuario", methods=["GET", "POST"])
def cadastrar_usuario():
    if request.method == "POST":
        # Recupera os dados enviados pelo formulário HTML
        dados = request.form
        nome = request.form.get("nome")
        cpf = request.form.get("cpf")            # CPF do usuário (identificador único)
        email = request.form.get("email")
        idade = request.form.get("idade")
        senha = request.form.get("senha")
        senha_hash = generate_password_hash(senha) # Armazena a senha de forma segura usando hash

        # carrega usuários atuais para checar duplicatas
        usuarios = carregar_usuarios()

        # evita inserir CPF repetido
        if any(u.get("cpf") == cpf for u in usuarios):
            flash("CPF já cadastrado no sistema.", "erro")
            return render_template("cadastro-usuario.html", campos=dados)
        if int(idade) < 18:
            flash("Usuário deve ser maior de idade.", "erro")
            return render_template("cadastro-usuario.html", campos=dados)

            # cria o objeto do usuário, incluindo um id UUID
        usuario = {
            "id": str(uuid.uuid4()),  # identificador global para uso interno
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "idade": idade,
            "senha": senha_hash,
        }

        # tenta salvar usando a função auxiliar
        status = salvar_usuario(usuario)

        if status:
            # após cadastro redireciona para a lista de usuários
            flash("Usuário cadastrado com sucesso.", "sucesso")
            return redirect(url_for('buscar_usuarios'))
        else:
            # caso de erro de escrita
            flash("Não foi possível cadastrar o usuário.", "erro")
            return render_template("cadastro-usuario.html", campos=dados)
    
    return render_template("cadastro-usuario.html", campos={})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        dados = request.form
        cpf = request.form.get("cpf")
        senha = request.form.get("senha")

        usuarios = carregar_usuarios()
        usuario = next((u for u in usuarios if u.get("cpf") == cpf), None)

        if usuario and check_password_hash(usuario.get("senha"), senha):
            flash("Login bem-sucedido!", "sucesso")
            session["usuario_id"] = usuario.get("id") 
            session["usuario_senha"] = usuario.get("senha")
            return redirect(url_for("buscar_usuarios"))
        else:
            flash("CPF ou Senha incorretos!", "erro")
            return render_template("login.html", campos=dados)
    return render_template("login.html", campos={})
       
@app.route("/logout")
def logout():
    session.clear()
    flash("Logout realizado com sucesso.", "sucesso")
    return redirect(url_for("login"))

@app.route("/usuarios/json", methods=["GET"])
def buscar_usuarios_json():
    usuarios = carregar_usuarios()
    return jsonify(usuarios)

@app.route("/usuarios", methods=["GET"])
def buscar_usuarios():
    usuarios = carregar_usuarios()
    return render_template("usuarios.html", usuarios = usuarios)


@app.route("/usuarios/editar/<cpf>", methods=["GET", "POST"])
def editar_usuario(cpf):

    if "usuario_id" not in session:
        flash("Não autorizado.", "erro")
        return redirect(url_for("login"))

    usuarios = carregar_usuarios()

    # ✅ Busca usuário pelo CPF
    usuario = next((u for u in usuarios if u["cpf"] == cpf), None)

    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("buscar_usuarios"))

    # --------------------------
    # GET → Carrega formulário
    # --------------------------
    if request.method == "GET":
        return render_template("editar_usuario.html", usuario=usuario)

    # --------------------------
    # POST → Atualiza dados
    # --------------------------

    nome = request.form.get("nome")
    email = request.form.get("email")
    idade = int(request.form.get("idade"))
    senha = request.form.get("senha")

    # ✅ Validação de idade também no UPDATE
    if idade < 18:
        flash("Usuário deve ser maior de 18 anos.", "erro")
        return redirect(url_for("editar_usuario", cpf=cpf))

    usuario["nome"] = nome
    usuario["email"] = email
    usuario["idade"] = idade

    # ✅ Atualiza senha somente se preenchida
    if senha:
        usuario["senha"] = generate_password_hash(senha)

    status = salvar_todos_usuarios(usuarios)

    if status:
        flash("Usuário atualizado com sucesso.", "sucesso")
    else:
        flash("Erro ao atualizar usuário.", "erro")

    return redirect(url_for("buscar_usuarios"))

@app.route('/api/usuarios/<cpf>', methods=['PUT'])
def api_atualizar_usuario(cpf):
    dados = request.json
    # buscar usuário, validar, atualizar campos e chamar salvar_todos_usuarios
    return jsonify({'sucesso': True}), 200

@app.route("/usuarios/deletar", methods=["POST"])
def deletar_usuario():
    if "usuario_id" not in session:
        flash("Não autorizado.", "erro")
        return redirect(url_for("login"))

    cpf = request.form.get("cpf")
    if not cpf:
        flash("CPF necessário para exclusão.", "erro")
        return redirect(url_for('buscar_usuarios'))

    usuarios = carregar_usuarios()
    novos = [u for u in usuarios if u.get("cpf") != cpf]

    try:
        with open("usuarios.json", "w", encoding="utf-8") as arquivo:
            json.dump(novos, arquivo, indent=4)
        flash("Usuário removido.", "sucesso")
    except Exception as e:
        flash(f"Erro ao deletar: {e}", "erro")

    return redirect(url_for('buscar_usuarios'))

if __name__ == "__main__":
    app.run(debug=True, port=8000)
