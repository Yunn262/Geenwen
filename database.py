import sqlite3
import json

DB_NAME = "footballai.db"


# ============================================================
# CONEXÃO
# ============================================================

def conectar():

    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )

    return conn


# ============================================================
# INICIALIZAR
# ============================================================

def init_db():

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS previsoes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            data_jogo TEXT,

            jogo TEXT,

            mercado TEXT,

            selecao TEXT,

            probabilidade REAL,

            odd REAL,

            pontuacao REAL,

            confianca_jogo REAL,

            criado_em TEXT
            DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bilhetes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            data_bilhete TEXT,

            selecoes TEXT,

            odd_total REAL,

            confianca_media REAL,

            status TEXT
            DEFAULT 'pendente',

            tipo TEXT
            DEFAULT 'normal',

            criado_em TEXT
            DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    conn.close()


# ============================================================
# SALVAR PREVISÃO
# ============================================================

def salvar_previsao(
    data_jogo,
    jogo,
    mercado,
    selecao,
    probabilidade,
    odd,
    pontuacao,
    confianca_jogo
):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO previsoes
        (
            data_jogo,
            jogo,
            mercado,
            selecao,
            probabilidade,
            odd,
            pontuacao,
            confianca_jogo
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data_jogo,
        jogo,
        mercado,
        selecao,
        probabilidade,
        odd,
        pontuacao,
        confianca_jogo
    ))

    conn.commit()

    conn.close()


# ============================================================
# VERIFICAR BILHETE DUPLICADO
# ============================================================

def bilhete_ja_existe(
    data_bilhete,
    tipo
):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT id

        FROM bilhetes

        WHERE data_bilhete = ?
        AND tipo = ?

        LIMIT 1
    """, (
        data_bilhete,
        tipo
    ))

    resultado = cursor.fetchone()

    conn.close()

    return resultado is not None


# ============================================================
# SALVAR BILHETE
# ============================================================

def salvar_bilhete(
    data_bilhete,
    selecoes,
    odd_total,
    confianca_media,
    status="pendente",
    tipo="normal"
):

    # Evita duplicar infinitamente
    # por causa do autorefresh do Streamlit.

    if bilhete_ja_existe(
        data_bilhete,
        tipo
    ):

        return

    conn = conectar()

    cursor = conn.cursor()

    selecoes_json = json.dumps(
        selecoes,
        ensure_ascii=False
    )

    cursor.execute("""
        INSERT INTO bilhetes
        (
            data_bilhete,
            selecoes,
            odd_total,
            confianca_media,
            status,
            tipo
        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data_bilhete,
        selecoes_json,
        odd_total,
        confianca_media,
        status,
        tipo
    ))

    conn.commit()

    conn.close()


# ============================================================
# LISTAR PREVISÕES
# ============================================================

def listar_previsoes(
    limit=100
):

    conn = conectar()

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *

        FROM previsoes

        ORDER BY criado_em DESC

        LIMIT ?
    """, (
        limit,
    ))

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# LISTAR BILHETES
# ============================================================

def listar_bilhetes(
    limit=50
):

    conn = conectar()

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT *

        FROM bilhetes

        ORDER BY criado_em DESC

        LIMIT ?
    """, (
        limit,
    ))

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# ATUALIZAR STATUS
# ============================================================

def atualizar_status_bilhete(
    bilhete_id,
    novo_status
):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bilhetes

        SET status = ?

        WHERE id = ?
    """, (
        novo_status,
        bilhete_id
    ))

    conn.commit()

    conn.close()


# ============================================================
# INICIAR BANCO
# ============================================================

init_db()
