"""
scraper.py
Recolha de dados da API-Football.

Inclui:
- Jogos
- Últimos jogos das equipas
- Estatísticas
- Escanteios
- Cartões
- Classificação
- Odds quando disponíveis
"""

import os
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("0ef75e8f44d4ab899653ab4d8753e386")

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY or "",
    "Accept": "application/json",
}


def _safe_get(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


class APIFootballAPI:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        self.last_events = []

        if not API_KEY:
            print("ATENÇÃO: API_FOOTBALL_KEY não encontrada no .env")

    # ========================================================
    # REQUEST
    # ========================================================

    def _get(self, endpoint: str, params: Dict):

        try:
            response = self.session.get(
                f"{BASE_URL}{endpoint}",
                params=params,
                timeout=20
            )

            if response.status_code != 200:
                print(
                    f"Erro API {response.status_code}: "
                    f"{response.text[:300]}"
                )
                return None

            data = response.json()

            errors = data.get("errors")

            if errors:
                print("Erro API-Football:", errors)

            return data

        except requests.RequestException as e:
            print(f"Erro de conexão com API: {e}")
            return None

    # ========================================================
    # JOGOS DO DIA
    # ========================================================

    def get_scheduled_events(self, date_str: str) -> List[Dict]:

        data = self._get(
            "/fixtures",
            {
                "date": date_str,
                "timezone": "Africa/Luanda"
            }
        )

        if not data:
            return []

        events = []

        for fx in data.get("response", []):

            fixture = fx.get("fixture", {})
            teams = fx.get("teams", {})
            league = fx.get("league", {})

            event_id = fixture.get("id")

            if not event_id:
                continue

            home = teams.get("home", {})
            away = teams.get("away", {})

            events.append({
                "event_id": event_id,

                "home_team": home.get("name", "?"),
                "away_team": away.get("name", "?"),

                "home_team_id": home.get("id"),
                "away_team_id": away.get("id"),

                "tournament": league.get("name", ""),
                "league_id": league.get("id"),
                "season": league.get("season"),

                "start_time": fixture.get("date", ""),

                "status": fixture.get(
                    "status", {}
                ).get("long", ""),

                "raw": fx
            })

        self.last_events = events

        return events

    # ========================================================
    # DETALHES
    # ========================================================

    def get_event_details(self, event_id):

        for event in self.last_events:

            if str(event["event_id"]) == str(event_id):
                return event["raw"]

        return None

    # ========================================================
    # ÚLTIMOS JOGOS
    # ========================================================

    def get_team_recent_matches(
        self,
        team_id,
        num_matches=5
    ):

        data = self._get(
            "/fixtures",
            {
                "team": team_id,
                "last": num_matches
            }
        )

        if not data:
            return []

        resultado = []

        for fx in data.get("response", []):

            goals = fx.get("goals", {})

            home_goals = goals.get("home")
            away_goals = goals.get("away")

            if home_goals is None or away_goals is None:
                continue

            teams = fx.get("teams", {})

            home = teams.get("home", {})
            away = teams.get("away", {})

            if str(home.get("id")) == str(team_id):

                marcado = int(home_goals)
                sofrido = int(away_goals)

                adversario = away.get(
                    "name",
                    "?"
                )

                casa = True

            else:

                marcado = int(away_goals)
                sofrido = int(home_goals)

                adversario = home.get(
                    "name",
                    "?"
                )

                casa = False

            resultado.append({

                "golos_marcados": marcado,
                "golos_sofridos": sofrido,

                "adversario": adversario,

                "casa": casa,

                "data": _safe_get(
                    fx,
                    "fixture",
                    "date",
                    default=""
                ),

                "fixture_id": _safe_get(
                    fx,
                    "fixture",
                    "id"
                )
            })

        return resultado[:num_matches]

    # ========================================================
    # ESTATÍSTICAS DO JOGO
    # ========================================================

    def get_event_statistics(self, event_id):

        data = self._get(
            "/fixtures/statistics",
            {
                "fixture": event_id
            }
        )

        if not data:
            return {}

        resultado = {}

        for team_stats in data.get("response", []):

            team = team_stats.get("team", {})

            team_id = team.get("id")

            if not team_id:
                continue

            stats = {}

            for item in team_stats.get(
                "statistics",
                []
            ):

                nome = item.get("type")
                valor = item.get("value")

                stats[nome] = valor

            resultado[team_id] = stats

        return resultado

    # ========================================================
    # CONVERTER ESTATÍSTICA
    # ========================================================

    @staticmethod
    def _number(value, default=0):

        if value is None:
            return default

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return value

        try:

            text = str(value)
            text = text.replace("%", "")

            return float(text)

        except Exception:
            return default

    # ========================================================
    # MÉDIAS DE ESCANTEIOS E CARTÕES
    # ========================================================

    def get_team_averages(
        self,
        team_id,
        num_matches=5
    ):

        jogos = self.get_team_recent_matches(
            team_id,
            num_matches
        )

        if not jogos:
            return {
                "cantos": 4.5,
                "cartoes": 2.0
            }

        cantos = []
        cartoes = []

        for jogo in jogos:

            fixture_id = jogo.get(
                "fixture_id"
            )

            if not fixture_id:
                continue

            try:

                stats = self.get_event_statistics(
                    fixture_id
                )

                team_stats = stats.get(
                    int(team_id),
                    {}
                )

                # ------------------------------
                # CANTOS
                # ------------------------------

                corners = team_stats.get(
                    "Corner Kicks"
                )

                if corners is not None:

                    valor = self._number(
                        corners,
                        0
                    )

                    cantos.append(valor)

                # ------------------------------
                # CARTÕES
                # ------------------------------

                yellow = team_stats.get(
                    "Yellow Cards"
                )

                if yellow is not None:

                    valor = self._number(
                        yellow,
                        0
                    )

                    cartoes.append(valor)

            except Exception as e:

                print(
                    f"Erro estatísticas {team_id}: {e}"
                )

        media_cantos = (
            sum(cantos) / len(cantos)
            if cantos else 4.5
        )

        media_cartoes = (
            sum(cartoes) / len(cartoes)
            if cartoes else 2.0
        )

        return {
            "cantos": round(
                media_cantos,
                2
            ),

            "cartoes": round(
                media_cartoes,
                2
            )
        }

    # ========================================================
    # CLASSIFICAÇÃO
    # ========================================================

    def get_tournament_standings(
        self,
        league_id,
        season
    ):

        if not league_id or not season:
            return {}

        data = self._get(
            "/standings",
            {
                "league": league_id,
                "season": season
            }
        )

        if not data:
            return {}

        try:

            standings = (
                data["response"][0]
                ["league"]["standings"][0]
            )

            resultado = {}

            for item in standings:

                team = item.get(
                    "team",
                    {}
                )

                team_id = team.get("id")

                if team_id:
                    resultado[
                        team_id
                    ] = item.get(
                        "rank"
                    )

            return resultado

        except Exception:

            return {}

    # ========================================================
    # ODDS
    # ========================================================

    def get_event_odds(
        self,
        event_id
    ):

        data = self._get(
            "/odds",
            {
                "fixture": event_id
            }
        )

        if not data:
            return {}

        return self._parse_odds(data)

    # ========================================================
    # INTERPRETAR ODDS
    # ========================================================

    def _parse_odds(self, data):

        odds = {}

        try:

            response = data.get(
                "response",
                []
            )

            for bookmaker in response:

                for bet in bookmaker.get(
                    "bookmakers",
                    []
                ):

                    pass

            # API-Football pode devolver
            # formatos diferentes dependendo
            # da conta/plano.

        except Exception as e:

            print(
                "Erro ao interpretar odds:",
                e
            )

        return odds

    # ========================================================
    # PREPARAR DADOS
    # ========================================================

    def prepare_match_data(
        self,
        event_id
    ):

        evento = None

        for ev in self.last_events:

            if str(
                ev["event_id"]
            ) == str(event_id):

                evento = ev
                break

        # Caso não esteja no cache,
        # tenta procurar diretamente.

        if not evento:

            data = self._get(
                "/fixtures",
                {
                    "id": event_id
                }
            )

            if data and data.get("response"):

                fx = data["response"][0]

                teams = fx.get(
                    "teams",
                    {}
                )

                league = fx.get(
                    "league",
                    {}
                )

                fixture = fx.get(
                    "fixture",
                    {}
                )

                evento = {

                    "event_id":
                        fixture.get("id"),

                    "home_team":
                        teams.get(
                            "home",
                            {}
                        ).get(
                            "name",
                            "?"
                        ),

                    "away_team":
                        teams.get(
                            "away",
                            {}
                        ).get(
                            "name",
                            "?"
                        ),

                    "home_team_id":
                        teams.get(
                            "home",
                            {}
                        ).get("id"),

                    "away_team_id":
                        teams.get(
                            "away",
                            {}
                        ).get("id"),

                    "league_id":
                        league.get("id"),

                    "season":
                        league.get("season"),

                    "raw": fx
                }

        if not evento:

            print(
                f"Evento {event_id} não encontrado."
            )

            return None

        home_id = evento.get(
            "home_team_id"
        )

        away_id = evento.get(
            "away_team_id"
        )

        # ====================================================
        # FORMA
        # ====================================================

        forma_casa = []

        forma_fora = []

        if home_id:

            try:

                forma_casa = (
                    self.get_team_recent_matches(
                        home_id,
                        5
                    )
                )

            except Exception as e:

                print(
                    "Erro forma casa:",
                    e
                )

        if away_id:

            try:

                forma_fora = (
                    self.get_team_recent_matches(
                        away_id,
                        5
                    )
                )

            except Exception as e:

                print(
                    "Erro forma fora:",
                    e
                )

        # ====================================================
        # GOLOS
        # ====================================================

        golos_casa = [
            x["golos_marcados"]
            for x in forma_casa
        ]

        golos_fora = [
            x["golos_marcados"]
            for x in forma_fora
        ]

        sofridos_casa = [
            x["golos_sofridos"]
            for x in forma_casa
        ]

        sofridos_fora = [
            x["golos_sofridos"]
            for x in forma_fora
        ]

        # ====================================================
        # CLASSIFICAÇÃO
        # ====================================================

        standings = self.get_tournament_standings(
            evento.get("league_id"),
            evento.get("season")
        )

        pos_casa = standings.get(
            home_id
        )

        pos_fora = standings.get(
            away_id
        )

        # ====================================================
        # ESCANTEIOS / CARTÕES
        # ====================================================

        stats_casa = {
            "cantos": 4.5,
            "cartoes": 2.0
        }

        stats_fora = {
            "cantos": 4.0,
            "cartoes": 2.0
        }

        if home_id:

            try:

                stats_casa = (
                    self.get_team_averages(
                        home_id,
                        5
                    )
                )

            except Exception:
                pass

        if away_id:

            try:

                stats_fora = (
                    self.get_team_averages(
                        away_id,
                        5
                    )
                )

            except Exception:
                pass

        # ====================================================
        # DADOS FINAIS
        # ====================================================

        return {

            "event_id":
                event_id,

            "home_team":
                evento.get(
                    "home_team",
                    "?"
                ),

            "away_team":
                evento.get(
                    "away_team",
                    "?"
                ),

            "forma_casa":
                forma_casa,

            "forma_fora":
                forma_fora,

            "golos_casa":
                golos_casa,

            "golos_fora":
                golos_fora,

            "golos_sofridos_casa":
                sofridos_casa,

            "golos_sofridos_fora":
                sofridos_fora,

            "posicao_casa":
                pos_casa,

            "posicao_fora":
                pos_fora,

            "media_cantos_casa":
                stats_casa["cantos"],

            "media_cantos_fora":
                stats_fora["cantos"],

            "media_cartoes_casa":
                stats_casa["cartoes"],

            "media_cartoes_fora":
                stats_fora["cartoes"],

            "odds": {}
        }


# ============================================================
# TESTE
# ============================================================

if __name__ == "__main__":

    api = APIFootballAPI()

    hoje = datetime.now().strftime(
        "%Y-%m-%d"
    )

    print(
        f"Buscando jogos de {hoje}..."
    )

    jogos = api.get_scheduled_events(
        hoje
    )

    print(
        f"Encontrados: {len(jogos)}"
    )

    for jogo in jogos[:10]:

        print(
            jogo["home_team"],
            "vs",
            jogo["away_team"]
        )
