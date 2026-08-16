import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

API_KEY = os.getenv("0ef75e8f44d4ab899653ab4d8753e386", "").strip()
BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY,
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
        self.cache_stats = {}
        self.cache_fixtures = {}

    def _get(self, endpoint: str, params: Dict) -> Optional[Dict]:
        if not API_KEY:
            print("ERRO: API_FOOTBALL_KEY não configurada.")
            return None

        try:
            response = self.session.get(
                f"{BASE_URL}{endpoint}",
                params=params,
                timeout=20
            )

            response.raise_for_status()
            data = response.json()

            errors = data.get("errors")
            if errors:
                print(f"API-Football: {errors}")

            return data

        except requests.RequestException as e:
            print(f"Erro API-Football: {e}")
            return None

    # =========================================================
    # JOGOS DO DIA
    # =========================================================

    def get_scheduled_events(self, date_str: str) -> List[Dict]:

        params = {
            "date": date_str,
            "timezone": "Africa/Luanda"
        }

        data = self._get("/fixtures", params)

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

            events.append({
                "event_id": event_id,
                "home_team": _safe_get(
                    teams, "home", "name", default="?"
                ),
                "away_team": _safe_get(
                    teams, "away", "name", default="?"
                ),
                "home_team_id": _safe_get(
                    teams, "home", "id"
                ),
                "away_team_id": _safe_get(
                    teams, "away", "id"
                ),
                "tournament": league.get("name", ""),
                "league_id": league.get("id"),
                "season": league.get("season"),
                "start_time": fixture.get("date", ""),
                "status": _safe_get(
                    fixture, "status", "long", default=""
                ),
                "raw": fx
            })

        self.last_events = events
        return events

    # =========================================================
    # ESTATÍSTICAS DE UM JOGO
    # =========================================================

    def get_event_statistics(self, event_id: int) -> Optional[Dict]:

        if event_id in self.cache_stats:
            return self.cache_stats[event_id]

        data = self._get(
            "/fixtures/statistics",
            {"fixture": event_id}
        )

        if not data:
            return None

        self.cache_stats[event_id] = data
        return data

    # =========================================================
    # ESCALAÇÕES
    # =========================================================

    def get_event_lineups(self, event_id: int) -> Optional[Dict]:

        return self._get(
            "/fixtures/lineups",
            {"fixture": event_id}
        )

    # =========================================================
    # ODDS
    # =========================================================

    def get_event_odds(self, event_id: int) -> Dict:

        data = self._get(
            "/odds",
            {"fixture": event_id}
        )

        if not data:
            return {}

        return self._parse_odds(data)

    def _parse_odds(self, data: Dict) -> Dict:

        odds = {}

        try:
            bookmakers = data.get("response", [])

            if not bookmakers:
                return odds

            bets = bookmakers[0].get("bookmakers", [])

            if not bets:
                return odds

            for bookmaker in bets:

                for bet in bookmaker.get("bets", []):

                    name = str(
                        bet.get("name", "")
                    ).lower()

                    values = bet.get("values", [])

                    for value in values:

                        label = str(
                            value.get("value", "")
                        ).lower()

                        odd = value.get("odd")

                        try:
                            odd = float(odd)
                        except:
                            continue

                        if "match winner" in name:

                            if label in ["home", "1"]:
                                odds.setdefault(
                                    "1x2", {}
                                )["casa"] = odd

                            elif label in ["draw", "x"]:
                                odds.setdefault(
                                    "1x2", {}
                                )["empate"] = odd

                            elif label in ["away", "2"]:
                                odds.setdefault(
                                    "1x2", {}
                                )["fora"] = odd

                        elif "over/under" in name:

                            if "1.5" in label:
                                odds["over_1_5"] = odd

                            elif "2.5" in label:
                                odds["over_2_5"] = odd

                        elif "both teams to score" in name:

                            if label == "yes":
                                odds["btts"] = odd

        except Exception as e:
            print(f"Erro ao processar odds: {e}")

        return odds

    # =========================================================
    # FORMA RECENTE
    # =========================================================

    def get_team_recent_matches(
        self,
        team_id: int,
        num_matches: int = 10
    ) -> List[Dict]:

        cache_key = f"{team_id}_{num_matches}"

        if cache_key in self.cache_fixtures:
            return self.cache_fixtures[cache_key]

        data = self._get(
            "/fixtures",
            {
                "team": team_id,
                "last": num_matches
            }
        )

        if not data:
            return []

        result = []

        for fx in data.get("response", []):

            fixture_id = fx.get(
                "fixture", {}
            ).get("id")

            teams = fx.get("teams", {})
            goals = fx.get("goals", {})

            home_id = _safe_get(
                teams, "home", "id"
            )

            away_id = _safe_get(
                teams, "away", "id"
            )

            hg = goals.get("home")
            ag = goals.get("away")

            if hg is None or ag is None:
                continue

            if str(home_id) == str(team_id):

                gm = int(hg)
                gs = int(ag)
                casa = True
                adversario = _safe_get(
                    teams, "away", "name", default="?"
                )

            elif str(away_id) == str(team_id):

                gm = int(ag)
                gs = int(hg)
                casa = False
                adversario = _safe_get(
                    teams, "home", "name", default="?"
                )

            else:
                continue

            stats = self.get_fixture_team_stats(
                fixture_id,
                team_id
            )

            result.append({
                "golos_marcados": gm,
                "golos_sofridos": gs,
                "adversario": adversario,
                "data": _safe_get(
                    fx, "fixture", "date", default=""
                ),
                "casa": casa,
                "escanteios_favor": stats["escanteios_favor"],
                "escanteios_contra": stats["escanteios_contra"],
                "cartoes": stats["cartoes"]
            })

        result = result[:num_matches]

        self.cache_fixtures[cache_key] = result

        return result

    # =========================================================
    # ESTATÍSTICAS DE UMA EQUIPE NUM JOGO
    # =========================================================

    def get_fixture_team_stats(
        self,
        fixture_id: int,
        team_id: int
    ) -> Dict:

        stats = {
            "escanteios_favor": 0.0,
            "escanteios_contra": 0.0,
            "cartoes": 0.0
        }

        data = self.get_event_statistics(fixture_id)

        if not data:
            return stats

        responses = data.get("response", [])

        minha_equipa = None
        adversario = None

        for item in responses:

            tid = _safe_get(
                item, "team", "id"
            )

            if str(tid) == str(team_id):
                minha_equipa = item
            else:
                adversario = item

        if not minha_equipa:
            return stats

        valores = {}

        for stat in minha_equipa.get(
            "statistics", []
        ):

            nome = str(
                stat.get("type", "")
            ).lower()

            valor = stat.get("value")

            if isinstance(valor, str):
                try:
                    valor = float(
                        valor.replace("%", "")
                    )
                except:
                    valor = 0

            valores[nome] = valor or 0

        esc_favor = valores.get(
            "corner kicks",
            0
        )

        cartoes = (
            valores.get("yellow cards", 0)
            or 0
        )

        stats["escanteios_favor"] = float(
            esc_favor or 0
        )

        stats["cartoes"] = float(
            cartoes or 0
        )

        if adversario:

            adv_values = {}

            for stat in adversario.get(
                "statistics", []
            ):

                nome = str(
                    stat.get("type", "")
                ).lower()

                valor = stat.get("value")

                if isinstance(valor, str):
                    try:
                        valor = float(
                            valor.replace("%", "")
                        )
                    except:
                        valor = 0

                adv_values[nome] = valor or 0

            stats["escanteios_contra"] = float(
                adv_values.get(
                    "corner kicks",
                    0
                ) or 0
            )

        return stats

    # =========================================================
    # CLASSIFICAÇÃO
    # =========================================================

    def get_tournament_standings(
        self,
        league_id: int,
        season: int
    ) -> Optional[Dict]:

        return self._get(
            "/standings",
            {
                "league": league_id,
                "season": season
            }
        )

    def get_team_position(
        self,
        league_id: int,
        season: int,
        team_id: int
    ) -> Optional[int]:

        data = self.get_tournament_standings(
            league_id,
            season
        )

        if not data:
            return None

        try:

            standings = data["response"][0][
                "league"
            ]["standings"][0]

            for team in standings:

                if str(
                    team["team"]["id"]
                ) == str(team_id):

                    return int(
                        team["rank"]
                    )

        except Exception:
            pass

        return None

    # =========================================================
    # PREPARAR DADOS
    # =========================================================

    def prepare_match_data(
        self,
        event_id: int
    ) -> Optional[Dict]:

        evento = None

        for ev in self.last_events:

            if str(ev["event_id"]) == str(event_id):
                evento = ev
                break

        if not evento:
            return None

        home_id = evento.get("home_team_id")
        away_id = evento.get("away_team_id")

        dados = {
            "event_id": event_id,
            "home_team": evento["home_team"],
            "away_team": evento["away_team"],
            "data": evento.get("start_time", ""),
            "liga_id": evento.get("league_id"),
            "season": evento.get("season"),

            "forma_casa": [],
            "forma_fora": [],

            "golos_casa": [],
            "golos_fora": [],

            "golos_sofridos_casa": [],
            "golos_sofridos_fora": [],

            "cantos_casa": [],
            "cantos_fora": [],

            "cartoes_casa": [],
            "cartoes_fora": [],

            "media_cantos_casa": None,
            "media_cantos_fora": None,

            "media_cartoes_casa": None,
            "media_cartoes_fora": None,

            "posicao_casa": None,
            "posicao_fora": None,

            "odds": {}
        }

        # -------------------------
        # CASA
        # -------------------------

        if home_id:

            jogos = self.get_team_recent_matches(
                home_id,
                10
            )

            dados["forma_casa"] = jogos

            dados["golos_casa"] = [
                x["golos_marcados"]
                for x in jogos
            ]

            dados["golos_sofridos_casa"] = [
                x["golos_sofridos"]
                for x in jogos
            ]

            dados["cantos_casa"] = [
                x["escanteios_favor"]
                for x in jogos
                if x["escanteios_favor"] > 0
            ]

            dados["cartoes_casa"] = [
                x["cartoes"]
                for x in jogos
                if x["cartoes"] > 0
            ]

        # -------------------------
        # FORA
        # -------------------------

        if away_id:

            jogos = self.get_team_recent_matches(
                away_id,
                10
            )

            dados["forma_fora"] = jogos

            dados["golos_fora"] = [
                x["golos_marcados"]
                for x in jogos
            ]

            dados["golos_sofridos_fora"] = [
                x["golos_sofridos"]
                for x in jogos
            ]

            dados["cantos_fora"] = [
                x["escanteios_favor"]
                for x in jogos
                if x["escanteios_favor"] > 0
            ]

            dados["cartoes_fora"] = [
                x["cartoes"]
                for x in jogos
                if x["cartoes"] > 0
            ]

        # -------------------------
        # MÉDIAS
        # -------------------------

        if dados["cantos_casa"]:
            dados["media_cantos_casa"] = sum(
                dados["cantos_casa"]
            ) / len(
                dados["cantos_casa"]
            )

        if dados["cantos_fora"]:
            dados["media_cantos_fora"] = sum(
                dados["cantos_fora"]
            ) / len(
                dados["cantos_fora"]
            )

        if dados["cartoes_casa"]:
            dados["media_cartoes_casa"] = sum(
                dados["cartoes_casa"]
            ) / len(
                dados["cartoes_casa"]
            )

        if dados["cartoes_fora"]:
            dados["media_cartoes_fora"] = sum(
                dados["cartoes_fora"]
            ) / len(
                dados["cartoes_fora"]
            )

        # -------------------------
        # CLASSIFICAÇÃO
        # -------------------------

        league = evento.get("league_id")
        season = evento.get("season")

        if league and season:

            dados["posicao_casa"] = (
                self.get_team_position(
                    league,
                    season,
                    home_id
                )
            )

            dados["posicao_fora"] = (
                self.get_team_position(
                    league,
                    season,
                    away_id
                )
            )

        # -------------------------
        # ODDS
        # -------------------------

        try:
            dados["odds"] = self.get_event_odds(
                event_id
            )
        except Exception:
            dados["odds"] = {}

        return dados


if __name__ == "__main__":

    api = APIFootballAPI()

    hoje = datetime.now().strftime(
        "%Y-%m-%d"
    )

    jogos = api.get_scheduled_events(hoje)

    print(
        f"Encontrados {len(jogos)} jogos."
    )

    for jogo in jogos[:10]:

        print(
            jogo["home_team"],
            "vs",
            jogo["away_team"]
        )
