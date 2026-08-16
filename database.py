import sqlite3
import json

DB_NAME = "footballai.db"


def get_connection():

    conn = sqlite3.connect(
        DB_NAME
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_connection()
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
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bilhetes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_bilhete TEXT,
            selecoes TEXT,
            odd_total REAL,
            confianca_media REAL,
            status TEXT DEFAULT 'pendente',
            tipo TEXT DEFAULT 'normal',
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


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

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO previsoes (
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


def salvar_bilhete(
    data_bilhete,
    selecoes,
    odd_total,
    confianca_media,
    status="pendente",
    tipo="normal"
):

    conn = get_connection()
    cursor = conn.cursor()

    selecoes_json = json.dumps(
        selecoes,
        ensure_ascii=False,
        sort_keys=True
    )

    # Evita duplicar o mesmo bilhete
    cursor.execute("""
        SELECT id
        FROM bilhetes
        WHERE data_bilhete = ?
          AND tipo = ?
          AND selecoes = ?
        LIMIT 1
    """, (
        data_bilhete,
        tipo,
        selecoes_json
    ))

    existe = cursor.fetchone()

    if not existe:

        cursor.execute("""
            INSERT INTO bilhetes (
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


def listar_previsoes(
    limit=50
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM previsoes
        ORDER BY criado_em DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def listar_bilhetes(
    limit=20
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM bilhetes
        ORDER BY criado_em DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()

    return [
        dict(row)
        for row in rows
    ]


def atualizar_status_bilhete(
    bilhete_id,
    novo_status
):

    conn = get_connection()

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


init_db()
