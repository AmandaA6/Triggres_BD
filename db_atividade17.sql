CREATE DATABASE db_atividade17;
USE db_atividade17 ;

CREATE TABLE Autores (
    ID_autor INT AUTO_INCREMENT PRIMARY KEY,
    Nome_autor VARCHAR(255) NOT NULL,
    Nacionalidade VARCHAR(255),
    Data_nascimento DATE,
    Biografia TEXT
);

CREATE TABLE Generos (
    id_genero INT AUTO_INCREMENT PRIMARY KEY,
    nome_genero VARCHAR(255) NOT NULL
);

CREATE TABLE Editoras (
    ID_editora INT AUTO_INCREMENT PRIMARY KEY,
    Nome_editora VARCHAR(255) NOT NULL,
    Endereco_editora TEXT
);

CREATE TABLE Livros (
    ID_livro INT AUTO_INCREMENT PRIMARY KEY,
    Titulo VARCHAR(255) NOT NULL,
    Autor_id INT,
    ISBN VARCHAR(13) NOT NULL,
    Ano_publicacao INT,
    Genero_id INT,
    Editora_id INT,
    Quantidade_disponivel INT,
    Resumo TEXT,
    FOREIGN KEY (Autor_id) REFERENCES Autores(ID_autor),
    FOREIGN KEY (Genero_id) REFERENCES Generos(ID_genero),
    FOREIGN KEY (Editora_id) REFERENCES Editoras(ID_editora)
);

CREATE TABLE Usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nome_usuario VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    numero_telefone VARCHAR(20),
    data_inscricao DATE,
    multa_atual DECIMAL(10, 2),
    senha VARCHAR(255) NOT NULL
);

CREATE TABLE Emprestimos (
    ID_emprestimo INT AUTO_INCREMENT PRIMARY KEY,
    Usuario_id INT,
    Livro_id INT,
    Data_emprestimo DATE,
    Data_devolucao_prevista DATE,
    Data_devolucao_real DATE,
    Status_emprestimo ENUM('pendente', 'devolvido', 'atrasado'),
    FOREIGN KEY (Usuario_id) REFERENCES Usuarios(id_usuario),
    FOREIGN KEY (Livro_id) REFERENCES Livros(ID_livro)
);

CREATE TABLE IF NOT EXISTS logs_auditoria (
    id_log INT AUTO_INCREMENT PRIMARY KEY,
    tabela_afetada VARCHAR(50),
    operacao VARCHAR(20),
    id_registro INT,
    dados_antigos JSON,
    dados_novos JSON,
    usuario_executor VARCHAR(100),
    data_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1. GATILHOS DE VALIDAÇÃO (BEFORE INSERT/UPDATE)

-- 1.1. Validar email único ao cadastrar usuário
DELIMITER $$
CREATE TRIGGER valida_email_unico
BEFORE INSERT ON usuarios
FOR EACH ROW
BEGIN
    IF EXISTS (SELECT 1 FROM usuarios WHERE email = NEW.email) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Email já cadastrado no sistema.';
    END IF;
END$$
DELIMITER ;

-- 1.2. Validar telefone com formato brasileiro (DDD + número)
DELIMITER $$
CREATE TRIGGER valida_formato_telefone
BEFORE INSERT ON usuarios
FOR EACH ROW
BEGIN
    IF NEW.numero_telefone IS NOT NULL THEN
        IF NEW.numero_telefone NOT REGEXP '^\\([1-9]{2}\\)\\s*9?\\s*[0-9]{4}-[0-9]{4}$' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Formato de telefone inválido. Use: (XX) 9XXXX-XXXX ou (XX) XXXX-XXXX';
        END IF;
    END IF;
END$$
DELIMITER ;

-- 1.3. Validar que multa não pode ser negativa
DELIMITER $$
CREATE TRIGGER valida_multa_positiva
BEFORE INSERT ON usuarios
FOR EACH ROW
BEGIN
    IF NEW.multa_atual < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Valor de multa não pode ser negativo.';
    END IF;
END$$
DELIMITER ;

-- 1.4. Validar que quantidade disponível não pode ser negativa
DELIMITER $$
CREATE TRIGGER valida_quantidade_livro
BEFORE INSERT ON Livros
FOR EACH ROW
BEGIN
    IF NEW.Quantidade_disponivel < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Quantidade de livros não pode ser negativa.';
    END IF;
END$$
DELIMITER ;

-- 1.5. Validar que data de devolução não pode ser anterior ao empréstimo
DELIMITER $$
CREATE TRIGGER valida_data_devolucao
BEFORE INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    IF NEW.Data_devolucao_prevista < NEW.Data_emprestimo THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Data de devolução não pode ser anterior à data de empréstimo.';
    END IF;
END$$
DELIMITER ;

-- 2. GATILHOS DE AUDITORIA (AFTER INSERT/UPDATE/DELETE)

-- 2.1. Registrar cadastro de novos usuários
DELIMITER $$
CREATE TRIGGER log_insert_usuarios
AFTER INSERT ON usuarios
FOR EACH ROW
BEGIN
    INSERT INTO logs_auditoria (
        tabela_afetada,
        operacao,
        id_registro,
        dados_antigos,
        dados_novos,
        usuario_executor
    )
    VALUES (
        'usuarios',
        'INSERT',
        NEW.id_usuario,
        NULL,
        JSON_OBJECT(
            'nome', NEW.nome_usuario,
            'email', NEW.email,
            'telefone', NEW.numero_telefone,
            'data_inscricao', NEW.data_inscricao
        ),
        USER()
    );
END$$
DELIMITER;  

-- 2.2. Registrar atualização na tabela de empréstimo
DELIMITER $$
CREATE TRIGGER log_update_emprestimos
AFTER UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    INSERT INTO logs_auditoria (
        tabela_afetada,
        operacao,
        id_registro,
        dados_antigos,
        dados_novos,
        usuario_executor
    )
    VALUES (
        'Emprestimos',
        'UPDATE',
        OLD.ID_emprestimo,
        JSON_OBJECT(
            'status', OLD.Status_emprestimo,
            'data_devolucao_real', OLD.Data_devolucao_real
        ),
        JSON_OBJECT(
            'status', NEW.Status_emprestimo,
            'data_devolucao_real', NEW.Data_devolucao_real
        ),
        USER()
    );
END$$
DELIMITER;

-- 2.3. Registrar exclusão de livros
DELIMITER $$

CREATE TRIGGER log_delete_livros
AFTER DELETE ON Livros
FOR EACH ROW
BEGIN
    INSERT INTO logs_auditoria (
        tabela_afetada,
        operacao,
        id_registro,
        dados_antigos,
        dados_novos,
        usuario_executor
    )
    VALUES (
        'Livros',
        'DELETE',
        OLD.ID_livro,
        JSON_OBJECT(
            'titulo', OLD.Titulo,
            'isbn', OLD.ISBN,
            'ano_publicacao', OLD.Ano_publicacao
        ),
        NULL,
        USER()
    );
END$$
DELIMITER;

-- 3. GATILHOS ATUALIZAÇÃO AUTOMÁTICA PÓS-EVENTO (INSERT/UPDATE/DELETE)

-- 3.1. Diminuir quantidade de livros após empréstimo
DELIMITER $$
CREATE TRIGGER diminuir_livro_emprestimo
AFTER INSERT ON Emprestimos
FOR EACH ROW
BEGIN
	UPDATE Livros
    SET Quantidade_disponivel = Quantidade_disponivel - 1
    WHERE ID_livro = NEW.Livro_id;
END$$

DELIMITER ;

-- 3.2. Aumentar quantidade do livro na devolução
DELIMITER $$
CREATE TRIGGER aumentar_livro_devolucao
AFTER UPDATE ON Emprestimos
FOR EACH ROW
BEGIN	
	IF OLD.Status_emprestimo <> 'devolvido'
		AND NEW.Status_emprestimo = 'devolvido' THEN
        
        UPDATE Livros
        SET Quantidade_disponivel = Quantidade_disponivel + 1
		WHERE ID_livro = NEW.Livro_id;
	END IF;
END$$

DELIMITER ;

-- 3.3. Marcar empréstimo como atrasado automaticamente
DELIMITER $$
CREATE TRIGGER marcar_atraso
BEFORE UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    IF NEW.Data_devolucao_real IS NULL
       AND CURDATE() > NEW.Data_devolucao_prevista THEN
        SET NEW.Status_emprestimo = 'atrasado';
    END IF;
END$$

DELIMITER ;

-- 3.4. Atualizar multa do usuário automaticamente
DELIMITER $$
CREATE TRIGGER atualizar_multa
AFTER UPDATE ON Emprestimos
FOR EACH ROW
BEGIN
    DECLARE dias_atraso INT;
    DECLARE valor_multa DECIMAL(10,2);

    IF NEW.Data_devolucao_real IS NOT NULL
       AND NEW.Data_devolucao_real > NEW.Data_devolucao_prevista THEN

        SET dias_atraso = DATEDIFF(
            NEW.Data_devolucao_real,
            NEW.Data_devolucao_prevista
        );
        
        SET valor_multa = dias_atraso * 0.2;
 
        UPDATE Usuarios
        SET multa_atual = IFNULL(multa_atual, 0) + valor_multa
        WHERE id_usuario = NEW.Usuario_id;
    END IF;
END$$

DELIMITER ;

-- 3.5. Devolver livro ao excluir empréstimo pendente
DELIMITER $$
CREATE TRIGGER deletar_emprestimo_pendente
AFTER DELETE ON Emprestimos
FOR EACH ROW
BEGIN
    IF OLD.Status_emprestimo = 'pendente' THEN
        UPDATE Livros
        SET Quantidade_disponivel = Quantidade_disponivel + 1
        WHERE ID_livro = OLD.Livro_id;
    END IF;
END$$

DELIMITER ;

-- 4. Geração Automática de Valores

-- 4.1. Preencher data de cadastro do usuário automaticamente
DELIMITER $$

CREATE TRIGGER data_cadastro_usuario
BEFORE INSERT ON Usuarios
FOR EACH ROW
BEGIN
    IF NEW.data_inscricao IS NULL THEN
        SET NEW.data_inscricao = CURDATE();
    END IF;
END$$

DELIMITER ;

-- 4.2. Definir multa inicial padrão (0.00)
DELIMITER $$

CREATE TRIGGER multa_padrao
BEFORE INSERT ON Usuarios
FOR EACH ROW
BEGIN
    IF NEW.multa_atual IS NULL THEN
        SET NEW.multa_atual = 0.00;
    END IF;
END$$

DELIMITER ;

-- 4.3. Preencher data do empréstimo automaticamente
DELIMITER $$

CREATE TRIGGER data_emprestimo
BEFORE INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    IF NEW.Data_emprestimo IS NULL THEN
        SET NEW.Data_emprestimo = CURDATE();
    END IF;
END$$

DELIMITER ;

--  4.4. Gerar data de devolução prevista automaticamente
DELIMITER $$

CREATE TRIGGER data_devolucao_prevista
BEFORE INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    IF NEW.Data_devolucao_prevista IS NULL THEN
        SET NEW.Data_devolucao_prevista = DATE_ADD(CURDATE(), INTERVAL 7 DAY);
    END IF;
END$$

DELIMITER ;

-- 4.5. Gerar status automático do empréstimo
DELIMITER $$

CREATE TRIGGER status_emprestimo
BEFORE INSERT ON Emprestimos
FOR EACH ROW
BEGIN
    IF NEW.Status_emprestimo IS NULL THEN
        SET NEW.Status_emprestimo = 'pendente';
    END IF;
END$$

DELIMITER ;
