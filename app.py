import json
import re
import unicodedata

import pandas as pd
import streamlit as st

from datetime import datetime, timedelta

from streamlit_autorefresh import (
    st_autorefresh
)

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

    page_title="⚽ FootballAI Bot",

    page_icon="⚽",

    layout="wide",

    initial_sidebar_state="expanded"
)


# ============================================================
# AUTO REFRESH
# ============================================================

st_autorefresh(
    interval=300000,
    key="football_auto_refresh"
)


# ============================================================
# ESTILO
# ============================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 800;
}

.card {
    padding: 18px;
    border-radius: 15px;
    border: 1px solid rgba(128,128,128,.25);
    margin-bottom: 10px;
}

</style>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="main-title">⚽ FootballAI Bot</div>',
    unsafe_allow_html=True
)

st.caption(
    "🤖 Análise automática de futebol | "
    "⚽ Golos | 🚩 Escanteios | 🟨 Cartões"
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Configurações")

    data_selecionada = st.date_input(

        "📅 Data dos jogos",

        value=datetime.now().date(),

        min_value=(
            datetime.now().date()
            -
            timedelta(days=7)
        ),

        max_value=(
            datetime.now().date()
            +
            timedelta(days=7)
        )
    )

    st.divider()

    st.info(
        "🔄 Atualização automática: 5 minutos"
    )

    st.info(
        "🎟️ Bilhete do dia: mínimo 10 jogos"
    )

    st.info(
        "🚫 Máximo de 1 seleção por jogo"
    )


# ============================================================
# NORMALIZAR TEXTO
# ============================================================

def normalizar(texto):

    if not texto:
        return ""

    texto = str(
        texto
    ).lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        c
        for c in texto
        if unicodedata.category(c)
        != "Mn"
    )

    texto = re.sub(
        r"[^a-z0-9\s]",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    return texto


def equipa_corresponde(
    pesquisa,
    nome
):

    pesquisa = normalizar(
        pesquisa
    )

    nome = normalizar(
        nome
    )

    if not pesquisa or not nome:
        return False

    # Correspondência direta
    if pesquisa in nome:
        return True

    # Comparação por palavras
    palavras = pesquisa.split()

    if all(
        palavra in nome
        for palavra in palavras
    ):
        return True

    return False


# ============================================================
# CACHE DOS JOGOS
# ============================================================

@st.cache_data(ttl=300)
def buscar_e_analisar(
    date_str
):

    api = APIFootballAPI()

    jogos = api.get_scheduled_events(
        date_str
    )

    resultados = []

    if not jogos:
        return []

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

            analise["event_id"] = (
                jogo["event_id"]
            )

            resultados.append(
                analise
            )

        except Exception as e:

            print(
                "Erro análise:",
                e
            )

    resultados.sort(
        key=lambda x:
            x.get(
                "confianca_geral",
                0
            ),
        reverse=True
    )

    return resultados


# ============================================================
# OBTER RESULTADOS
# ============================================================

date_str = (
    data_selecionada.strftime(
        "%Y-%m-%d"
    )
)

with st.spinner(
    "⚽ A recolher e analisar os jogos..."
):

    resultados = buscar_e_analisar(
        date_str
    )


# ============================================================
# ABAS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([

    "📊 Análise",

    "🔎 Pesquisa",

    "🎟️ Bilhete do Dia",

    "💎 Montagens",

    "📜 Histórico"
])


# ============================================================
# ABA 1
# ============================================================

with tab1:

    st.subheader(
        f"📅 Jogos de {date_str}"
    )

    st.metric(
        "Jogos analisados",
        len(resultados)
    )

    if not resultados:

        st.warning(
            "Nenhum jogo encontrado para esta data."
        )

    else:

        # -----------------------------------------------
        # SALVAR PREVISÕES
        # -----------------------------------------------

        for r in resultados:

            for p in r.get(
                "previsoes",
                []
            ):

                database.salvar_previsao(

                    data_jogo=date_str,

                    jogo=(
                        f"{r['home_team']} "
                        f"vs "
                        f"{r['away_team']}"
                    ),

                    mercado=p["mercado"],

                    selecao=p["selecao"],

                    probabilidade=p[
                        "probabilidade"
                    ],

                    odd=p.get("odd"),

                    pontuacao=p[
                        "pontuacao"
                    ],

                    confianca_jogo=r[
                        "confianca_geral"
                    ]
                )

        # -----------------------------------------------
        # TABELA
        # -----------------------------------------------

        rows = []

        for r in resultados:

            melhores = r.get(
                "previsoes",
                []
            )[:3]

            top = " | ".join([

                f"{p['mercado']}: "
                f"{p['selecao']} "
                f"({p['probabilidade']:.0%})"

                for p in melhores
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
                    )[-14:-9],

                "xG":
                    f"{r['xg_casa']:.2f} - "
                    f"{r['xg_fora']:.2f}",

                "Confiança":
                    f"{r['confianca_geral']}%",

                "Melhores mercados":
                    top
            })

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # -----------------------------------------------
        # DETALHES
        # -----------------------------------------------

        for r in resultados:

            with st.expander(

                f"⚽ {r['home_team']} "
                f"vs "
                f"{r['away_team']} "
                f" | "
                f"Confiança: "
                f"{r['confianca_geral']}%"
            ):

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
                    "Escanteios Casa",
                    r.get(
                        "media_cantos_casa",
                        4.5
                    )
                )

                c4.metric(
                    "Escanteios Fora",
                    r.get(
                        "media_cantos_fora",
                        4.0
                    )
                )

                st.markdown(
                    "### 🤖 Palpites"
                )

                for p in r.get(
                    "previsoes",
                    []
                ):

                    st.markdown(

                        f"**{p['mercado']}** → "
                        f"**{p['selecao']}** "
                        f"| "
                        f"{p['probabilidade']:.0%} "
                        f"| Pontuação: "
                        f"{p['pontuacao']:.1f}"
                    )


# ============================================================
# ABA 2 - PESQUISA
# ============================================================

with tab2:

    st.subheader(
        "🔎 Pesquisar Jogo"
    )

    st.caption(
        "Procura automaticamente nos próximos 7 dias."
    )

    c1, c2 = st.columns(2)

    with c1:

        equipa_casa = st.text_input(
            "🏠 Equipa da Casa",
            placeholder="Ex: Arsenal"
        )

    with c2:

        equipa_fora = st.text_input(
            "✈️ Equipa de Fora",
            placeholder="Ex: Chelsea"
        )

    pesquisar = st.button(
        "🔍 Pesquisar",
        type="primary"
    )

    if pesquisar:

        if (
            not equipa_casa
            or
            not equipa_fora
        ):

            st.warning(
                "Digite as duas equipas."
            )

        else:

            api = APIFootballAPI()

            encontrados = []

            with st.spinner(
                "🔎 Procurando nos próximos 7 dias..."
            ):

                for i in range(7):

                    data_pesquisa = (

                        datetime.now().date()
                        +
                        timedelta(days=i)
                    ).strftime(
                        "%Y-%m-%d"
                    )

                    eventos = (
                        api.get_scheduled_events(
                            data_pesquisa
                        )
                    )

                    for ev in eventos:

                        casa_ok = equipa_corresponde(
                            equipa_casa,
                            ev["home_team"]
                        )

                        fora_ok = equipa_corresponde(
                            equipa_fora,
                            ev["away_team"]
                        )

                        if casa_ok and fora_ok:

                            encontrados.append(
                                (
                                    data_pesquisa,
                                    ev
                                )
                            )

            # ------------------------------------------------
            # RESULTADOS
            # ------------------------------------------------

            if not encontrados:

                st.error(
                    "❌ Jogo não encontrado "
                    "nos próximos 7 dias."
                )

                st.info(
                    "💡 Tenta escrever apenas "
                    "parte do nome da equipa."
                )

            else:

                st.success(
                    f"✅ {len(encontrados)} "
                    f"jogo(s) encontrado(s)."
                )

                # ------------------------------------------------
                # ESCOLHER JOGO
                # ------------------------------------------------

                opcoes = [

                    f"{data} | "
                    f"{ev['home_team']} "
                    f"vs "
                    f"{ev['away_team']}"

                    for data, ev
                    in encontrados
                ]

                escolha = st.selectbox(
                    "Seleciona o jogo:",
                    range(len(opcoes)),
                    format_func=lambda i:
                        opcoes[i]
                )

                data_jogo, evento = (
                    encontrados[escolha]
                )

                # ------------------------------------------------
                # ANALISAR
                # ------------------------------------------------

                with st.spinner(
                    "🤖 A analisar o jogo..."
                ):

                    dados = (
                        api.prepare_match_data(
                            evento["event_id"]
                        )
                    )

                    if dados:

                        analise = analisar_jogo(
                            dados
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
                            f"{analise['confianca_geral']}%"
                        )

                        st.divider()

                        st.markdown(
                            "### 📊 Palpites"
                        )

                        for p in analise[
                            "previsoes"
                        ]:

                            st.markdown(

                                f"**{p['mercado']}**  \n"
                                f"➡️ **{p['selecao']}**  \n"
                                f"📊 Probabilidade: "
                                f"**{p['probabilidade']:.0%}**  \n"
                                f"⭐ Pontuação: "
                                f"**{p['pontuacao']:.1f}**"
                            )

                            st.progress(
                                float(
                                    p["probabilidade"]
                                )
                            )

                            st.divider()

                    else:

                        st.error(
                            "Não foi possível "
                            "obter os dados."
                        )


# ============================================================
# ABA 3 - BILHETE
# ============================================================

with tab3:

    st.subheader(
        "🎟️ Bilhete do Dia"
    )

    st.info(
        "O bilhete exige pelo menos "
        "**10 jogos diferentes**."
    )

    if len(resultados) < 10:

        st.warning(

            f"⚠️ Existem apenas "
            f"**{len(resultados)} jogos analisados**. "

            f"O Bilhete do Dia só será criado "
            f"quando existirem pelo menos "
            f"**10 jogos**."
        )

    else:

        bilhete = gerar_bilhete(
            resultados,
            minimo_jogos=10,
            max_selecoes=20
        )

        if bilhete:

            st.success(
                f"🎟️ Bilhete criado com "
                f"**{bilhete['num_jogos']} jogos**."
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Jogos",
                bilhete["num_jogos"]
            )

            c2.metric(
                "Confiança média",
                f"{bilhete['confianca_media']:.1f}%"
            )

            c3.metric(
                "Odd total",
                (
                    f"{bilhete['odd_total']:.2f}"
                    if bilhete["odd_total"]
                    else "Indisponível"
                )
            )

            st.divider()

            for i, sel in enumerate(
                bilhete["selecoes"],
                start=1
            ):

                st.markdown(

                    f"### {i}. ⚽ {sel['jogo']}"

                )

                st.markdown(

                    f"**{sel['mercado']}** → "
                    f"**{sel['selecao']}** "
                    f"| "
                    f"📊 {sel['probabilidade']:.0%} "
                    f"| "
                    f"⭐ {sel['pontuacao']:.1f}"
                )

            # Salvar
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

                tipo="normal"
            )

        else:

            st.warning(
                "Não foi possível gerar "
                "o bilhete."
            )


# ============================================================
# ABA 4 - MONTAGENS
# ============================================================

with tab4:

    st.subheader(
        "💎 Montagens Inteligentes"
    )

    if len(resultados) < 10:

        st.warning(
            "São necessários pelo menos "
            "**10 jogos analisados**."
        )

    else:

        montagens = (
            gerar_montagens_inteligentes(
                resultados
            )
        )

        if not montagens:

            st.info(
                "Não existem montagens "
                "com os critérios atuais."
            )

        else:

            for m in montagens:

                with st.expander(

                    f"{m['nome']} | "
                    f"{m['num_selecoes']} jogos | "
                    f"Confiança "
                    f"{m['confianca_media']:.1f}%"
                ):

                    for i, sel in enumerate(
                        m["selecoes"],
                        start=1
                    ):

                        st.markdown(

                            f"**{i}.** "
                            f"{sel['jogo']} → "
                            f"**{sel['mercado']}**: "
                            f"**{sel['selecao']}** "
                            f"({sel['probabilidade']:.0%})"
                        )

                    if m.get(
                        "odd_total"
                    ):

                        st.success(

                            f"Odd total: "
                            f"{m['odd_total']:.2f}"
                        )

                    database.salvar_bilhete(

                        data_bilhete=date_str,

                        selecoes=m[
                            "selecoes"
                        ],

                        odd_total=m[
                            "odd_total"
                        ],

                        confianca_media=m[
                            "confianca_media"
                        ],

                        tipo=m[
                            "nome"
                        ]
                    )


# ============================================================
# ABA 5 - HISTÓRICO
# ============================================================

with tab5:

    st.subheader(
        "📜 Histórico"
    )

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # PREVISÕES
    # --------------------------------------------------------

    with col1:

        st.markdown(
            "### 📊 Previsões"
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

    # --------------------------------------------------------
    # BILHETES
    # --------------------------------------------------------

    with col2:

        st.markdown(
            "### 🎟️ Bilhetes"
        )

        bilhetes = (
            database.listar_bilhetes(
                50
            )
        )

        if bilhetes:

            for b in bilhetes:

                with st.expander(

                    f"{b['tipo']} | "
                    f"{b['data_bilhete']} | "
                    f"{b['status']}"
                ):

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

                    st.write(
                        f"Jogos: "
                        f"{len(selecoes)}"
                    )

                    st.write(
                        f"Confiança: "
                        f"{b['confianca_media']}%"
                    )

                    for sel in selecoes:

                        st.markdown(

                            f"- {sel['jogo']} → "
                            f"{sel['mercado']}: "
                            f"**{sel['selecao']}**"
                        )

                    st.divider()

                    opcoes = [
                        "pendente",
                        "ganho",
                        "perdido"
                    ]

                    status_atual = (
                        b["status"]
                        if b["status"]
                        in opcoes
                        else "pendente"
                    )

                    novo_status = st.selectbox(

                        "Status",

                        opcoes,

                        index=opcoes.index(
                            status_atual
                        ),

                        key=f"status_{b['id']}"
                    )

                    if st.button(
                        "💾 Guardar",
                        key=f"guardar_{b['id']}"
                    ):

                        database.atualizar_status_bilhete(
                            b["id"],
                            novo_status
                        )

                        st.success(
                            "Status atualizado."
                        )

                        st.rerun()

        else:

            st.info(
                "Sem bilhetes."
            )
