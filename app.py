from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from database import engine
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "chave_secreta"

def atualizar_status_emprestimos():
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE Emprestimos 
            SET Status_emprestimo = 'atrasado' 
            WHERE Status_emprestimo = 'pendente' 
            AND Data_devolucao_prevista < CURDATE()
        """))
        conn.commit()

@app.before_request
def before_request():
    atualizar_status_emprestimos()

@app.context_processor
def inject_today_date():
    return {'today': datetime.now().date()}

@app.route('/')
def index():
    return render_template('index.html')

#---Usuários ---

# Cadastro Usuários
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        telefone = request.form['telefone']
        data_inscricao = request.form['data_inscricao']
        senha = request.form['senha']
        
        import re
        
        telefone_limpo = telefone.strip() if telefone else ""
        padrao_valido = re.match(r'^\(\d{2}\)\s*9?\s*\d{4}-\d{4}$', telefone_limpo)
        
        if telefone and not padrao_valido:
            flash('Formato de telefone inválido. Use (XX) 9XXXX-XXXX', 'danger')
            return render_template('usuarios/cadastro.html')
        
        hash_senha = generate_password_hash(senha)

        with engine.connect() as conn:
            try:
                conn.execute(text("""
                    INSERT INTO usuarios (nome_usuario, email, numero_telefone, data_inscricao, multa_atual, senha)
                    VALUES (:nome, :email, :telefone, :data, 0.00, :senha)
                """), {"nome": nome, "email": email, "telefone": telefone, "data": data_inscricao, "senha": hash_senha})
                conn.commit()
                
                flash('Cadastro realizado com sucesso! Faça login.', 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                error_msg = str(e)
                
                if "Email já cadastrado" in error_msg:
                    flash('Este email já está cadastrado no sistema!', 'danger')
                
                elif "Formato de telefone inválido" in error_msg:
                    flash('Telefone no formato incorreto!', 'danger')
                
                else:
                    flash(f'Erro no cadastro: {error_msg[:100]}', 'danger')
                
                return render_template('usuarios/cadastro.html')

    return render_template('usuarios/cadastro.html')

# Login Usuários
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        with engine.connect() as conn:
            usuario = conn.execute(text("SELECT * FROM usuarios WHERE email = :email"), {"email": email}).fetchone()

        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id_usuario
            session['usuario_nome'] = usuario.nome_usuario
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou senha incorretos.', 'danger')

    return render_template('usuarios/login.html')

# LOGOUT 
@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('index'))

# Listar Gêneros 
@app.route('/generos')
def listar_generos():
    with engine.connect() as conn:
        generos = conn.execute(text("SELECT * FROM generos")).fetchall()
    return render_template('generos/listar_genero.html', dados=generos, tabela='generos')

# Cadastrar Gêneros 
@app.route('/generos/novo', methods=['GET', 'POST'])
def novo_genero():
    if request.method == 'POST':
        nome = request.form['nome']
        with engine.connect() as conn:
            conn.execute(text("INSERT INTO generos (nome_genero) VALUES (:nome)"), {"nome": nome})
            conn.commit()
        flash('Gênero adicionado com sucesso!', 'success')
        return redirect(url_for('listar_generos'))
    return render_template('generos/cadastrar_genero.html', tabela='generos', dado=None)

# Editar Gêneros 
@app.route('/generos/editar/<int:id>', methods=['GET', 'POST'])
def editar_genero(id):
    with engine.connect() as conn:
        if request.method == 'POST':
            nome = request.form['nome']
            conn.execute(text("UPDATE generos SET nome_genero=:nome WHERE id_genero=:id"),
                         {"nome": nome, "id": id})
            conn.commit()
            flash('Gênero atualizado com sucesso!', 'success')
            return redirect(url_for('listar_generos'))

        genero = conn.execute(text("SELECT * FROM generos WHERE id_genero=:id"), {"id": id}).fetchone()
    return render_template('generos/editar_genero.html', tabela='generos', dado=genero)

# Excluir Gêneros 
@app.route('/generos/excluir/<int:id>')
def excluir_genero(id):
    with engine.connect() as conn:
        try:
            conn.execute(text("DELETE FROM generos WHERE id_genero=:id"), {"id": id})
            conn.commit()
            flash('Gênero excluído com sucesso!', 'success')
        except:
            flash('Gênero não pode ser excluído!', 'danger')
        finally:
            conn.close()

    
    return redirect(url_for('listar_generos'))

#---AUTORES ---

# Listar Autores
@app.route("/autores")
def listar_autor():
    with engine.connect() as conn:
        autores = conn.execute(text("SELECT * FROM Autores")).fetchall()
    return render_template("autores/listar_autor.html", autores=autores)

# Cadastrar Autores
@app.route("/autores/cadastrar_autor", methods=["GET", "POST"])
def cadastrar_autor():
    if request.method == "POST":
        nome = request.form.get("nome")
        nacionalidade = request.form.get("nacionalidade")
        nascimento = request.form.get("nascimento")
        biografia = request.form.get("biografia")

        with engine.begin() as conn:
    
            autor_existente = conn.execute(
                text("SELECT * FROM Autores WHERE Nome_autor = :nome"),
                {"nome": nome}
            ).fetchone()

            if autor_existente:
                flash("Autor já cadastrado!", "error")

            else:
                conn.execute(
                    text("""
                        INSERT INTO Autores 
                            (Nome_autor, Nacionalidade, Data_nascimento, Biografia)
                        VALUES 
                            (:nome, :nacionalidade, :data_nascimento, :biografia)
                    """),
                    {
                        "nome": nome,
                        "nacionalidade": nacionalidade,
                        "data_nascimento": nascimento,
                        "biografia": biografia
                    }
                )
                flash("Autor cadastrado com sucesso!", "success")
        return redirect(url_for("listar_autor"))

    return render_template("autores/cadastrar_autor.html")
       
# Editar Autores
@app.route("/autores/editar_autor/<int:id>", methods=["GET", "POST"])
def editar_autor(id):
    with engine.connect() as conn:
        autor = conn.execute(
            text("SELECT * FROM Autores WHERE ID_autor = :id"), {"id": id}
        ).fetchone()

    if not autor:
        flash("Autor não encontrado!", "error")
        return redirect(url_for("listar_autor"))

    if request.method == "POST":
        nome = request.form.get("nome")
        nacionalidade = request.form.get("nacionalidade")
        nascimento = request.form.get("nascimento")
        biografia = request.form.get("biografia")

        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE Autores
                    SET Nome_autor = :nome,
                        Nacionalidade = :nacionalidade,
                        Data_nascimento = :data_nascimento,
                        Biografia = :biografia
                    WHERE ID_autor = :id
                """),
                {
                    "nome": nome,
                    "nacionalidade": nacionalidade,
                    "data_nascimento": nascimento,
                    "biografia": biografia,
                    "id": id
                }
            )
        flash("Autor atualizado com sucesso!", "success")
        return redirect(url_for("listar_autor"))

    return render_template("autores/editar_autor.html", autor=autor)

# Excluir Autores
@app.route("/autores/excluir_autor/<int:id>")
def excluir_autor(id):
    with engine.begin() as conn:
        try:
            conn.execute(
            text("DELETE FROM Autores WHERE ID_autor = :id"),
            {"id": id}
        )
            conn.commit()
            flash('Autor excluído com sucesso!', 'success')
        except:
            flash('Autor não pode ser excluído!', 'danger')
        finally:
            conn.close()
    return redirect(url_for("listar_autor"))


#---EDITORAS ---

# Listar Editoras
@app.route("/editoras")
def listar_editora():
    with engine.connect() as conn:
        editoras = conn.execute(text("SELECT * FROM Editoras")).fetchall()
    return render_template("editoras/listar_editora.html", editoras=editoras)

# Cadastrar Editoras
@app.route("/editoras/cadastrar_editora", methods=["GET", "POST"])
def cadastrar_editora():
    if request.method == "POST":
        nome = request.form.get("nome")
        endereco = request.form.get("endereco")

        with engine.begin() as conn:
            editora_existente = conn.execute(
                text("SELECT * FROM Editoras WHERE Nome_editora = :nome"),
                {"nome": nome}
            ).fetchone()

            if editora_existente:
                flash("Editora já cadastrada!", "error")
            else:
                conn.execute(
                    text("""
                        INSERT INTO Editoras (Nome_editora, Endereco_editora)
                        VALUES (:nome, :endereco)
                    """),
                    {"nome": nome, "endereco": endereco}
                )
                flash("Editora cadastrada com sucesso!", "success")
        return redirect(url_for("listar_editora"))

    return render_template("editoras/cadastrar_editora.html")

# Editar Editoras
@app.route("/editoras/editar_editora/<int:id>", methods=["GET", "POST"])
def editar_editora(id):
    with engine.connect() as conn:
        editora = conn.execute(
            text("SELECT * FROM Editoras WHERE ID_editora = :id"),
            {"id": id}
        ).fetchone()

    if not editora:
        flash("Editora não encontrada!", "error")
        return redirect(url_for("listar_editora"))

    if request.method == "POST":
        nome = request.form.get("nome")
        endereco = request.form.get("endereco")

        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE Editoras
                    SET Nome_editora = :nome,
                        Endereco_editora = :endereco
                    WHERE ID_editora = :id
                """),
                {"nome": nome, "endereco": endereco, "id": id}
            )
        flash("Editora atualizada com sucesso!", "success")
        return redirect(url_for("listar_editora"))

    return render_template("editoras/editar_editora.html", editora=editora)

# Excluir Editoras
@app.route("/editoras/excluir_editora/<int:id>")
def excluir_editora(id):
    with engine.begin() as conn:
        try:
            conn.execute(
            text("DELETE FROM Editoras WHERE ID_editora = :id"),
            {"id": id}
        )
            conn.commit()
            flash('Editora excluído com sucesso!', 'success')
        except:
            flash('Editora não pode ser excluída!', 'danger')
        finally:
            conn.close()
    return redirect(url_for("listar_editora"))

#---Usuários ---

# Listar Usuários
@app.route('/usuarios')
def listar_usuarios():
    with engine.connect() as conn:
        usuarios = conn.execute(text("SELECT id_usuario, nome_usuario, email, numero_telefone, data_inscricao, multa_atual FROM usuarios")).fetchall()
    return render_template('usuarios/listar_usuario.html', dados=usuarios, tabela='usuarios')

# Editar Usuários
@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    with engine.connect() as conn:
        if request.method == 'POST':
            nome = request.form['nome']
            email = request.form['email']
            telefone = request.form['telefone']
            data = request.form['data_inscricao']
            multa = request.form['multa']
            conn.execute(text("""
                UPDATE usuarios
                SET nome_usuario=:nome, email=:email, numero_telefone=:telefone, data_inscricao=:data, multa_atual=:multa
                WHERE id_usuario=:id
            """), {"nome": nome, "email": email, "telefone": telefone, "data": data, "multa": multa, "id": id})
            conn.commit()
            flash('Usuário atualizado com sucesso!', 'success')
            return redirect(url_for('listar_usuarios'))

        usuario = conn.execute(text("SELECT * FROM usuarios WHERE id_usuario=:id"), {"id": id}).fetchone()
    return render_template('usuarios/editar_usuario.html', tabela='usuarios', dado=usuario)

# Excluir Usuários
@app.route('/usuarios/excluir/<int:id>')
def excluir_usuario(id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM usuarios WHERE id_usuario=:id"), {"id": id})
        conn.commit()
        try:
            flash('Usuário excluído com sucesso!', 'success')
        except:
            flash('Usuário não pode ser excluído!', 'danger')
        finally:
            conn.close()
    return redirect(url_for('listar_usuarios'))

# Listar Livros
@app.route("/livros")
def listar_livros():
    with engine.connect() as conn:
        livros = conn.execute(text("""
            SELECT l.*, a.Nome_autor, g.nome_genero, e.Nome_editora 
            FROM Livros l
            LEFT JOIN Autores a ON l.Autor_id = a.ID_autor
            LEFT JOIN generos g ON l.Genero_id = g.id_genero
            LEFT JOIN Editoras e ON l.Editora_id = e.ID_editora
        """)).fetchall()
    return render_template("livros/listar_livro.html", livros=livros)

# Cadastrar Livros
@app.route("/livros/criar_livro", methods=["GET", "POST"])
def criar_livro():
    with engine.connect() as conn:
        autores = conn.execute(text("SELECT * FROM Autores")).fetchall()
        generos = conn.execute(text("SELECT * FROM generos")).fetchall()
        editoras = conn.execute(text("SELECT * FROM Editoras")).fetchall()
        
    if request.method == "POST":
        titulo = request.form.get("titulo")
        autor_id = request.form.get("autor_id")
        isbn = request.form.get("isbn")
        ano_publicacao = request.form.get("ano_publicacao")
        genero_id = request.form.get("genero_id")
        editora_id = request.form.get("editora_id")
        quantidade = request.form.get("quantidade")
        resumo = request.form.get("resumo")

        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO Livros 
                        (Titulo, Autor_id, ISBN, Ano_publicacao, Genero_id, Editora_id, Quantidade_disponivel, Resumo) 
                        VALUES (:titulo, :autor_id, :isbn, :ano_publicacao, :genero_id, :editora_id, :quantidade, :resumo)
                    """),
                    {
                        "titulo": titulo,
                        "autor_id": autor_id,
                        "isbn": isbn,
                        "ano_publicacao": ano_publicacao,
                        "genero_id": genero_id,
                        "editora_id": editora_id,
                        "quantidade": quantidade,
                        "resumo": resumo
                    }
                )
            
            flash("Livro criado com sucesso!", "success")
            return redirect(url_for("listar_livros"))
            
        except Exception as e:
            error_msg = str(e)
            if "Quantidade de livros não pode ser negativa" in error_msg:
                flash('Quantidade não pode ser negativa!', 'danger')
            else:
                flash('Erro ao criar livro', 'danger')
            
            return render_template("livros/criar_livro.html", 
                                 autores=autores, 
                                 generos=generos, 
                                 editoras=editoras)

    return render_template("livros/criar_livro.html", autores=autores, generos=generos, editoras=editoras)

# Editar Livros
@app.route("/livros/editar_livro/<int:id>", methods=["GET", "POST"])
def editar_livro(id):
    with engine.connect() as conn:
        livro = conn.execute(
            text("SELECT * FROM Livros WHERE ID_livro = :id"), {"id": id}
        ).fetchone()
        
        autores = conn.execute(text("SELECT * FROM Autores")).fetchall()
        generos = conn.execute(text("SELECT * FROM generos")).fetchall()
        editoras = conn.execute(text("SELECT * FROM Editoras")).fetchall()
    
    if not livro:
        flash("Livro não encontrado!", "error")
        return redirect(url_for("listar_livros"))

    if request.method == "POST":
        titulo = request.form.get("titulo")
        autor_id = request.form.get("autor_id")
        isbn = request.form.get("isbn")
        ano_publicacao = request.form.get("ano_publicacao")
        genero_id = request.form.get("genero_id")
        editora_id = request.form.get("editora_id")
        quantidade = request.form.get("quantidade")
        resumo = request.form.get("resumo")
        
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        UPDATE Livros
                        SET Titulo = :titulo,
                            Autor_id = :autor_id,
                            ISBN = :isbn,
                            Ano_publicacao = :ano_publicacao,
                            Genero_id = :genero_id,
                            Editora_id = :editora_id,
                            Quantidade_disponivel = :quantidade,
                            Resumo = :resumo
                        WHERE ID_livro = :id
                    """),
                    {
                        "titulo": titulo,
                        "autor_id": autor_id,
                        "isbn": isbn,
                        "ano_publicacao": ano_publicacao,
                        "genero_id": genero_id,
                        "editora_id": editora_id,
                        "quantidade": quantidade,
                        "resumo": resumo,
                        "id": id
                    }
                )
            
            flash("Livro atualizado com sucesso!", "success")
            return redirect(url_for("listar_livros"))
            
        except Exception as e:
            error_msg = str(e)
            if "Quantidade de livros não pode ser negativa" in error_msg:
                flash('Quantidade não pode ser negativa!', 'danger')
            else:
                flash('Erro ao atualizar livro', 'danger')
            
            return render_template("livros/editar_livro.html", 
                                 livro=livro, 
                                 autores=autores, 
                                 generos=generos, 
                                 editoras=editoras)

    return render_template("livros/editar_livro.html", 
                         livro=livro, autores=autores, generos=generos, editoras=editoras)

# Excluir Livros
@app.route("/livros/excluir_livro/<int:id>")
def excluir_livro(id):
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM Livros WHERE ID_livro = :id"),
            {"id": id}
        )
    flash("Livro excluído com sucesso!", "success")
    return redirect(url_for("listar_livros"))

#---EMPRÉSTIMOS ---

# Listar Empréstimos
@app.route("/emprestimos")
def listar_emprestimos():
    with engine.connect() as conn:
        emprestimos = conn.execute(text("""
            SELECT e.*, u.nome_usuario, l.Titulo 
            FROM Emprestimos e
            LEFT JOIN usuarios u ON e.Usuario_id = u.id_usuario
            LEFT JOIN Livros l ON e.Livro_id = l.ID_livro
            ORDER BY e.Data_emprestimo DESC
        """)).fetchall()
    return render_template("emprestimos/listar_emprestimo.html", emprestimos=emprestimos)

# Criar Empréstimo
@app.route("/emprestimos/novo", methods=["GET", "POST"])
def novo_emprestimo():
    with engine.connect() as conn:
        usuarios = conn.execute(
            text("SELECT id_usuario, nome_usuario, multa_atual FROM usuarios")
        ).fetchall()
        
        livros = conn.execute(text("SELECT * FROM Livros WHERE Quantidade_disponivel > 0")).fetchall()
        
    if request.method == "POST":
        usuario_id = request.form.get("usuario_id")
        livro_id = request.form.get("livro_id")
        data_emprestimo = request.form.get("data_emprestimo")
        data_devolucao_prevista = request.form.get("data_devolucao_prevista")
        
        from datetime import datetime, timedelta
        
        data_emprestimo_obj = datetime.strptime(data_emprestimo, '%Y-%m-%d')
        
        if not data_devolucao_prevista:
            data_devolucao_prevista_obj = data_emprestimo_obj + timedelta(days=20)
        else:
            data_devolucao_prevista_obj = datetime.strptime(data_devolucao_prevista, '%Y-%m-%d')
        
        data_devolucao_prevista_str = data_devolucao_prevista_obj.strftime('%Y-%m-%d')
        
        if data_devolucao_prevista_obj.date() < data_emprestimo_obj.date():
            flash('Data de devolução não pode ser anterior à data de empréstimo.', 'danger')
            return render_template("emprestimos/novo_emprestimo.html", 
                                usuarios=usuarios, 
                                livros=livros)
        
        if data_emprestimo_obj.date() > datetime.now().date():
            flash('Data de empréstimo não pode ser futura.', 'danger')
            return render_template("emprestimos/novo_emprestimo.html", 
                                usuarios=usuarios, 
                                livros=livros)
        
        with engine.begin() as conn:
            usuario_info = conn.execute(
                text("SELECT nome_usuario, multa_atual FROM usuarios WHERE id_usuario = :id"),
                {"id": usuario_id}
            ).fetchone()
            
            mensagem_aviso = ""
            if usuario_info and usuario_info.multa_atual > 0:
                mensagem_aviso = f" Usuário possui multa pendente de R$ {usuario_info.multa_atual:.2f}."
            
            conn.execute(
                text("""
                    INSERT INTO Emprestimos 
                    (Usuario_id, Livro_id, Data_emprestimo, Data_devolucao_prevista, Status_emprestimo) 
                    VALUES (:usuario_id, :livro_id, :data_emprestimo, :data_devolucao_prevista, 'pendente')
                """),
                {
                    "usuario_id": usuario_id,
                    "livro_id": livro_id,
                    "data_emprestimo": data_emprestimo,
                    "data_devolucao_prevista": data_devolucao_prevista_str
                }
            )
            
        flash(f"Empréstimo realizado com sucesso! Data de devolução: {data_devolucao_prevista_str}.{mensagem_aviso}", 
              "warning" if mensagem_aviso else "success")
        return redirect(url_for("listar_emprestimos"))

    return render_template("emprestimos/novo_emprestimo.html", usuarios=usuarios, livros=livros)

# Devolver empréstimo
@app.route("/emprestimos/devolver/<int:id>", methods=["GET", "POST"])
def devolver_emprestimo(id):
    with engine.connect() as conn:
        emprestimo = conn.execute(
            text("""
                SELECT e.*, u.nome_usuario, l.Titulo, l.ID_livro 
                FROM Emprestimos e
                LEFT JOIN usuarios u ON e.Usuario_id = u.id_usuario
                LEFT JOIN Livros l ON e.Livro_id = l.ID_livro
                WHERE e.ID_emprestimo = :id
            """),
            {"id": id}
        ).fetchone()

    if not emprestimo:
        flash("Empréstimo não encontrado!", "error")
        return redirect(url_for("listar_emprestimos"))

    if request.method == "POST":
        data_devolucao_real = request.form.get("data_devolucao_real")
        
        with engine.begin() as conn:
            from datetime import datetime
            data_devolucao_real_obj = datetime.strptime(data_devolucao_real, '%Y-%m-%d')
            data_prevista_obj = datetime.strptime(str(emprestimo.Data_devolucao_prevista), '%Y-%m-%d')
            
            result = conn.execute(text("SELECT @ultima_multa_aplicada as mensagem")).fetchone()
            mensagem_multa = result.mensagem if result and result.mensagem else ""
            
            conn.execute(
                text("""
                    UPDATE Emprestimos 
                    SET Data_devolucao_real = :data_devolucao_real, 
                        Status_emprestimo = 'devolvido'
                    WHERE ID_emprestimo = :id
                """),
                {
                    "data_devolucao_real": data_devolucao_real,
                    "id": id
                }
            )

        flash(f"Devolução realizada com sucesso! {mensagem_multa}", 
              "warning" if mensagem_multa else "success")
        return redirect(url_for("listar_emprestimos"))

    return render_template("emprestimos/devolver_emprestimo.html", emprestimo=emprestimo)

# Excluir Empréstimo
@app.route("/emprestimos/excluir/<int:id>")
def excluir_emprestimo(id):
    with engine.begin() as conn:
        emprestimo = conn.execute(
            text("SELECT * FROM Emprestimos WHERE ID_emprestimo = :id"),
            {"id": id}
        ).fetchone()
        
        if emprestimo and emprestimo.Status_emprestimo == 'pendente':
            conn.execute(
                text("UPDATE Livros SET Quantidade_disponivel = Quantidade_disponivel + 1 WHERE ID_livro = :id"),
                {"id": emprestimo.Livro_id}
            )
        
        conn.execute(
            text("DELETE FROM Emprestimos WHERE ID_emprestimo = :id"),
            {"id": id}
        )
    
    flash("Empréstimo excluído com sucesso!", "success")
    return redirect(url_for("listar_emprestimos"))

# Listar Empréstimos Atrasados
@app.route("/emprestimos/atrasados")
def listar_emprestimos_atrasados():
    atualizar_status_emprestimos()
    
    with engine.connect() as conn:
        emprestimos_atrasados = conn.execute(text("""
            SELECT e.*, u.nome_usuario, l.Titulo,
                   DATEDIFF(CURDATE(), e.Data_devolucao_prevista) as dias_atraso
            FROM Emprestimos e
            LEFT JOIN usuarios u ON e.Usuario_id = u.id_usuario
            LEFT JOIN Livros l ON e.Livro_id = l.ID_livro
            WHERE e.Status_emprestimo = 'atrasado'
            ORDER BY e.Data_devolucao_prevista ASC
        """)).fetchall()
    
    print(f"Empréstimos atrasados encontrados: {len(emprestimos_atrasados)}")
    return render_template("emprestimos/listar_atrasados.html", emprestimos=emprestimos_atrasados)

# Auditoria
@app.route('/auditoria')
def auditoria():
    with engine.connect() as conn:
        logs = conn.execute(text("""
            SELECT * FROM logs_auditoria 
            ORDER BY data_hora DESC 
            LIMIT 100
        """)).fetchall()
    return render_template('auditoria/listar_logs.html', logs=logs)

@app.route('/auditoria/filtrar', methods=['POST'])
def filtrar_auditoria():
    data_inicio = request.form.get('data_inicio')
    data_fim = request.form.get('data_fim')
    operacao = request.form.get('operacao') or None
    
    with engine.connect() as conn:
        logs = conn.execute(text("CALL relatorio_auditoria(:inicio, :fim, :operacao)"), {
            "inicio": data_inicio,
            "fim": data_fim,
            "operacao": operacao
        }).fetchall()
    
    return render_template('auditoria/listar_logs.html', logs=logs)

# Estatísticas
@app.route('/estatisticas')
def estatisticas():
    if 'usuario_id' not in session:
        flash('Faça login para ver suas estatísticas.', 'warning')
        return redirect(url_for('login'))
    
    with engine.connect() as conn:
        multa_result = conn.execute(text("""
            SELECT multa_atual FROM Usuarios WHERE id_usuario = :id
        """), {"id": session['usuario_id']}).fetchone()
        
        multa_atual = multa_result.multa_atual if multa_result else 0
        
        total_emprestimos = conn.execute(text("""
            SELECT COUNT(*) FROM Emprestimos 
            WHERE Usuario_id = :id
        """), {"id": session['usuario_id']}).fetchone()[0] or 0
        
        atrasos = conn.execute(text("""
            SELECT COUNT(*) FROM Emprestimos 
            WHERE Usuario_id = :id 
            AND Status_emprestimo = 'atrasado'
        """), {"id": session['usuario_id']}).fetchone()[0] or 0
        
        historico = conn.execute(text("""
            SELECT e.*, l.Titulo,
                   CASE 
                     WHEN e.Data_devolucao_real IS NOT NULL 
                     THEN DATEDIFF(e.Data_devolucao_real, e.Data_devolucao_prevista)
                     ELSE DATEDIFF(CURDATE(), e.Data_devolucao_prevista)
                   END as dias_atraso,
                   CASE 
                     WHEN e.Data_devolucao_real IS NOT NULL 
                     THEN DATEDIFF(e.Data_devolucao_real, e.Data_devolucao_prevista) * 2.00
                     ELSE DATEDIFF(CURDATE(), e.Data_devolucao_prevista) * 2.00
                   END as multa_calculada
            FROM Emprestimos e
            JOIN Livros l ON e.Livro_id = l.ID_livro
            WHERE e.Usuario_id = :id
            ORDER BY e.Data_emprestimo DESC
            LIMIT 10
        """), {"id": session['usuario_id']}).fetchall()
        
        emprestimos_atrasados = conn.execute(text("""
            SELECT e.*, l.Titulo,
                   DATEDIFF(CURDATE(), e.Data_devolucao_prevista) as dias_atraso,
                   DATEDIFF(CURDATE(), e.Data_devolucao_prevista) * 2.00 as multa_devida
            FROM Emprestimos e
            JOIN Livros l ON e.Livro_id = l.ID_livro
            WHERE e.Usuario_id = :id 
            AND e.Status_emprestimo = 'atrasado'
            AND CURDATE() > e.Data_devolucao_prevista
        """), {"id": session['usuario_id']}).fetchall()
        
        multa_pendente = 0
        for emp in emprestimos_atrasados:
            if hasattr(emp, 'multa_devida'):
                multa_pendente += emp.multa_devida
        
        estatisticas = {
            'total_emprestimos': total_emprestimos,
            'atrasos': atrasos,
            'multa_atual': multa_atual,
            'multa_pendente': multa_pendente,
            'multa_total': multa_atual + multa_pendente,
            'media_atrasos': round((atrasos * 100.0) / total_emprestimos, 2) if total_emprestimos > 0 else 0
        }
    
    return render_template('usuarios/estatisticas.html', estatisticas=estatisticas, historico=historico,

                         emprestimos_atrasados=emprestimos_atrasados, multa_atual=multa_atual)
