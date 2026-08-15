# scraper.py
"""
Módulo de recolha de dados da SportMonks API v3.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# ============================================================
# CONFIGURAÇÃO
# ============================================================
API_KEY = "MEhqXtjX5ei5lwuvFqxMdoWbuRF57zEbEzyd8pFZjZOsmWRohJHTUUq1RgMP"  # ← COLOCA AQUI A TUA CHAVE REAL
BASE_URL = "https://api.sportmonks.com/v3/football"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def _get(endpoint: str, params: Dict) -> Optional[Dict]:
    """Faz GET request à SportMonks API."""
    params["api_token"] = API_KEY
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data
    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")
        return None

def _safe_get(data, *keys, default=None):
    """Acede a chaves aninhadas com segurança."""
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data

# ============================================================
# CLASSE PRINCIPAL
# ============================================================

class SportMonksAPI:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last_events = []

    # ---------- JOGOS DO DIA ----------
    def get_scheduled_events(self, date_str: str) -> List[Dict]:
        """
        Obtém jogos de uma data (formato 'YYYY-MM-DD').
        A data deve ser passada como filtro.
        """
        params = {
            "filters": f"fixtureDate:{date_str}",
            "include": "league;homeTeam;awayTeam",
            "per_page": 100,
        }
        data = _get("/fixtures", params)
        if not data or "data" not in data:
            self.last_events = []
            return []

        events = []
        for fx in _safe_get(data, "data", default=[]):
            home_team = _safe_get(fx, "homeTeam", "name", default="?")
            away_team = _safe_get(fx, "awayTeam", "name", default="?")
            league_name = _safe_get(fx, "league", "name", default="")
            event_id = fx.get("id")
            start_time = fx.get("starting_at", "")

            event = {
                "event_id": event_id,
                "home_team": home_team,
                "away_team": away_team,
                "tournament": league_name,
                "start_time": start_time,
                "status": fx.get("state", ""),
                "home_team_id": _safe_get(fx, "homeTeam", "id"),
                "away_team_id": _safe_get(fx, "awayTeam", "id"),
                "league_id": _safe_get(fx, "league", "id"),
                "raw": fx
            }
            events.append(event)

        self.last_events = events
        return events

    # ---------- DETALHES DO EVENTO ----------
    def get_event_details(self, event_id: str) -> Optional[Dict]:
        for ev in self.last_events:
            if str(ev["event_id"]) == str(event_id):
                return ev["raw"]
        return None

    # ---------- ESTATÍSTICAS (não implementado) ----------
    def get_event_statistics(self, event_id: str) -> Optional[Dict]:
        return None

    # ---------- ESCALAÇÕES (não implementado) ----------
    def get_event_lineups(self, event_id: str) -> Optional[Dict]:
        return None

    # ---------- ODDS (não implementado) ----------
    def get_event_odds(self, event_id: str) -> Optional[Dict]:
        return None

    # ---------- CLASSIFICAÇÃO ----------
    def get_tournament_standings(self, season_id: str) -> Optional[Dict]:
        params = {"per_page": 100}
        data = _get(f"/standings/{season_id}", params)
        return data

    # ---------- FORMA RECENTE ----------
    def get_team_recent_matches(self, team_id: str, num_matches: int = 5) -> List[Dict]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        params = {
            "filters": f"teamId:{team_id};fixtureDateStart:{start_date.strftime('%Y-%m-%d')};fixtureDateEnd:{end_date.strftime('%Y-%m-%d')}",
            "include": "homeTeam;awayTeam",
            "per_page": 50,
        }
        data = _get("/fixtures", params)
        if not data or "data" not in data:
            return []

        fixtures = _safe_get(data, "data", default=[])
        played = []
        for fx in fixtures:
            scores = fx.get("scores", [])
            if not scores:
                continue
            # Último score (final)
            final_score = scores[-1] if scores else {}
            home_goals = _safe_get(final_score, "score", "home", default=0) or 0
            away_goals = _safe_get(final_score, "score", "away", default=0) or 0

            if str(fx.get("home_team_id")) == str(team_id):
                golos_marcados = int(home_goals)
                golos_sofridos = int(away_goals)
                adversario = _safe_get(fx, "awayTeam", "name", default="?")
            else:
                golos_marcados = int(away_goals)
                golos_sofridos = int(home_goals)
                adversario = _safe_get(fx, "homeTeam", "name", default="?")

            played.append({
                "golos_marcados": golos_marcados,
                "golos_sofridos": golos_sofridos,
                "adversario": adversario,
                "data": fx.get("starting_at", "")
            })

        # Ordenar por data decrescente
        played.sort(key=lambda x: x["data"], reverse=True)
        return played[:num_matches]

    # ---------- PREPARAR DADOS PARA O MOTOR DE IA ----------
    def prepare_match_data(self, event_id: str) -> Optional[Dict]:
        evento = None
        for ev in self.last_events:
            if str(ev["event_id"]) == str(event_id):
                evento = ev
                break

        if not evento:
            print(f"Evento {event_id} não encontrado.")
            return None

        match_data = {
            "event_id": event_id,
            "home_team": evento["home_team"],
            "away_team": evento["away_team"],
            "data": datetime.now().strftime("%Y-%m-%d"),
            "forma_casa": [],
            "forma_fora": [],
            "golos_casa": [],
            "golos_fora": [],
            "golos_sofridos_casa": [],
            "golos_sofridos_fora": [],
            "posicao_casa": None,
            "posicao_fora": None,
            "media_cantos_casa": 4.5,
            "media_cantos_fora": 4.0,
            "media_cartoes_casa": 2.0,
            "media_cartoes_fora": 2.0,
            "odds": {}
        }

        home_id = evento.get("home_team_id")
        away_id = evento.get("away_team_id")
        league_id = evento.get("league_id")

        if home_id:
            try:
                ultimos_casa = self.get_team_recent_matches(home_id, 5)
                match_data["forma_casa"] = ultimos_casa
                match_data["golos_casa"] = [j["golos_marcados"] for j in ultimos_casa]
                match_data["golos_sofridos_casa"] = [j["golos_sofridos"] for j in ultimos_casa]
            except Exception as e:
                print(f"Erro forma casa: {e}")

        if away_id:
            try:
                ultimos_fora = self.get_team_recent_matches(away_id, 5)
                match_data["forma_fora"] = ultimos_fora
                match_data["golos_fora"] = [j["golos_marcados"] for j in ultimos_fora]
                match_data["golos_sofridos_fora"] = [j["golos_sofridos"] for j in ultimos_fora]
            except Exception as e:
                print(f"Erro forma fora: {e}")

        # Classificação (precisa do season_id, não league_id)
        # Pode ser adicionado depois se necessário
        # if league_id:
        #     standings = self.get_tournament_standings(league_id)
        #     ...

        return match_data

# ============================================================
# TESTE RÁPIDO
# ============================================================
if __name__ == "__main__":
    api = SportMonksAPI()
    date_str = "2026-08-15"
    print(f"Buscando jogos de {date_str}...")
    events = api.get_scheduled_events(date_str)
    if not events:
        print("Nenhum jogo encontrado.")
    else:
        print(f"Encontrados {len(events)} jogos.")
        for ev in events[:5]:
            print(f"- {ev['home_team']} vs {ev['away_team']} | ID: {ev['event_id']}")
