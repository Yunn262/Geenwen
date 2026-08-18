"""
FootballAI Bot - Recolha de dados com SoccerData (FBref / Understat)
100% Gratuito e Sem Limites de API

Funcionalidades:
- Jogos por data (Calendário/Resultados)
- Pesquisa de confrontos entre equipas (H2H)
- Estatísticas de desempenho de equipas
- Preparação dos dados para o motor de IA
"""

import pandas as pd
import soccerdata as sd
from datetime import datetime
from typing import Dict, List, Optional, Any

# Mapeamento de nomes de ligas do formato padrão para o formato exigido pelo FBref
LIGAS_SUPORTADAS = {
    "Premier League": "ENG-Premier League",
    "Brasileirao Serie A": "BRA-Serie A",
    "La Liga": "ESP-La Liga",
    "Serie A": "ITA-Serie A",
    "Bundesliga": "GER-Bundesliga",
    "Ligue 1": "FRA-Ligue 1",
    "Liga Portugal": "POR-Liga Portugal"
}

class SoccerDataScraper:

    def __init__(self, league_name: str = "Premier League", season: str = "2425"):
        """
        Inicializa o coletor do FBref para uma liga e temporada específicas.
        Formatos de temporada aceites: '2024', '2425', '2024-2025'
        """
        # Converte o nome amigável para o ID do FBref
        self.league_id = LIGAS_SUPORTADAS.get(league_name, "ENG-Premier League")
        self.season = season
        
        # Inicializa o cliente FBref (ele cria uma cache local automaticamente)
        self.fbref = sd.FBref(leagues=self.league_id, seasons=self.season)
        self.last_events = []

    # ========================================================
    # TESTAR INTEGRAÇÃO
    # ========================================================
    def testar_api(self) -> bool:
        """Verifica se a biblioteca consegue ler o calendário da liga com sucesso."""
        try:
            df = self.fbref.read_schedule()
            if df is not None and not df.empty:
                print(f"✅ SoccerData/FBref respondeu corretamente para a liga {self.league_id}.")
                return True
            return False
        except Exception as e:
            print(f"❌ Erro ao conectar ao SoccerData: {e}")
            return False

    # ========================================================
    # JOGOS POR DATA (Calendário e Resultados)
    # ========================================================
    def get_scheduled_events(self, date_str: str) -> List[Dict]:
        """
        Obtém todos os jogos de determinada data na liga configurada.
        Formato: YYYY-MM-DD
        """
        try:
            # Baixa ou lê da cache o calendário completo da temporada
            df = self.fbref.read_schedule()
            
            if df.empty:
                self.last_events = []
                return []

            # Resetar o index para transformar as colunas multi-index em colunas normais
            df = df.reset_index()

            # Filtrar os jogos pela data selecionada
            # O FBref armazena a coluna 'date' como datetime ou string YYYY-MM-DD
            df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df_filtrado = df[df['date_str'] == date_str]

            if df_filtrado.empty:
                print(f"⚠️ Nenhum jogo encontrado para {date_str} na liga {self.league_id}")
                self.last_events = []
                return []

            events = []
            for _, row in df_filtrado.iterrows():
                # Formatar o dicionário mantendo a estrutura original que a sua IA espera
                event = {
                    "event_id": row.get("game_id", None),
                    "home_team": row.get("home_team", "?"),
                    "away_team": row.get("away_team", "?"),
                    "home_team_id": None,  # Soccerdata usa strings/nomes como ID nativo
                    "away_team_id": None,
                    "tournament": row.get("league", self.league_id),
                    "season": row.get("season", self.season),
                    "start_time": str(row.get("date", "")),
                    "status": "Terminado" if pd.notna(row.get("home_score")) else "Agendado",
                    "status_short": "FT" if pd.notna(row.get("home_score")) else "NS",
                    "venue": row.get("venue", ""),
                    "referee": row.get("referee", ""),
                    # Dados do placar real e do xG (Golos Esperados) para o seu motor de IA
                    "home_score": row.get("home_score", None),
                    "away_score": row.get("away_score", None),
                    "home_xg": row.get("home_xg", None),
                    "away_xg": row.get("away_xg", None),
                    "raw": row.to_dict()
                }
                events.append(event)

            self.last_events = events
            print(f"✅ {len(events)} jogos encontrados para {date_str}")
            return events

        except Exception as e:
            print(f"❌ Erro ao processar eventos por data: {e}")
            return []

    # ========================================================
    # PESQUISAR CONFRONTO DIRETO (H2H) HISTÓRICO
    # ========================================================
    def pesquisar_jogo(self, equipa_casa: str, equipa_fora: str) -> List[Dict]:
        """
        CORREÇÃO DO LOOP: Busca todos os confrontos históricos entre as duas equipas 
        na temporada atual diretamente do DataFrame, sem fazer loops de requisições.
        """
        try:
            df = self.fbref.read_schedule().reset_index()
            
            casa = equipa_casa.lower().strip()
            fora = equipa_fora.lower().strip()

            # Filtrar onde as equipas se enfrentam (independente de quem é o mandante)
            condicao = (
                (df['home_team'].str.lower().str.contains(casa)) & 
                (df['away_team'].str.lower().str.contains(fora))
            ) | (
                (df['home_team'].str.lower().str.contains(fora)) & 
                (df['away_team'].str.lower().str.contains(casa))
            )

            df_confrontos = df[condicao]
            
            confrontos = []
            for _, row in df_confrontos.iterrows():
                confrontos.append({
                    "date": str(row.get("date", "")),
                    "home_team": row.get("home_team"),
                    "away_team": row.get("away_team"),
                    "score": f"{row.get('home_score', '?')}-{row.get('away_score', '?')}",
                    "home_xg": row.get("home_xg", 0.0),
                    "away_xg": row.get("away_xg", 0.0)
                })
            
            return confrontos
        except Exception as e:
            print(f"❌ Erro ao pesquisar confronto: {e}")
            return []

    # ========================================================
    # PREPARAÇÃO DE ESTATÍSTICAS PARA O MOTOR DE IA
    # ========================================================
    def get_team_stats_for_ai(self, equipa_nome: str) -> Dict[str, Any]:
        """
        Extrai métricas avançadas (xG, Remates, Passes, etc.) da equipa 
        para o seu modelo preditivo calcular os palpites.
        """
        try:
            # Puxa tabela de estatísticas de finalizações (Shooting) do FBref
            df_shooting = self.fbref.read_team_season_stats(stat_type="shooting")
            df_shooting = df_shooting.reset_index()

            # Encontrar a linha da equipa especificada
            df_team = df_shooting[df_shooting['team'].str.lower().str.contains(equipa_nome.lower().strip())]

            if df_team.empty:
                return {"erro": "Equipa não encontrada nas estatísticas globais"}

            row = df_team.iloc[0]

            # Dicionário estruturado pronto para análise estatística ou Machine Learning
            return {
                "team_name": row.get("team"),
                "remates_por_jogo": row.get(("90s", "Sh")) if isinstance(row.get("90s"), dict) else row.get("Sh"),
                "remates_a_baliza_pct": row.get(("Standard", "SoT%")),
                "gols_por_remate": row.get(("Standard", "G/Sh")),
                "distancia_media_remates": row.get(("Standard", "Dist")),
                "historico_disponivel": True
            }
        except Exception as e:
            print(f"❌ Erro ao extrair estatísticas para a IA: {e}")
            return {}
