import math
from typing import Dict, List

import numpy as np


# ============================================================
# FORMA
# ============================================================

def calcular_forma(
    partidas: List[Dict],
    num_jogos: int = 5
) -> float:

    if not partidas:
        return 1.5

    ultimas = partidas[-num_jogos:]

    pontos = 0

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

    return pontos / len(ultimas)


# ============================================================
# MÉDIA DE GOLOS
# ============================================================

def media_golos(
    marcados,
    sofridos
):

    media_marcados = (
        sum(marcados) /
        len(marcados)
        if marcados
        else 1.2
    )

    media_sofridos = (
        sum(sofridos) /
        len(sofridos)
        if sofridos
        else 1.2
    )

    return (
        media_marcados,
        media_sofridos
    )


# ============================================================
# xG
# ============================================================

def calcular_expectativa_golos(
    media_marcados_casa,
    media_sofridos_fora,
    media_marcados_fora,
    media_sofridos_casa
):

    xg_casa = (
        media_marcados_casa +
        media_sofridos_fora
    ) / 2

    xg_fora = (
        media_marcados_fora +
        media_sofridos_casa
    ) / 2

    return (
        xg_casa,
        xg_fora
    )


# ============================================================
# POISSON
# ============================================================

def prob_poisson(
    golos_esperados,
    max_golos=8
):

    resultado = []

    for k in range(max_golos + 1):

        p = (
            math.exp(-golos_esperados)
            *
            golos_esperados ** k
            /
            math.factorial(k)
        )

        resultado.append(p)

    return resultado


# ============================================================
# RESULTADO FINAL
# ============================================================

def avaliar_resultado_final(
    xg_casa,
    xg_fora
):

    casa = 0
    empate = 0
    fora = 0

    pc = prob_poisson(
        xg_casa
    )

    pf = prob_poisson(
        xg_fora
    )

    for i in range(9):

        for j in range(9):

            p = pc[i] * pf[j]

            if i > j:
                casa += p

            elif i == j:
                empate += p

            else:
                fora += p

    total = casa + empate + fora

    return {

        "casa":
            round(casa / total, 3),

        "empate":
            round(empate / total, 3),

        "fora":
            round(fora / total, 3)
    }


# ============================================================
# OVER
# ============================================================

def avaliar_over_under(
    xg_casa,
    xg_fora,
    linha
):

    pc = prob_poisson(
        xg_casa
    )

    pf = prob_poisson(
        xg_fora
    )

    prob = 0

    for i in range(9):

        for j in range(9):

            if i + j > linha:

                prob += (
                    pc[i] * pf[j]
                )

    return round(
        min(max(prob, 0), 1),
        3
    )


# ============================================================
# BTTS
# ============================================================

def avaliar_btts(
    xg_casa,
    xg_fora
):

    pc = prob_poisson(
        xg_casa
    )

    pf = prob_poisson(
        xg_fora
    )

    prob = (
        (1 - pc[0])
        *
        (1 - pf[0])
    )

    return round(
        prob,
        3
    )


# ============================================================
# DISTRIBUIÇÃO NORMAL
# ============================================================

def prob_over_normal(
    media,
    linha,
    desvio
):

    if media <= 0:
        return 0

    z = (
        linha - media
    ) / desvio

    return (
        1 -
        0.5 *
        (
            1 +
            math.erf(
                z / math.sqrt(2)
            )
        )
    )


# ============================================================
# ESCANTEIOS
# ============================================================

def avaliar_cantos(
    casa,
    fora,
    linha
):

    media = casa + fora

    return round(
        min(
            max(
                prob_over_normal(
                    media,
                    linha,
                    3.0
                ),
                0
            ),
            1
        ),
        3
    )


# ============================================================
# CARTÕES
# ============================================================

def avaliar_cartoes(
    casa,
    fora,
    linha
):

    media = casa + fora

    return round(
        min(
            max(
                prob_over_normal(
                    media,
                    linha,
                    1.8
                ),
                0
            ),
            1
        ),
        3
    )


# ============================================================
# ANÁLISE
# ============================================================

def analisar_jogo(
    dados_jogo: Dict
):

    home = dados_jogo.get(
        "home_team",
        "?"
    )

    away = dados_jogo.get(
        "away_team",
        "?"
    )

    # --------------------------------------------------------
    # FORMA
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # GOLOS
    # --------------------------------------------------------

    media_casa, sofridos_casa = media_golos(
        dados_jogo.get(
            "golos_casa",
            []
        ),
        dados_jogo.get(
            "golos_sofridos_casa",
            []
        )
    )

    media_fora, sofridos_fora = media_golos(
        dados_jogo.get(
            "golos_fora",
            []
        ),
        dados_jogo.get(
            "golos_sofridos_fora",
            []
        )
    )

    # --------------------------------------------------------
    # CLASSIFICAÇÃO
    # --------------------------------------------------------

    try:

        pos_casa = int(
            dados_jogo.get(
                "posicao_casa"
            )
            or 10
        )

    except:

        pos_casa = 10

    try:

        pos_fora = int(
            dados_jogo.get(
                "posicao_fora"
            )
            or 10
        )

    except:

        pos_fora = 10

    ajuste = (
        pos_fora - pos_casa
    ) * 0.04

    # --------------------------------------------------------
    # xG
    # --------------------------------------------------------

    xg_casa, xg_fora = calcular_expectativa_golos(

        media_casa +
        max(
            0,
            ajuste
        ),

        sofridos_fora,

        media_fora +
        max(
            0,
            -ajuste
        ),

        sofridos_casa
    )

    # Forma influencia moderadamente

    xg_casa *= (
        0.90 +
        forma_casa * 0.06
    )

    xg_fora *= (
        0.90 +
        forma_fora * 0.06
    )

    xg_casa = max(
        0.25,
        min(
            4.5,
            xg_casa
        )
    )

    xg_fora = max(
        0.25,
        min(
            4.5,
            xg_fora
        )
    )

    # --------------------------------------------------------
    # PROBABILIDADES
    # --------------------------------------------------------

    resultado = avaliar_resultado_final(
        xg_casa,
        xg_fora
    )

    over15 = avaliar_over_under(
        xg_casa,
        xg_fora,
        1.5
    )

    over25 = avaliar_over_under(
        xg_casa,
        xg_fora,
        2.5
    )

    over35 = avaliar_over_under(
        xg_casa,
        xg_fora,
        3.5
    )

    btts = avaliar_btts(
        xg_casa,
        xg_fora
    )

    # --------------------------------------------------------
    # CANTOS
    # --------------------------------------------------------

    cantos_casa = dados_jogo.get(
        "media_cantos_casa",
        4.5
    )

    cantos_fora = dados_jogo.get(
        "media_cantos_fora",
        4.0
    )

    over7_cantos = avaliar_cantos(
        cantos_casa,
        cantos_fora,
        7
    )

    over8_cantos = avaliar_cantos(
        cantos_casa,
        cantos_fora,
        8
    )

    over85_cantos = avaliar_cantos(
        cantos_casa,
        cantos_fora,
        8.5
    )

    # --------------------------------------------------------
    # CARTÕES
    # --------------------------------------------------------

    cartoes_casa = dados_jogo.get(
        "media_cartoes_casa",
        2
    )

    cartoes_fora = dados_jogo.get(
        "media_cartoes_fora",
        2
    )

    over2_cartoes = avaliar_cartoes(
        cartoes_casa,
        cartoes_fora,
        2
    )

    over3_cartoes = avaliar_cartoes(
        cartoes_casa,
        cartoes_fora,
        3
    )

    over4_cartoes = avaliar_cartoes(
        cartoes_casa,
        cartoes_fora,
        4
    )

    previsoes = []

    # --------------------------------------------------------
    # ADICIONAR PREVISÃO
    # --------------------------------------------------------

    def adicionar(
        mercado,
        selecao,
        probabilidade
    ):

        probabilidade = float(
            max(
                0,
                min(
                    1,
                    probabilidade
                )
            )
        )

        # Pontuação baseada principalmente
        # na probabilidade calculada.
        pontuacao = (
            probabilidade * 100
        )

        previsoes.append({

            "mercado":
                mercado,

            "selecao":
                selecao,

            "probabilidade":
                round(
                    probabilidade,
                    3
                ),

            "odd":
                None,

            "pontuacao":
                round(
                    pontuacao,
                    1
                )
        })

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    melhor = max(
        resultado,
        key=resultado.get
    )

    nomes = {
        "casa": "Casa",
        "empate": "Empate",
        "fora": "Fora"
    }

    adicionar(
        "Resultado Final",
        nomes[melhor],
        resultado[melhor]
    )

    # --------------------------------------------------------
    # DUPLA HIPÓTESE
    # --------------------------------------------------------

    casa_empate = (
        resultado["casa"] +
        resultado["empate"]
    )

    fora_empate = (
        resultado["fora"] +
        resultado["empate"]
    )

    if casa_empate >= fora_empate:

        adicionar(
            "Dupla Hipótese",
            "Casa ou Empate",
            casa_empate
        )

    else:

        adicionar(
            "Dupla Hipótese",
            "Fora ou Empate",
            fora_empate
        )

    # --------------------------------------------------------
    # GOLOS
    # --------------------------------------------------------

    adicionar(
        "Over 1.5",
        "Sim",
        over15
    )

    adicionar(
        "Over 2.5",
        "Sim",
        over25
    )

    adicionar(
        "Over 3.5",
        "Sim",
        over35
    )

    adicionar(
        "BTTS",
        "Sim",
        btts
    )

    # --------------------------------------------------------
    # CANTOS
    # --------------------------------------------------------

    adicionar(
        "Over 7 Cantos",
        "Sim",
        over7_cantos
    )

    adicionar(
        "Over 8 Cantos",
        "Sim",
        over8_cantos
    )

    adicionar(
        "Over 8.5 Cantos",
        "Sim",
        over85_cantos
    )

    # --------------------------------------------------------
    # CARTÕES
    # --------------------------------------------------------

    adicionar(
        "Over 2 Cartões",
        "Sim",
        over2_cartoes
    )

    adicionar(
        "Over 3 Cartões",
        "Sim",
        over3_cartoes
    )

    adicionar(
        "Over 4 Cartões",
        "Sim",
        over4_cartoes
    )

    # --------------------------------------------------------
    # ORDENAR
    # --------------------------------------------------------

    previsoes.sort(
        key=lambda x: x["pontuacao"],
        reverse=True
    )

    confianca = int(
        np.mean(
            [
                p["pontuacao"]
                for p in previsoes[:3]
            ]
        )
    )

    return {

        "event_id":
            dados_jogo.get(
                "event_id"
            ),

        "home_team":
            home,

        "away_team":
            away,

        "xg_casa":
            round(
                xg_casa,
                2
            ),

        "xg_fora":
            round(
                xg_fora,
                2
            ),

        "previsoes":
            previsoes,

        "confianca_geral":
            confianca,

        "media_cantos_casa":
            cantos_casa,

        "media_cantos_fora":
            cantos_fora,

        "media_cartoes_casa":
            cartoes_casa,

        "media_cartoes_fora":
            cartoes_fora
    }
