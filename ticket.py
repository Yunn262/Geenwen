from typing import List, Dict, Optional
from itertools import combinations


MIN_JOGOS_BILHETE = 10
MAX_JOGOS_BILHETE = 15


def preparar_candidatas(
    resultados: List[Dict],
    min_pontuacao: float = 65
):

    candidatas = []

    for jogo in resultados:

        previsoes = jogo.get(
            "previsoes",
            []
        )

        if not previsoes:
            continue

        # Melhor previsão do jogo
        melhores = [
            p for p in previsoes
            if p.get(
                "pontuacao",
                0
            ) >= min_pontuacao
        ]

        if not melhores:
            continue

        melhores.sort(
            key=lambda x: (
                x.get(
                    "pontuacao",
                    0
                ),
                x.get(
                    "probabilidade",
                    0
                )
            ),
            reverse=True
        )

        p = melhores[0]

        candidatas.append({
            "jogo": (
                f"{jogo['home_team']} "
                f"vs "
                f"{jogo['away_team']}"
            ),
            "event_id": jogo.get(
                "event_id"
            ),
            "mercado": p["mercado"],
            "selecao": p["selecao"],
            "probabilidade": p["probabilidade"],
            "odd": p.get("odd"),
            "pontuacao": p["pontuacao"],
            "confianca_jogo": jogo.get(
                "confianca_geral",
                0
            )
        })

    candidatas.sort(
        key=lambda x: (
            x["pontuacao"],
            x["probabilidade"]
        ),
        reverse=True
    )

    return candidatas


def calcular_odd_total(
    selecoes
):

    if not selecoes:
        return None

    total = 1.0

    for s in selecoes:

        odd = s.get("odd")

        if not odd or odd <= 1:
            return None

        total *= float(odd)

    return round(
        total,
        2
    )


def gerar_bilhete(
    resultados: List[Dict],
    min_jogos: int = MIN_JOGOS_BILHETE,
    max_jogos: int = MAX_JOGOS_BILHETE,
    min_pontuacao: float = 65
) -> Optional[Dict]:

    candidatas = preparar_candidatas(
        resultados,
        min_pontuacao
    )

    # Uma seleção por jogo
    jogos_unicos = {}

    for c in candidatas:

        event_id = c.get(
            "event_id"
        )

        if event_id not in jogos_unicos:

            jogos_unicos[event_id] = c

    selecionadas = list(
        jogos_unicos.values()
    )

    selecionadas.sort(
        key=lambda x: x["pontuacao"],
        reverse=True
    )

    # Máximo
    selecionadas = selecionadas[
        :max_jogos
    ]

    # Regra fundamental:
    # menos de 10 = não gerar
    if len(selecionadas) < min_jogos:

        return None

    confianca_media = round(
        sum(
            x["pontuacao"]
            for x in selecionadas
        ) / len(selecionadas),
        1
    )

    return {
        "selecoes": selecionadas,
        "num_selecoes": len(
            selecionadas
        ),
        "odd_total": calcular_odd_total(
            selecionadas
        ),
        "confianca_media": confianca_media
    }


# ============================================================
# COMBINAÇÕES DENTRO DO MESMO JOGO
# ============================================================

def gerar_combinacoes_jogo(
    jogo: Dict,
    min_prob: float = 0.72
):

    previsoes = [
        p for p in jogo.get(
            "previsoes",
            []
        )
        if p.get(
            "probabilidade",
            0
        ) >= min_prob
    ]

    previsoes.sort(
        key=lambda x: x.get(
            "probabilidade",
            0
        ),
        reverse=True
    )

    combinacoes = []

    # Só combina mercados diferentes
    for a, b in combinations(
        previsoes,
        2
    ):

        # Evita combinar o mesmo mercado
        if a["mercado"] == b["mercado"]:
            continue

        pa = a["probabilidade"]
        pb = b["probabilidade"]

        # Penalização de correlação/risco.
        # Não tratamos os mercados como independentes.
        prob_combinada = (
            min(pa, pb) * 0.82
            + ((pa + pb) / 2) * 0.18
        )

        if prob_combinada < 0.60:
            continue

        combinacoes.append({
            "jogo": (
                f"{jogo['home_team']} "
                f"vs "
                f"{jogo['away_team']}"
            ),
            "event_id": jogo.get(
                "event_id"
            ),
            "mercado": (
                f"{a['mercado']} + "
                f"{b['mercado']}"
            ),
            "selecao": (
                f"{a['selecao']} + "
                f"{b['selecao']}"
            ),
            "probabilidade": round(
                prob_combinada,
                3
            ),
            "odd": None,
            "pontuacao": round(
                prob_combinada * 100,
                1
            ),
            "confianca_jogo": jogo.get(
                "confianca_geral",
                0
            )
        })

    combinacoes.sort(
        key=lambda x: x["pontuacao"],
        reverse=True
    )

    return combinacoes


# ============================================================
# MONTAGENS INTELIGENTES
# ============================================================

def gerar_montagens_inteligentes(
    resultados: List[Dict]
):

    montagens = []

    configs = [
        {
            "nome": "💚 Muito Seguro",
            "min_prob": 0.82,
            "num": 5
        },
        {
            "nome": "🟢 Seguro",
            "min_prob": 0.78,
            "num": 6
        },
        {
            "nome": "🔵 Equilibrado",
            "min_prob": 0.74,
            "num": 8
        },
        {
            "nome": "🟠 Agressivo",
            "min_prob": 0.68,
            "num": 10
        }
    ]

    for cfg in configs:

        candidatas = []

        for jogo in resultados:

            combinacoes = gerar_combinacoes_jogo(
                jogo,
                cfg["min_prob"]
            )

            if combinacoes:

                candidatas.append(
                    combinacoes[0]
                )

        candidatas.sort(
            key=lambda x: x["pontuacao"],
            reverse=True
        )

        selecionadas = candidatas[
            :cfg["num"]
        ]

        if len(selecionadas) < 2:
            continue

        confianca = round(
            sum(
                x["pontuacao"]
                for x in selecionadas
            ) / len(selecionadas),
            1
        )

        montagens.append({
            "nome": cfg["nome"],
            "selecoes": selecionadas,
            "num_selecoes": len(
                selecionadas
            ),
            "odd_total": None,
            "confianca_media": confianca
        })

    return montagens
