from typing import List, Dict, Optional


# ============================================================
# BILHETE DO DIA
# ============================================================

def gerar_bilhete(
    resultados: List[Dict],
    minimo_jogos: int = 10,
    max_selecoes: int = 20
) -> Optional[Dict]:

    candidatos = []

    # ========================================================
    # ESCOLHER APENAS O MELHOR PALPITE DE CADA JOGO
    # ========================================================

    for jogo in resultados:

        previsoes = jogo.get(
            "previsoes",
            []
        )

        if not previsoes:
            continue

        # Melhor previsão do jogo
        melhor = max(
            previsoes,
            key=lambda p: p.get(
                "pontuacao",
                0
            )
        )

        if melhor.get(
            "pontuacao",
            0
        ) <= 0:
            continue

        candidatos.append({

            "jogo":
                f"{jogo['home_team']} vs "
                f"{jogo['away_team']}",

            "event_id":
                jogo.get(
                    "event_id"
                ),

            "mercado":
                melhor["mercado"],

            "selecao":
                melhor["selecao"],

            "probabilidade":
                melhor["probabilidade"],

            "odd":
                melhor.get("odd"),

            "pontuacao":
                melhor["pontuacao"],

            "confianca_jogo":
                jogo.get(
                    "confianca_geral",
                    0
                )
        })

    # ========================================================
    # PRECISA DE PELO MENOS 10 JOGOS
    # ========================================================

    if len(candidatos) < minimo_jogos:

        return None

    # ========================================================
    # ORDENAR
    # ========================================================

    candidatos.sort(
        key=lambda x: (
            x["pontuacao"],
            x["probabilidade"]
        ),
        reverse=True
    )

    # ========================================================
    # PEGAR PELO MENOS 10
    # ========================================================

    selecionadas = candidatos[
        :max(
            minimo_jogos,
            min(
                max_selecoes,
                len(candidatos)
            )
        )
    ]

    # ========================================================
    # ODDS
    # ========================================================

    odd_total = 1.0
    tem_odds = True

    for sel in selecionadas:

        odd = sel.get("odd")

        if odd is None:

            tem_odds = False
            break

        try:

            odd_total *= float(
                odd
            )

        except:

            tem_odds = False
            break

    # ========================================================
    # CONFIANÇA
    # ========================================================

    confianca = (
        sum(
            s["pontuacao"]
            for s in selecionadas
        )
        /
        len(selecionadas)
    )

    return {

        "selecoes":
            selecionadas,

        "num_selecoes":
            len(selecionadas),

        "num_jogos":
            len(
                set(
                    s["jogo"]
                    for s in selecionadas
                )
            ),

        "odd_total":
            round(
                odd_total,
                2
            )
            if tem_odds
            else None,

        "confianca_media":
            round(
                confianca,
                1
            )
    }


# ============================================================
# MONTAGENS INTELIGENTES
# ============================================================

def gerar_montagens_inteligentes(
    resultados: List[Dict]
) -> List[Dict]:

    configs = [

        {
            "nome": "🔥 10 Mais Seguros",
            "min_conf": 75,
            "min_sel": 10,
            "max_sel": 10
        },

        {
            "nome": "🛡️ 12 Seguros",
            "min_conf": 70,
            "min_sel": 10,
            "max_sel": 12
        },

        {
            "nome": "⚖️ 15 Moderados",
            "min_conf": 60,
            "min_sel": 10,
            "max_sel": 15
        },

        {
            "nome": "🚀 20 Agressivos",
            "min_conf": 50,
            "min_sel": 10,
            "max_sel": 20
        }
    ]

    montagens = []

    for cfg in configs:

        candidatos = []

        # ----------------------------------------------------
        # UM PALPITE POR JOGO
        # ----------------------------------------------------

        for jogo in resultados:

            previsoes = jogo.get(
                "previsoes",
                []
            )

            validas = [
                p for p in previsoes
                if p.get(
                    "pontuacao",
                    0
                ) >= cfg["min_conf"]
            ]

            if not validas:
                continue

            melhor = max(
                validas,
                key=lambda p:
                    p.get(
                        "pontuacao",
                        0
                    )
            )

            candidatos.append({

                "jogo":
                    f"{jogo['home_team']} vs "
                    f"{jogo['away_team']}",

                "event_id":
                    jogo.get(
                        "event_id"
                    ),

                "mercado":
                    melhor["mercado"],

                "selecao":
                    melhor["selecao"],

                "probabilidade":
                    melhor["probabilidade"],

                "odd":
                    melhor.get("odd"),

                "pontuacao":
                    melhor["pontuacao"],

                "confianca_jogo":
                    jogo.get(
                        "confianca_geral",
                        0
                    )
            })

        # ----------------------------------------------------
        # MÍNIMO DE 10 JOGOS
        # ----------------------------------------------------

        if len(candidatos) < cfg["min_sel"]:
            continue

        candidatos.sort(
            key=lambda x:
                x["pontuacao"],
            reverse=True
        )

        selecionadas = candidatos[
            :cfg["max_sel"]
        ]

        # ----------------------------------------------------
        # ODDS
        # ----------------------------------------------------

        odd_total = 1.0
        tem_odds = True

        for sel in selecionadas:

            if sel.get("odd") is None:

                tem_odds = False
                break

            try:

                odd_total *= float(
                    sel["odd"]
                )

            except:

                tem_odds = False
                break

        confianca = (
            sum(
                s["pontuacao"]
                for s in selecionadas
            )
            /
            len(selecionadas)
        )

        montagens.append({

            "nome":
                cfg["nome"],

            "selecoes":
                selecionadas,

            "num_selecoes":
                len(selecionadas),

            "odd_total":
                round(
                    odd_total,
                    2
                )
                if tem_odds
                else None,

            "confianca_media":
                round(
                    confianca,
                    1
                )
        })

    return montagens
