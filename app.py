from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash  # flash para mensagens de feedback
import json
import os
import uuid  # usado para gerar IDs únicos (uuid4)
from werkzeug.security import generate_password_hash, check_password_hash
import re

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
    
def cpf_valido(cpf):
    cpf = re.sub(r'\D', '', cpf)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        digito = (soma * 10 % 11) % 10
        if digito != int(cpf[i]):
            return False
    return True

@app.route("/")
def home():
    # Renderiza a página inicial com o formulário de cadastro
    return render_template("index.html", campos={})

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/cadastro-usuario", methods=["GET", "POST"])
def cadastrar_usuario():
    if request.method == "POST":
        dados = request.form
        nome = request.form.get("nome")
        cpf_sujo = dados.get("cpf")
        cpf_limpo = re.sub(r'\D', '', cpf_sujo)
        email = request.form.get("email")
        idade = request.form.get("idade")
        senha = request.form.get("senha")
        senha_hash = generate_password_hash(senha) # Armazena a senha de forma segura usando hash
        cargo = request.form.get("cargo", "comum")

        if not cpf_valido(cpf_limpo):
            flash("CPF inválido. Verifique os números digitados.", "erro")
            return render_template("cadastro-usuario.html", campos=dados)
        # carrega usuários atuais para checar duplicatas
        usuarios = carregar_usuarios()

        # evita inserir CPF repetido
        if any(u.get("cpf") == cpf_limpo for u in usuarios):
            flash("CPF já cadastrado no sistema.", "erro")
            return render_template("cadastro-usuario.html", campos=dados)
        if int(idade) < 18:
            flash("Usuário deve ser maior de idade.", "erro")
            return render_template("cadastro-usuario.html", campos=dados)

            # cria o objeto do usuário, incluindo um id UUID
        usuario = {
            "id": str(uuid.uuid4()),  # identificador global para uso interno
            "nome": nome,
            "cpf": cpf_limpo,
            "email": email,
            "idade": idade,
            "senha": senha_hash,
            "cargo": cargo
        }

        # tenta salvar usando a função auxiliar
        status = salvar_usuario(usuario)

        if status:
            # após cadastro redireciona para a lista de usuários
            flash("Usuário cadastrado com sucesso.", "sucesso")
            return redirect(url_for('login'))
        else:
            # caso de erro de escrita
            flash("Não foi possível cadastrar o usuário.", "erro")
            return render_template("cadastro-usuario.html", campos=dados)
    
    return render_template("cadastro-usuario.html", campos={})

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        dados = request.form
        cpf_com_mascara = request.form.get("cpf")
        cpf_input = re.sub(r'\D', '', cpf_com_mascara)
        senha = request.form.get("senha")

        usuarios = carregar_usuarios()
        usuario = next((u for u in usuarios if str(u.get("cpf")) == cpf_input), None)

        if usuario and check_password_hash(usuario.get("senha"), senha):
            session.clear()
            flash("Login bem-sucedido!", "sucesso")
            session["usuario_id"] = str(usuario.get("id"))
            session["usuario_cpf"] = str(usuario.get("cpf"))
            session["cargo"] = usuario.get("cargo", "comum")
            session["usuario_nome"] = usuario.get("nome", "Usuário")
            return redirect(url_for("buscar_usuarios"))
        else:
            flash("CPF ou Senha incorretos!", "erro")
            return render_template("login.html", campos=dados)
    return render_template("login.html", campos={})

@app.route("/buscar-usuario")
def buscar_usuario():
    termo = request.args.get("termo", "").strip()
    todos_usuarios = carregar_usuarios()
    usuarios_filtrados = []
    mensagem_erro = None

    if termo:
        # Limpa o termo caso o usuário digite CPF com pontos para comparar com o banco limpo
        termo_cpf_limpo = re.sub(r'\D', '', termo)
        
        for u in todos_usuarios:
            # Comparação EXATA (Igualdade estrita)
            nome_exato = (u.get("nome") == termo) 
            cpf_exato = (u.get("cpf") == termo_cpf_limpo)
            
            if nome_exato or cpf_exato:
                usuarios_filtrados.append(u)
        
        # Se houve busca mas ninguém foi encontrado exatamente
        if not usuarios_filtrados:
            mensagem_erro = f"Erro: Nenhum usuário encontrado com o Nome ou CPF exato: '{termo}'"
    else:
        # Se não houver busca, mostra todos normalmente
        usuarios_filtrados = todos_usuarios

    return render_template("usuarios.html", 
                           usuarios=usuarios_filtrados, 
                           busca=termo, 
                           erro_busca=mensagem_erro)

@app.route("/ordem-usuarios")
def ordem_usuarios():
    termo = request.args.get("termo", "").strip()
    ordem = request.args.get("ordem", "")
    
    todos_usuarios = carregar_usuarios()
    usuarios_filtrados = []
    mensagem_erro = None

    if termo:
        termo_cpf_limpo = re.sub(r'\D', '', termo)
        for u in todos_usuarios:
            if u.get("nome") == termo or u.get("cpf") == termo_cpf_limpo:
                usuarios_filtrados.append(u)
        
        if not usuarios_filtrados:
            mensagem_erro = f"Nenhum usuário encontrado com o Nome ou CPF exato: '{termo}'"
    else:
        usuarios_filtrados = todos_usuarios

    if ordem == "asc":
        usuarios_filtrados = sorted(usuarios_filtrados, key=lambda x: int(x.get("idade", 0)))
    elif ordem == "desc":
        usuarios_filtrados = sorted(usuarios_filtrados, key=lambda x: int(x.get("idade", 0)), reverse=True)

    return render_template("usuarios.html", 
                           usuarios=usuarios_filtrados, 
                           busca=termo, 
                           ordem=ordem,
                           erro_busca=mensagem_erro)

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

    if "usuario_id" not in session:
        flash("Acesso negado. Por favor, faça login.", "erro")
        return redirect(url_for("login"))
        
    usuarios = carregar_usuarios()
    return render_template("usuarios.html", usuarios=usuarios)

@app.route("/usuarios/editar/<cpf>", methods=["GET", "POST"])
def editar_usuario(cpf):
    if "usuario_id" not in session:
        flash("Acesso negado. Por favor, faça login.", "erro")
        return redirect(url_for("login"))

    cpf_url_limpo = re.sub(r'\D', '', str(cpf))
    cpf_sessao_limpo = re.sub(r'\D', '', str(session.get("usuario_cpf", "")))
    eh_admin = session.get("cargo") == "admin"

    if not eh_admin and cpf_sessao_limpo != cpf_url_limpo:
        flash("Você só pode editar sua própria conta!", "erro")
        return redirect(url_for("buscar_usuarios"))

    usuarios = carregar_usuarios()
    
    usuario = next((u for u in usuarios if re.sub(r'\D', '', str(u.get("cpf", ""))) == cpf_url_limpo), None)

    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("buscar_usuarios"))

    # --------------------------
    # GET → Carrega e exibe o formulário
    # --------------------------
    if request.method == "GET":
        return render_template("editar_usuario.html", usuario=usuario)

    # --------------------------
    # POST → Processa os dados enviados e atualiza
    # --------------------------
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        idade_str = request.form.get("idade")
        senha = request.form.get("senha")

        try:
            idade = int(idade_str)
        except (ValueError, TypeError):
            flash("Idade inválida.", "erro")
            return redirect(url_for("editar_usuario", cpf=cpf))

        # ✅ Validação de idade também no UPDATE
        if idade < 18:
            flash("Usuário deve ser maior de 18 anos.", "erro")
            return redirect(url_for("editar_usuario", cpf=cpf))

        # ✅ Atualiza os dados comuns
        usuario["nome"] = nome
        usuario["email"] = email
        usuario["idade"] = idade

        # ✅ Atualiza senha somente se o campo não estiver vazio
        if senha:
            usuario["senha"] = generate_password_hash(senha)

        # ✅ Salva as alterações
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

@app.route("/usuarios/deletar", methods=["GET", "POST"])
def deletar_usuario():

    if session.get("cargo") != "admin":
        flash("Apenas administradores podem excluir usuários.", "erro")
        return redirect(url_for('buscar_usuarios'))
    
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
