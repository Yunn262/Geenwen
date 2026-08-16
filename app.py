import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

from scraper import APIFootballAPI
from ai_engine import analisar_jogo
from ticket import (
    gerar_bilhete,
    gerar_montagens_inteligentes
)
import database


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="⚽ FootballAI Bot PRO",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

st_autorefresh(
    interval=300000,
    key="auto_refresh"
)


# ============================================================
# CABEÇALHO
# ============================================================

st.title("⚽ FootballAI Bot PRO")

st.caption(
    "Análise estatística de futebol • "
    "Gols • Escanteios • Cartões • "
    "Bilhetes inteligentes"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Configurações")

    hoje = datetime.now().date()

    data_selecionada = st.date_input(
        "Data dos jogos",
        value=hoje,
        min_value=hoje - timedelta(days=7),
        max_value=hoje + timedelta(days=7)
    )

    st.divider()

    st.info(
        "🎟️ Bilhete do Dia: "
        "**mínimo de 10 jogos**"
    )

    st.info(
        "🔄 Atualização automática: 5 minutos"
    )

    st.caption(
        "Os resultados são estimativas "
        "estatísticas e não garantem resultados."
    )


# ============================================================
# ANÁLISE DOS JOGOS
# ============================================================

@st.cache_data(ttl=300)
def analisar_jogos_do_dia(
    date_str
):

    api = APIFootballAPI()

    jogos = api.get_scheduled_events(
        date_str
    )

    if not jogos:
        return []

    resultados = []

    for jogo in jogos:

        try:

            dados = api.prepare_match_data(
                jogo["event_id"]
            )

            if not dados:
                continue

            analise = analisar_jogo(
                dados
            )

            analise["tournament"] = (
                jogo.get(
                    "tournament",
                    ""
                )
            )

            analise["start_time"] = (
                jogo.get(
                    "start_time",
                    ""
                )
            )

            analise["status"] = (
                jogo.get(
                    "status",
                    ""
                )
            )

            resultados.append(
                analise
            )

        except Exception as e:

            print(
                "Erro ao analisar:",
                jogo.get("home_team"),
                jogo.get("away_team"),
                e
            )

    resultados.sort(
        key=lambda x: x.get(
            "confianca_geral",
            0
        ),
        reverse=True
    )

    return resultados


date_str = data_selecionada.strftime(
    "%Y-%m-%d"
)

with st.spinner(
    "🔎 A recolher e analisar jogos..."
):

    resultados = analisar_jogos_do_dia(
        date_str
    )


# ============================================================
# ABAS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Análise",
    "🔎 Pesquisa",
    "🎟️ Bilhete do Dia",
    "💎 Montagens Inteligentes",
    "📜 Histórico"
])


# ============================================================
# ABA 1
# ============================================================

with tab1:

    st.subheader(
        f"📊 Jogos de {date_str}"
    )

    st.metric(
        "Jogos analisados",
        len(resultados)
    )

    if not resultados:

        st.warning(
            "Nenhum jogo encontrado ou "
            "não foi possível obter os dados."
        )

    else:

        # ------------------------------------
        # TABELA
        # ------------------------------------

        rows = []

        for r in resultados:

            top = r["previsoes"][:3]

            texto = " | ".join([
                (
                    f"{p['mercado']}: "
                    f"{p['selecao']} "
                    f"({p['probabilidade']:.0%})"
                )
                for p in top
            ])

            rows.append({

                "Jogo":
                    f"{r['home_team']} "
                    f"vs "
                    f"{r['away_team']}",

                "Liga":
                    r.get(
                        "tournament",
                        ""
                    ),

                "Hora":
                    r.get(
                        "start_time",
                        ""
                    ),

                "xG Casa":
                    r["xg_casa"],

                "xG Fora":
                    r["xg_fora"],

                "Confiança":
                    f"{r['confianca_geral']:.1f}%",

                "Melhores mercados":
                    texto
            })

        df = pd.DataFrame(rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # ------------------------------------
        # DETALHES
        # ------------------------------------

        for r in resultados:

            titulo = (
                f"⚽ {r['home_team']} "
                f"vs "
                f"{r['away_team']} "
                f"• {r['confianca_geral']:.1f}%"
            )

            with st.expander(titulo):

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "xG Casa",
                    r["xg_casa"]
                )

                c2.metric(
                    "xG Fora",
                    r["xg_fora"]
                )

                c3.metric(
                    "Forma Casa",
                    f"{r['forma_casa']:.0f}%"
                )

                c4.metric(
                    "Forma Fora",
                    f"{r['forma_fora']:.0f}%"
                )

                st.markdown(
                    "### 🎯 Previsões"
                )

                for p in r["previsoes"]:

                    prob = min(
                        float(
                            p["probabilidade"]
                        ),
                        1.0
                    )

                    st.markdown(
                        f"**{p['mercado']}** — "
                        f"{p['selecao']} "
                        f"• "
                        f"**{p['probabilidade']:.0%}** "
                        f"• Pontuação "
                        f"{p['pontuacao']:.1f}"
                    )

                    st.progress(
                        prob
                    )

                # Guardar previsões
                for p in r["previsoes"]:

                    database.salvar_previsao(
                        data_jogo=date_str,
                        jogo=(
                            f"{r['home_team']} "
                            f"vs "
                            f"{r['away_team']}"
                        ),
                        mercado=p["mercado"],
                        selecao=p["selecao"],
                        probabilidade=p["probabilidade"],
                        odd=p.get("odd"),
                        pontuacao=p["pontuacao"],
                        confianca_jogo=r[
                            "confianca_geral"
                        ]
                    )


# ============================================================
# ABA 2 — PESQUISA
# ============================================================

with tab2:

    st.subheader(
        "🔎 Pesquisar Jogo"
    )

    c1, c2 = st.columns(2)

    with c1:

        equipa_casa = st.text_input(
            "Equipa da Casa",
            placeholder="Ex: Arsenal"
        )

    with c2:

        equipa_fora = st.text_input(
            "Equipa de Fora",
            placeholder="Ex: Chelsea"
        )

    pesquisar = st.button(
        "🔍 Pesquisar",
        type="primary"
    )

    if pesquisar:

        if not equipa_casa or not equipa_fora:

            st.warning(
                "Indica as duas equipas."
            )

        else:

            with st.spinner(
                "A procurar..."
            ):

                api = APIFootballAPI()

                encontrado = None
                data_encontrada = None

                for i in range(7):

                    data = (
                        datetime.now().date()
                        + timedelta(days=i)
                    ).strftime(
                        "%Y-%m-%d"
                    )

                    eventos = (
                        api.get_scheduled_events(
                            data
                        )
                    )

                    for ev in eventos:

                        h = ev[
                            "home_team"
                        ].lower()

                        a = ev[
                            "away_team"
                        ].lower()

                        if (
                            equipa_casa.lower()
                            in h
                            and
                            equipa_fora.lower()
                            in a
                        ):

                            encontrado = ev
                            data_encontrada = data
                            break

                    if encontrado:
                        break

                if not encontrado:

                    st.warning(
                        "❌ Jogo não encontrado."
                    )

                else:

                    dados = (
                        api.prepare_match_data(
                            encontrado[
                                "event_id"
                            ]
                        )
                    )

                    if not dados:

                        st.error(
                            "Não foi possível "
                            "obter os dados."
                        )

                    else:

                        analise = analisar_jogo(
                            dados
                        )

                        st.success(
                            f"✅ Encontrado: "
                            f"{encontrado['home_team']} "
                            f"vs "
                            f"{encontrado['away_team']}"
                        )

                        c1, c2, c3 = st.columns(3)

                        c1.metric(
                            "xG Casa",
                            analise["xg_casa"]
                        )

                        c2.metric(
                            "xG Fora",
                            analise["xg_fora"]
                        )

                        c3.metric(
                            "Confiança",
                            f"{analise['confianca_geral']:.1f}%"
                        )

                        st.markdown(
                            "### 🎯 Mercados"
                        )

                        for p in analise[
                            "previsoes"
                        ]:

                            st.markdown(
                                f"**{p['mercado']}**: "
                                f"{p['selecao']} — "
                                f"**{p['probabilidade']:.0%}**"
                            )

                            st.progress(
                                min(
                                    p["probabilidade"],
                                    1
                                )
                            )


# ============================================================
# ABA 3 — BILHETE DO DIA
# ============================================================

with tab3:

    st.subheader(
        "🎟️ Bilhete do Dia"
    )

    st.info(
        "O Bilhete do Dia exige "
        "**10 ou mais jogos diferentes**."
    )

    bilhete = gerar_bilhete(
        resultados,
        min_jogos=10,
        max_jogos=15,
        min_pontuacao=65
    ) if resultados else None

    if not bilhete:

        st.warning(
            "⚠️ Não existem pelo menos "
            "10 jogos com qualidade suficiente "
            "para formar o Bilhete do Dia."
        )

        st.write(
            f"Jogos analisados: "
            f"**{len(resultados)}**"
        )

    else:

        database.salvar_bilhete(
            data_bilhete=date_str,
            selecoes=bilhete[
                "selecoes"
            ],
            odd_total=bilhete[
                "odd_total"
            ],
            confianca_media=bilhete[
                "confianca_media"
            ],
            tipo="Bilhete do Dia"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Jogos",
            bilhete[
                "num_selecoes"
            ]
        )

        c2.metric(
            "Confiança média",
            f"{bilhete['confianca_media']:.1f}%"
        )

        c3.metric(
            "Odd Total",
            (
                f"{bilhete['odd_total']:.2f}"
                if bilhete["odd_total"]
                else "N/D"
            )
        )

        st.divider()

        for i, sel in enumerate(
            bilhete["selecoes"],
            1
        ):

            st.markdown(
                f"### {i}. {sel['jogo']}"
            )

            st.write(
                f"**{sel['mercado']}** → "
                f"**{sel['selecao']}**"
            )

            st.progress(
                min(
                    sel["probabilidade"],
                    1
                )
            )

            st.caption(
                f"Probabilidade: "
                f"{sel['probabilidade']:.0%} "
                f"• Pontuação: "
                f"{sel['pontuacao']:.1f}"
            )


# ============================================================
# ABA 4 — MONTAGENS
# ============================================================

with tab4:

    st.subheader(
        "💎 Montagens Inteligentes"
    )

    st.caption(
        "Combinações de mercados do mesmo jogo "
        "quando existem sinais estatísticos "
        "suficientemente fortes."
    )

    montagens = (
        gerar_montagens_inteligentes(
            resultados
        )
        if resultados
        else []
    )

    if not montagens:

        st.info(
            "Nenhuma combinação suficientemente "
            "forte foi encontrada."
        )

    else:

        for montagem in montagens:

            database.salvar_bilhete(
                data_bilhete=date_str,
                selecoes=montagem[
                    "selecoes"
                ],
                odd_total=None,
                confianca_media=montagem[
                    "confianca_media"
                ],
                tipo=montagem["nome"]
            )

            with st.expander(
                f"{montagem['nome']} "
                f"• {montagem['num_selecoes']} "
                f"combinações "
                f"• {montagem['confianca_media']:.1f}%"
            ):

                for sel in montagem[
                    "selecoes"
                ]:

                    st.markdown(
                        f"**{sel['jogo']}**"
                    )

                    st.write(
                        f"{sel['mercado']} → "
                        f"{sel['selecao']}"
                    )

                    st.progress(
                        min(
                            sel[
                                "probabilidade"
                            ],
                            1
                        )
                    )

                    st.caption(
                        f"Confiança estimada: "
                        f"{sel['probabilidade']:.0%}"
                    )


# ============================================================
# ABA 5 — HISTÓRICO
# ============================================================

with tab5:

    st.subheader(
        "📜 Histórico"
    )

    c1, c2 = st.columns(2)

    with c1:

        st.markdown(
            "### 🎯 Previsões"
        )

        previsoes = (
            database.listar_previsoes(
                100
            )
        )

        if previsoes:

            df = pd.DataFrame(
                previsoes
            )

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.info(
                "Sem previsões."
            )

    with c2:

        st.markdown(
            "### 🎟️ Bilhetes"
        )

        bilhetes = (
            database.listar_bilhetes(
                30
            )
        )

        if not bilhetes:

            st.info(
                "Sem bilhetes."
            )

        else:

            for b in bilhetes:

                with st.expander(
                    f"{b['tipo']} — "
                    f"{b['data_bilhete']} "
                    f"• "
                    f"{b['confianca_media']:.1f}%"
                ):

                    st.write(
                        f"Status: "
                        f"**{b['status']}**"
                    )

                    try:

                        selecoes = (
                            json.loads(
                                b["selecoes"]
                            )
                            if isinstance(
                                b["selecoes"],
                                str
                            )
                            else b["selecoes"]
                        )

                    except:

                        selecoes = []

                    for sel in selecoes:

                        st.markdown(
                            f"- **{sel.get('jogo', '')}** "
                            f"→ "
                            f"{sel.get('mercado', '')}: "
                            f"{sel.get('selecao', '')}"
                        )

                    if b["odd_total"]:

                        st.write(
                            f"Odd total: "
                            f"**{b['odd_total']:.2f}**"
                        )

                    opcoes = [
                        "pendente",
                        "ganho",
                        "perdido"
                    ]

                    atual = (
                        b["status"]
                        if b["status"]
                        in opcoes
                        else "pendente"
                    )

                    novo = st.selectbox(
                        "Status",
                        opcoes,
                        index=opcoes.index(
                            atual
                        ),
                        key=f"status_{b['id']}"
                    )

                    if novo != atual:

                        if st.button(
                            "💾 Salvar",
                            key=f"save_{b['id']}"
                        ):

                            database.atualizar_status_bilhete(
                                b["id"],
                                novo
                            )

                            st.success(
                                "Status atualizado."
                            )

                            st.rerun()
