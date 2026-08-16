import math
from typing import Dict, List
import numpy as np


# ============================================================
# UTILIDADES
# ============================================================

def media(lista, padrao=0.0):
    valores = [
        float(x)
        for x in lista
        if x is not None
    ]

    return (
        sum(valores) / len(valores)
        if valores else padrao
    )


def limitar(valor, minimo=0.0, maximo=1.0):
    return max(minimo, min(maximo, valor))


# ============================================================
# FORMA
# ============================================================

def calcular_forma(
    partidas: List[Dict],
    num_jogos: int = 5
) -> float:

    if not partidas:
        return 0.5

    ultimas = partidas[-num_jogos:]

    pontos = 0
    max_pontos = len(ultimas) * 3

    for jogo in ultimas:

        gm = jogo.get(
            "golos_marcados",
            0
        )

        gs = jogo.get(
            "golos_sofridos",
            0
        )

        if gm > gs:
            pontos += 3

        elif gm == gs:
            pontos += 1

    if max_pontos == 0:
        return 0.5

    return pontos / max_pontos


# ============================================================
# GOLOS
# ============================================================

def media_golos(
    marcados,
    sofridos
):

    return (
        media(marcados, 1.2),
        media(sofridos, 1.2)
    )


def calcular_xg(
    gm_casa,
    gs_casa,
    gm_fora,
    gs_fora,
    forma_casa,
    forma_fora,
    pos_casa=None,
    pos_fora=None
):

    ataque_casa = (
        gm_casa * 0.60 +
        gs_fora * 0.40
    )

    ataque_fora = (
        gm_fora * 0.60 +
        gs_casa * 0.40
    )

    # Pequeno ajuste de forma
    ataque_casa *= (
        0.90 + forma_casa * 0.20
    )

    ataque_fora *= (
        0.90 + forma_fora * 0.20
    )

    # Vantagem de jogar em casa
    ataque_casa *= 1.05

    # Classificação
    if pos_casa and pos_fora:

        diferenca = pos_fora - pos_casa

        ajuste = limitar(
            diferenca * 0.012,
            -0.10,
            0.10
        )

        ataque_casa *= (
            1 + max(0, ajuste)
        )

        ataque_fora *= (
            1 + max(0, -ajuste)
        )

    return (
        limitar(ataque_casa, 0.25, 4.0),
        limitar(ataque_fora, 0.20, 3.5)
    )


# ============================================================
# POISSON
# ============================================================

def poisson_lista(
    esperado,
    max_golos=10
):

    resultado = []

    for k in range(max_golos + 1):

        p = (
            math.exp(-esperado) *
            esperado ** k /
            math.factorial(k)
        )

        resultado.append(p)

    return resultado


def prob_over(
    xg_casa,
    xg_fora,
    linha
):

    pc = poisson_lista(xg_casa)
    pf = poisson_lista(xg_fora)

    prob = 0

    for i, p1 in enumerate(pc):

        for j, p2 in enumerate(pf):

            if i + j > linha:

                prob += p1 * p2

    return limitar(prob)


def prob_btts(
    xg_casa,
    xg_fora
):

    p_casa = 1 - poisson_lista(
        xg_casa
    )[0]

    p_fora = 1 - poisson_lista(
        xg_fora
    )[0]

    return limitar(
        p_casa * p_fora
    )


# ============================================================
# RESULTADO
# ============================================================

def avaliar_resultado(
    xg_casa,
    xg_fora
):

    pc = poisson_lista(xg_casa)
    pf = poisson_lista(xg_fora)

    casa = 0
    empate = 0
    fora = 0

    for i, p1 in enumerate(pc):

        for j, p2 in enumerate(pf):

            p = p1 * p2

            if i > j:
                casa += p

            elif i == j:
                empate += p

            else:
                fora += p

    total = casa + empate + fora

    return {
        "casa": casa / total,
        "empate": empate / total,
        "fora": fora / total
    }


# ============================================================
# ESCANTEIOS
# ============================================================

def prob_over_estatistica(
    media_total,
    linha,
    desvio
):

    if media_total <= 0:
        return 0.0

    z = (
        linha - media_total
    ) / desvio

    return limitar(
        1 - 0.5 * (
            1 + math.erf(
                z / math.sqrt(2)
            )
        )
    )


def calcular_prob_cantos(
    cantos_casa,
    cantos_fora,
    linha
):

    esperado = (
        media(cantos_casa, 4.5) +
        media(cantos_fora, 4.0)
    )

    return prob_over_estatistica(
        esperado,
        linha,
        2.8
    )


# ============================================================
# CARTÕES
# ============================================================

def calcular_prob_cartoes(
    cartoes_casa,
    cartoes_fora,
    linha
):

    esperado = (
        media(cartoes_casa, 2.0) +
        media(cartoes_fora, 2.0)
    )

    return prob_over_estatistica(
        esperado,
        linha,
        1.7
    )


# ============================================================
# PONTUAÇÃO
# ============================================================

def calcular_pontuacao(
    probabilidade,
    odd=None
):

    probabilidade = limitar(
        probabilidade
    )

    # Sem odd:
    # a probabilidade é o fator principal
    base = probabilidade * 100

    if odd and odd > 1:

        valor = (
            probabilidade * odd
        ) - 1

        # Pequeno bônus/malus de valor
        base += valor * 10

    return round(
        limitar(base, 0, 99),
        1
    )


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================

def analisar_jogo(
    dados_jogo: Dict
) -> Dict:

    home = dados_jogo.get(
        "home_team",
        "?"
    )

    away = dados_jogo.get(
        "away_team",
        "?"
    )

    # -------------------------
    # FORMA
    # -------------------------

    forma_casa = calcular_forma(
        dados_jogo.get(
            "forma_casa",
            []
        )
    )

    forma_fora = calcular_forma(
        dados_jogo.get(
            "forma_fora",
            []
        )
    )

    # -------------------------
    # GOLOS
    # -------------------------

    gm_casa, gs_casa = media_golos(
        dados_jogo.get(
            "golos_casa",
            []
        ),
        dados_jogo.get(
            "golos_sofridos_casa",
            []
        )
    )

    gm_fora, gs_fora = media_golos(
        dados_jogo.get(
            "golos_fora",
            []
        ),
        dados_jogo.get(
            "golos_sofridos_fora",
            []
        )
    )

    xg_casa, xg_fora = calcular_xg(
        gm_casa,
        gs_casa,
        gm_fora,
        gs_fora,
        forma_casa,
        forma_fora,
        dados_jogo.get(
            "posicao_casa"
        ),
        dados_jogo.get(
            "posicao_fora"
        )
    )

    # -------------------------
    # PROBABILIDADES
    # -------------------------

    resultado = avaliar_resultado(
        xg_casa,
        xg_fora
    )

    over15 = prob_over(
        xg_casa,
        xg_fora,
        1.5
    )

    over25 = prob_over(
        xg_casa,
        xg_fora,
        2.5
    )

    btts = prob_btts(
        xg_casa,
        xg_fora
    )

    # -------------------------
    # ESCANTEIOS
    # -------------------------

    cantos_casa = dados_jogo.get(
        "cantos_casa",
        []
    )

    cantos_fora = dados_jogo.get(
        "cantos_fora",
        []
    )

    over75_cantos = calcular_prob_cantos(
        cantos_casa,
        cantos_fora,
        7.5
    )

    over85_cantos = calcular_prob_cantos(
        cantos_casa,
        cantos_fora,
        8.5
    )

    # -------------------------
    # CARTÕES
    # -------------------------

    cartoes_casa = dados_jogo.get(
        "cartoes_casa",
        []
    )

    cartoes_fora = dados_jogo.get(
        "cartoes_fora",
        []
    )

    over25_cartoes = calcular_prob_cartoes(
        cartoes_casa,
        cartoes_fora,
        2.5
    )

    over35_cartoes = calcular_prob_cartoes(
        cartoes_casa,
        cartoes_fora,
        3.5
    )

    odds = dados_jogo.get(
        "odds",
        {}
    )

    previsoes = []

    def add(
        mercado,
        selecao,
        prob,
        odd=None
    ):

        previsoes.append({
            "mercado": mercado,
            "selecao": selecao,
            "probabilidade": round(
                prob,
                3
            ),
            "odd": odd,
            "pontuacao": calcular_pontuacao(
                prob,
                odd
            )
        })

    # -------------------------
    # RESULTADO
    # -------------------------

    melhor = max(
        resultado,
        key=resultado.get
    )

    odd = (
        odds.get(
            "1x2",
            {}
        ).get(
            melhor
        )
    )

    nomes = {
        "casa": "Casa",
        "empate": "Empate",
        "fora": "Fora"
    }

    add(
        "Resultado Final",
        nomes[melhor],
        resultado[melhor],
        odd
    )

    # -------------------------
    # DUPLA HIPÓTESE
    # -------------------------

    casa_empate = (
        resultado["casa"] +
        resultado["empate"]
    )

    fora_empate = (
        resultado["fora"] +
        resultado["empate"]
    )

    if casa_empate >= fora_empate:

        add(
            "Dupla Hipótese",
            "Casa ou Empate",
            casa_empate
        )

    else:

        add(
            "Dupla Hipótese",
            "Fora ou Empate",
            fora_empate
        )

    # -------------------------
    # GOLOS
    # -------------------------

    add(
        "Over 1.5 Gols",
        "Sim",
        over15,
        odds.get("over_1_5")
    )

    add(
        "Over 2.5 Gols",
        "Sim",
        over25,
        odds.get("over_2_5")
    )

    add(
        "BTTS",
        "Sim",
        btts,
        odds.get("btts")
    )

    # -------------------------
    # ESCANTEIOS
    # -------------------------

    add(
        "Over 7.5 Escanteios",
        "Sim",
        over75_cantos
    )

    add(
        "Over 8.5 Escanteios",
        "Sim",
        over85_cantos
    )

    # -------------------------
    # CARTÕES
    # -------------------------

    add(
        "Over 2.5 Cartões",
        "Sim",
        over25_cartoes
    )

    add(
        "Over 3.5 Cartões",
        "Sim",
        over35_cartoes
    )

    # -------------------------
    # ORDENAR
    # -------------------------

    previsoes.sort(
        key=lambda x: x["pontuacao"],
        reverse=True
    )

    confianca = round(
        np.mean([
            x["pontuacao"]
            for x in previsoes[:3]
        ]),
        1
    )

    return {
        "event_id": dados_jogo.get(
            "event_id"
        ),
        "home_team": home,
        "away_team": away,
        "xg_casa": round(
            xg_casa,
            2
        ),
        "xg_fora": round(
            xg_fora,
            2
        ),
        "forma_casa": round(
            forma_casa * 100,
            1
        ),
        "forma_fora": round(
            forma_fora * 100,
            1
        ),
        "previsoes": previsoes,
        "confianca_geral": confianca
    }
