import streamlit as st
from scraper import SoccerDataScraper

st.title("🤖 Bot de Palpites IA - SoccerData")

# 1. Escolha da liga e inicialização do robô
liga = st.selectbox("Selecione a Liga:", ["Premier League", "Brasileirao Serie A"])
temporada = st.selectbox("Temporada:", ["2425", "2024"])

# Guardar a instância do robô no estado do Streamlit
if 'bot_ia' not in st.session_state:
    st.session_state.bot_ia = SoccerDataScraper(league_name=liga, season=temporada)

# 2. Buscar jogos do dia para palpites
data_hoje = st.date_input("Data do Confronto:").strftime("%Y-%m-%d")

if st.button("Analisar Jogos do Dia"):
    jogos = st.session_state.bot_ia.get_scheduled_events(data_hoje)
    
    if not jogos:
        st.info("Nenhum jogo listado para esta data.")
    for jogo in jogos:
        st.write(f"⚽ **{jogo['home_team']} vs {jogo['away_team']}**")
        
        # Puxa dados estatísticos pesados instantaneamente da cache para o seu motor de palpites
        stats_casa = st.session_state.bot_ia.get_team_stats_for_ai(jogo['home_team'])
        st.caption(f"Taxa de acerto de remates do mandante: {stats_casa.get('remates_a_baliza_pct')}%")
