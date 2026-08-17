# scraper.py
"""
FootballAI Bot - Recolha de dados da API-Football

API:
https://v3.football.api-sports.io

Funcionalidades:
- Jogos por data
- Pesquisa de equipas
- Últimos jogos
- Estatísticas
- Escalações
- Odds
- Classificação
- Preparação dos dados para o motor de IA
"""

import os
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

# ============================================================
# CONFIGURAÇÃO
# ============================================================

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


API_KEY = os.getenv("1e0fa7a4aac45071ea25522926441080", "").strip()

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY,
    "Accept": "application/json",
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def _safe_get(data, *keys, default=None):
    """
    Acede a dados aninhados com segurança.
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default

    return data


def _get(endpoint: str, params: Dict) -> Optional[Dict]:
    """
    Faz uma requisição GET à API-Football.
    """

    if not API_KEY:
        print("❌ API_FOOTBALL_KEY não configurada.")
        return None

    url = f"{BASE_URL}{endpoint}"

    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=20
        )

        print(
            f"API-Football | "
            f"{endpoint} | "
            f"status={response.status_code}"
        )

        # ----------------------------------------------------
        # ERROS HTTP
        # ----------------------------------------------------

        if response.status_code != 200:
            print("❌ Erro HTTP:")
            print(response.text[:1000])
            return None

        data = response.json()

        # ----------------------------------------------------
        # ERROS DA API
        # ----------------------------------------------------

        errors = data.get("errors")

        if errors:
            print("❌ Erros da API:")
            print(errors)

        # ----------------------------------------------------
        # RATE LIMIT / REQUESTS
        # ----------------------------------------------------

        paging = data.get("paging", {})

        print(
            f"API-Football | "
            f"results={paging.get('total', '?')}"
        )

        return data

    except requests.exceptions.Timeout:
        print("❌ Timeout ao consultar a API-Football.")
        return None

    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão com a API-Football.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        return None

    except ValueError:
        print("❌ A API retornou uma resposta que não é JSON.")
        return None

    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return None


# ============================================================
# CLASSE PRINCIPAL
# ============================================================

class APIFootballAPI:

    def __init__(self):

        self.session = requests.Session()

        if API_KEY:
            self.session.headers.update(HEADERS)

        self.last_events = []

    # ========================================================
    # TESTAR API
    # ========================================================

    def testar_api(self) -> bool:

        if not API_KEY:
            print("❌ API key não configurada.")
            return False

        data = _get(
            "/status",
            {}
        )

        if data is not None:
            print("✅ API-Football respondeu.")
            return True

        return False

    # ========================================================
    # JOGOS POR DATA
    # ========================================================

    def get_scheduled_events(self, date_str: str) -> List[Dict]:
        """
        Obtém todos os jogos de determinada data.

        Formato:
        YYYY-MM-DD
        """

        if not date_str:
            return []

        params = {
            "date": date_str
        }

        data = _get(
            "/fixtures",
            params
        )

        if not data:
            self.last_events = []
            return []

        response = data.get("response", [])

        if not response:
            print(
                f"⚠️ Nenhum jogo retornado para {date_str}"
            )

            self.last_events = []

            return []

        events = []

        for fx in response:

            try:

                teams = fx.get("teams", {})
                league = fx.get("league", {})
                fixture = fx.get("fixture", {})

                home = teams.get("home") or {}
                away = teams.get("away") or {}

                status = fixture.get("status") or {}

                event = {

                    "event_id": fixture.get("id"),

                    "home_team":
                        home.get("name", "?"),

                    "away_team":
                        away.get("name", "?"),

                    "home_team_id":
                        home.get("id"),

                    "away_team_id":
                        away.get("id"),

                    "tournament":
                        league.get("name", ""),

                    "league_id":
                        league.get("id"),

                    "league_country":
                        league.get("country", ""),

                    "season":
                        league.get("season"),

                    "round":
                        league.get("round", ""),

                    "start_time":
                        fixture.get("date", ""),

                    "timestamp":
                        fixture.get("timestamp"),

                    "status":
                        status.get("long", ""),

                    "status_short":
                        status.get("short", ""),

                    "venue":
                        _safe_get(
                            fixture,
                            "venue",
                            "name",
                            default=""
                        ),

                    "referee":
                        fixture.get("referee"),

                    "raw":
                        fx
                }

                events.append(event)

            except Exception as e:

                print(
                    f"Erro ao processar fixture: {e}"
                )

                continue

        self.last_events = events

        print(
            f"✅ {len(events)} jogos encontrados "
            f"para {date_str}"
        )

        return events

    # ========================================================
    # PESQUAR JOGO ENTRE DUAS EQUIPAS
    # ========================================================

    def pesquisar_jogo(
        self,
        equipa_casa: str,
        equipa_fora: str,
        dias: int = 7
    ) -> Optional[Dict]:

        if not equipa_casa or not equipa_fora:
            return None

        casa = equipa_casa.lower().strip()
        fora = equipa_fora.lower().strip()

        from datetime import timedelta

        hoje = datetime.now().date()

        for i in range(dias):

            data = (
                hoje +
                timedelta(days=i)
            ).strftime("%Y-%m-%d")

            eventos = self.get_scheduled_events(data)

            for ev in eventos:

                home = ev["home_team"].lower().strip()
                away = ev["away_team"].lower().strip()

                if (
                    casa in home
                    and
                    fora in away
                ):

                    print(
                        f"✅ Jogo encontrado: "
                        f"{ev['home_team']} vs "
                        f"{ev['away_team']}"
                    )

                    return ev

        print(
            f"❌ Jogo não encontrado: "
            f"{equipa_casa} vs {equipa_fora}"
        )

        return None

    # ========================================================
    # PESQUISAR EQUIPA
    # ========================================================

    def pesquisar_equipa(
        self,
        nome: str
    ) -> List[Dict]:

        if not nome:
            return []

        data = _get(
            "/teams",
            {
                "search": nome
            }
        )

        if not data:
            return []

        resultados = []

        for item in data.get("response", []):

            team = item.get("team", {})

            resultados.append({

                "id":
                    team.get("id"),

                "name":
                    team.get("name"),

                "country":
                    team.get("country"),

                "logo":
                    team.get("logo")
            })

        return resultados

    # ========================================================
    # DETALHES DO EVENTO
    # ========================================================

    def get_event_details(
        self,
        event_id: str
    ) -> Optional[Dict]:

        for ev in self.last_events:

            if str(ev["event_id"]) == str(event_id):

                return ev["raw"]

        # Se não estiver no cache, consulta diretamente

        data = _get(
            "/fixtures",
            {
                "id": event_id
            }
        )

        if not data:
            return None

        response = data.get("response", [])

        if response:
            return response[0]

        return None

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    def get_event_statistics(
        self,
        event_id: str
    ) -> Optional[Dict]:

        data = _get(
            "/fixtures/statistics",
            {
                "fixture": event_id
            }
        )

        if not data:
            return None

        return data

    # ========================================================
    # ESCALAÇÕES
    # ========================================================

    def get_event_lineups(
        self,
        event_id: str
    ) -> Optional[Dict]:

        data = _get(
            "/fixtures/lineups",
            {
                "fixture": event_id
            }
        )

        if not data:
            return None

        return data

    # ========================================================
    # ODDS
    # ========================================================

    def get_event_odds(
        self,
        event_id: str
    ) -> Optional[Dict]:

        data = _get(
            "/odds",
            {
                "fixture": event_id
            }
        )

        if not data:
            return None

        return data

    # ========================================================
    # CLASSIFICAÇÃO
    # ========================================================

    def get_tournament_standings(
        self,
        league_id: str,
        season: str
    ) -> Optional[Dict]:

        if not league_id or not season:
            return None

        return _get(
            "/standings",
            {
                "league": league_id,
                "season": season
            }
        )

    # ========================================================
    # POSIÇÃO DA EQUIPA
    # ========================================================

    def get_team_position(
        self,
        team_id: str,
        league_id: str,
        season: str
    ) -> Optional[int]:

        data = self.get_tournament_standings(
            league_id,
            season
        )

        if not data:
            return None

        try:

            response = data.get(
                "response",
                []
            )

            for league_data in response:

                standings = (
                    league_data
                    .get("league", {})
                    .get("standings", [])
                )

                for grupo in standings:

                    for team_data in grupo:

                        team = team_data.get(
                            "team",
                            {}
                        )

                        if str(team.get("id")) == str(team_id):

                            return team_data.get(
                                "rank"
                            )

        except Exception as e:

            print(
                f"Erro ao obter classificação: {e}"
            )

        return None

    # ========================================================
    # ÚLTIMOS JOGOS DA EQUIPA
    # ========================================================

    def get_team_recent_matches(
        self,
        team_id: str,
        num_matches: int = 5
    ) -> List[Dict]:

        if not team_id:
            return []

        data = _get(
            "/fixtures",
            {
                "team": team_id,
                "last": num_matches
            }
        )

        if not data:
            return []

        fixtures = data.get(
            "response",
            []
        )

        played = []

        for fx in fixtures:

            try:

                fixture = fx.get(
                    "fixture",
                    {}
                )

                status = fixture.get(
                    "status",
                    {}
                )

                # Apenas jogos terminados

                if status.get("short") not in [
                    "FT",
                    "AET",
                    "PEN"
                ]:
                    continue

                goals = fx.get(
                    "goals",
                    {}
                )

                home_goals = goals.get(
                    "home"
                )

                away_goals = goals.get(
                    "away"
                )

                if (
                    home_goals is None
                    or
                    away_goals is None
                ):
                    continue

                teams = fx.get(
                    "teams",
                    {}
                )

                home = teams.get(
                    "home",
                    {}
                )

                away = teams.get(
                    "away",
                    {}
                )

                home_id = home.get(
                    "id"
                )

                away_id = away.get(
                    "id"
                )

                if str(home_id) == str(team_id):

                    golos_marcados = int(
                        home_goals
                    )

                    golos_sofridos = int(
                        away_goals
                    )

                    adversario = away.get(
                        "name",
                        "?"
                    )

                    casa = True

                elif str(away_id) == str(team_id):

                    golos_marcados = int(
                        away_goals
                    )

                    golos_sofridos = int(
                        home_goals
                    )

                    adversario = home.get(
                        "name",
                        "?"
                    )

                    casa = False

                else:
                    continue

                played.append({

                    "golos_marcados":
                        golos_marcados,

                    "golos_sofridos":
                        golos_sofridos,

                    "adversario":
                        adversario,

                    "data":
                        fixture.get(
                            "date",
                            ""
                        ),

                    "casa":
                        casa,

                    "resultado":
                        (
                            "V"
                            if golos_marcados > golos_sofridos
                            else
                            "E"
                            if golos_marcados == golos_sofridos
                            else
                            "D"
                        )
                })

            except Exception as e:

                print(
                    f"Erro ao processar jogo recente: {e}"
                )

                continue

        return played[:num_matches]

    # ========================================================
    # EXTRAIR ESTATÍSTICAS DE CANTOS E CARTÕES
    # ========================================================

    def extrair_estatisticas(
        self,
        event_id: str
    ) -> Dict:

        resultado = {

            "cantos_casa": None,
            "cantos_fora": None,

            "cartoes_casa": None,
            "cartoes_fora": None
        }

        data = self.get_event_statistics(
            event_id
        )

        if not data:
            return resultado

        try:

            equipes = data.get(
                "response",
                []
            )

            for equipe in equipes:

                team_name = _safe_get(
                    equipe,
                    "team",
                    "name",
                    default=""
                )

                statistics = equipe.get(
                    "statistics",
                    []
                )

                valores = {}

                for stat in statistics:

                    tipo = stat.get(
                        "type",
                        ""
                    )

                    valor = stat.get(
                        "value"
                    )

                    valores[tipo] = valor

                # Estes valores são usados
                # apenas se disponíveis.

                corners = valores.get(
                    "Corner Kicks"
                )

                yellow = valores.get(
                    "Yellow Cards"
                )

                # A identificação casa/fora
                # será feita pelo nome do evento.

                evento = self.get_event_details(
                    event_id
                )

                if not evento:
                    continue

                home_name = _safe_get(
                    evento,
                    "teams",
                    "home",
                    "name",
                    default=""
                )

                if team_name == home_name:

                    resultado[
                        "cantos_casa"
                    ] = self._numero(
                        corners
                    )

                    resultado[
                        "cartoes_casa"
                    ] = self._numero(
                        yellow
                    )

                else:

                    resultado[
                        "cantos_fora"
                    ] = self._numero(
                        corners
                    )

                    resultado[
                        "cartoes_fora"
                    ] = self._numero(
                        yellow
                    )

        except Exception as e:

            print(
                f"Erro estatísticas: {e}"
            )

        return resultado

    # ========================================================
    # CONVERTER NÚMERO
    # ========================================================

    @staticmethod
    def _numero(valor):

        if valor is None:
            return None

        try:

            if isinstance(valor, str):

                valor = (
                    valor
                    .replace("%", "")
                    .strip()
                )

            return float(valor)

        except Exception:

            return None

    # ========================================================
    # PREPARAR DADOS PARA IA
    # ========================================================

    def prepare_match_data(
        self,
        event_id: str
    ) -> Optional[Dict]:

        evento = None

        # ----------------------------------------------------
        # Procurar no cache
        # ----------------------------------------------------

        for ev in self.last_events:

            if str(ev["event_id"]) == str(event_id):

                evento = ev

                break

        # ----------------------------------------------------
        # Se não encontrar, buscar API
        # ----------------------------------------------------

        if not evento:

            raw = self.get_event_details(
                event_id
            )

            if not raw:

                print(
                    f"❌ Evento {event_id} não encontrado."
                )

                return None

            teams = raw.get(
                "teams",
                {}
            )

            league = raw.get(
                "league",
                {}
            )

            fixture = raw.get(
                "fixture",
                {}
            )

            evento = {

                "event_id":
                    event_id,

                "home_team":
                    _safe_get(
                        teams,
                        "home",
                        "name",
                        default="?"
                    ),

                "away_team":
                    _safe_get(
                        teams,
                        "away",
                        "name",
                        default="?"
                    ),

                "home_team_id":
                    _safe_get(
                        teams,
                        "home",
                        "id"
                    ),

                "away_team_id":
                    _safe_get(
                        teams,
                        "away",
                        "id"
                    ),

                "league_id":
                    league.get("id"),

                "season":
                    league.get("season"),

                "raw":
                    raw,

                "start_time":
                    fixture.get("date")
            }

        home_id = evento.get(
            "home_team_id"
        )

        away_id = evento.get(
            "away_team_id"
        )

        league_id = evento.get(
            "league_id"
        )

        season = evento.get(
            "season"
        )

        # ----------------------------------------------------
        # Estrutura inicial
        # ----------------------------------------------------

        match_data = {

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

            "data":
                datetime.now().strftime(
                    "%Y-%m-%d"
                ),

            "forma_casa": [],
            "forma_fora": [],

            "golos_casa": [],
            "golos_fora": [],

            "golos_sofridos_casa": [],
            "golos_sofridos_fora": [],

            "posicao_casa": None,
            "posicao_fora": None,

            # Valores padrão.
            # Serão substituídos se
            # houver dados reais.

            "media_cantos_casa": 4.5,
            "media_cantos_fora": 4.0,

            "media_cartoes_casa": 2.0,
            "media_cartoes_fora": 2.0,

            "odds": {}
        }

        # ====================================================
        # FORMA CASA
        # ====================================================

        if home_id:

            try:

                ultimos_casa = (
                    self.get_team_recent_matches(
                        home_id,
                        5
                    )
                )

                match_data[
                    "forma_casa"
                ] = ultimos_casa

                match_data[
                    "golos_casa"
                ] = [
                    j["golos_marcados"]
                    for j in ultimos_casa
                ]

                match_data[
                    "golos_sofridos_casa"
                ] = [
                    j["golos_sofridos"]
                    for j in ultimos_casa
                ]

            except Exception as e:

                print(
                    f"Erro forma casa: {e}"
                )

        # ====================================================
        # FORMA FORA
        # ====================================================

        if away_id:

            try:

                ultimos_fora = (
                    self.get_team_recent_matches(
                        away_id,
                        5
                    )
                )

                match_data[
                    "forma_fora"
                ] = ultimos_fora

                match_data[
                    "golos_fora"
                ] = [
                    j["golos_marcados"]
                    for j in ultimos_fora
                ]

                match_data[
                    "golos_sofridos_fora"
                ] = [
                    j["golos_sofridos"]
                    for j in ultimos_fora
                ]

            except Exception as e:

                print(
                    f"Erro forma fora: {e}"
                )

        # ====================================================
        # CLASSIFICAÇÃO
        # ====================================================

        if league_id and season:

            try:

                match_data[
                    "posicao_casa"
                ] = self.get_team_position(
                    home_id,
                    league_id,
                    season
                )

                match_data[
                    "posicao_fora"
                ] = self.get_team_position(
                    away_id,
                    league_id,
                    season
                )

            except Exception as e:

                print(
                    f"Erro classificação: {e}"
                )

        # ====================================================
        # ODDS
        # ====================================================

        try:

            odds_data = self.get_event_odds(
                event_id
            )

            if odds_data:

                match_data[
                    "odds"
                ] = self.processar_odds(
                    odds_data
                )

        except Exception as e:

            print(
                f"Erro odds: {e}"
            )

        # ====================================================
        # ESTATÍSTICAS
        # ====================================================

        try:

            estatisticas = (
                self.extrair_estatisticas(
                    event_id
                )
            )

            if estatisticas.get(
                "cantos_casa"
            ) is not None:

                match_data[
                    "media_cantos_casa"
                ] = estatisticas[
                    "cantos_casa"
                ]

            if estatisticas.get(
                "cantos_fora"
            ) is not None:

                match_data[
                    "media_cantos_fora"
                ] = estatisticas[
                    "cantos_fora"
                ]

            if estatisticas.get(
                "cartoes_casa"
            ) is not None:

                match_data[
                    "media_cartoes_casa"
                ] = estatisticas[
                    "cartoes_casa"
                ]

            if estatisticas.get(
                "cartoes_fora"
            ) is not None:

                match_data[
                    "media_cartoes_fora"
                ] = estatisticas[
                    "cartoes_fora"
                ]

        except Exception as e:

            print(
                f"Erro ao obter estatísticas: {e}"
            )

        return match_data

    # ========================================================
    # PROCESSAR ODDS
    # ========================================================

    def processar_odds(
        self,
        data: Dict
    ) -> Dict:

        odds = {}

        try:

            responses = data.get(
                "response",
                []
            )

            for bookmaker_data in responses:

                bookmakers = bookmaker_data.get(
                    "bookmakers",
                    []
                )

                for bookmaker in bookmakers:

                    bets = bookmaker.get(
                        "bets",
                        []
                    )

                    for bet in bets:

                        bet_name = (
                            bet.get(
                                "name",
                                ""
                            )
                            .lower()
                        )

                        values = bet.get(
                            "values",
                            []
                        )

                        for value in values:

                            nome = (
                                value.get(
                                    "value",
                                    ""
                                )
                                .lower()
                            )

                            odd = value.get(
                                "odd"
                            )

                            try:

                                odd = float(
                                    odd
                                )

                            except Exception:

                                continue

                            # --------------------------------
                            # 1X2
                            # --------------------------------

                            if (
                                "match winner"
                                in bet_name
                                or
                                "winner"
                                in bet_name
                            ):

                                if nome in [
                                    "home",
                                    "1"
                                ]:

                                    odds.setdefault(
                                        "1x2",
                                        {}
                                    )["casa"] = odd

                                elif nome in [
                                    "draw",
                                    "x"
                                ]:

                                    odds.setdefault(
                                        "1x2",
                                        {}
                                    )["empate"] = odd

                                elif nome in [
                                    "away",
                                    "2"
                                ]:

                                    odds.setdefault(
                                        "1x2",
                                        {}
                                    )["fora"] = odd

                            # --------------------------------
                            # OVER/UNDER
                            # --------------------------------

                            if (
                                "goals over/under"
                                in bet_name
                            ):

                                if (
                                    "over 1.5"
                                    in nome
                                ):

                                    odds[
                                        "over_1_5"
                                    ] = odd

                                elif (
                                    "over 2.5"
                                    in nome
                                ):

                                    odds[
                                        "over_2_5"
                                    ] = odd

                            # --------------------------------
                            # BTTS
                            # --------------------------------

                            if (
                                "both teams"
                                in bet_name
                                or
                                "both teams to score"
                                in bet_name
                            ):

                                if nome == "yes":

                                    odds[
                                        "btts"
                                    ] = odd

        except Exception as e:

            print(
                f"Erro ao processar odds: {e}"
            )

        return odds


# ============================================================
# TESTE DIRETO
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("⚽ FOOTBALLAI - TESTE API-FOOTBALL")
    print("=" * 60)

    if not API_KEY:

        print()
        print(
            "❌ API_FOOTBALL_KEY não configurada."
        )
        print()
        print(
            "Cria um arquivo .env com:"
        )
        print()
        print(
            "API_FOOTBALL_KEY=TUA_CHAVE_AQUI"
        )
        print()

    else:

        api = APIFootballAPI()

        print()
        print("🔑 API Key encontrada.")
        print()

        hoje = datetime.now().strftime(
            "%Y-%m-%d"
        )

        print(
            f"📅 Procurando jogos de {hoje}..."
        )

        eventos = api.get_scheduled_events(
            hoje
        )

        print()
        print(
            f"⚽ Jogos encontrados: "
            f"{len(eventos)}"
        )

        for ev in eventos[:10]:

            print(
                f"- "
                f"{ev['home_team']} "
                f"vs "
                f"{ev['away_team']} "
                f"| "
                f"{ev['tournament']} "
                f"| "
                f"{ev['start_time']}"
            )

        print()
        print("=" * 60)
