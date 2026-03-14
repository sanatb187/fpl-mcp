from __future__ import annotations

from typing import Any

import httpx

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"

_BOOTSTRAP_CACHE: dict[str, Any] | None = None
_FIXTURES_CACHE: list[dict[str, Any]] | None = None


async def _get_json(url: str) -> Any:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


async def fetch_bootstrap() -> dict[str, Any]:
    global _BOOTSTRAP_CACHE
    if _BOOTSTRAP_CACHE is None:
        _BOOTSTRAP_CACHE = await _get_json(BOOTSTRAP_URL)
    return _BOOTSTRAP_CACHE


async def fetch_fixtures() -> list[dict[str, Any]]:
    global _FIXTURES_CACHE
    if _FIXTURES_CACHE is None:
        _FIXTURES_CACHE = await _get_json(FIXTURES_URL)
    return _FIXTURES_CACHE


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


async def search_team(team_name: str) -> dict[str, Any]:
    data = await fetch_bootstrap()
    teams = data["teams"]
    query = team_name.strip().lower()

    def score(team: dict[str, Any]) -> tuple[int, str]:
        name = team["name"].lower()
        short = team["short_name"].lower()

        if query == name:
            return (0, name)
        if query == short:
            return (1, name)
        if name.startswith(query):
            return (2, name)
        if query in name:
            return (3, name)
        return (999, name)

    ranked = sorted((team for team in teams if score(team)[0] < 999), key=score)
    if not ranked:
        raise ValueError(f"No team found for: {team_name}")

    best = ranked[0]
    return {
        "team_id": best["id"],
        "team_name": best["name"],
        "team_short_name": best["short_name"],
        "strength": best.get("strength"),
    }


async def get_team_last_fixtures(team_id: int, last_n: int = 5) -> list[dict[str, Any]]:
    fixtures = await fetch_fixtures()

    played = [
        fixture
        for fixture in fixtures
        if fixture.get("finished") is True
        and (fixture["team_h"] == team_id or fixture["team_a"] == team_id)
    ]

    played_sorted = sorted(
        played,
        key=lambda fixture: (
            fixture.get("kickoff_time") or "",
            fixture.get("event") or 0,
            fixture.get("id") or 0,
        ),
        reverse=True,
    )

    return played_sorted[:last_n]

async def get_team_next_fixtures(team_name: str, next_n: int = 5) -> dict:
    fixtures = await fetch_fixtures()
    bootstrap = await fetch_bootstrap()

    team = await search_team(team_name)
    team_id = team["team_id"]
    team_map = {t["id"]: t["name"] for t in bootstrap["teams"]}

    upcoming = [
        fixture
        for fixture in fixtures
        if fixture.get("finished") is False
        and fixture.get("kickoff_time") is not None
        and (fixture["team_h"] == team_id or fixture["team_a"] == team_id)
    ]

    upcoming_sorted = sorted(
        upcoming,
        key=lambda fixture: (
            fixture["kickoff_time"],
            fixture.get("event") or 0,
            fixture.get("id") or 0,
        ),
    )[:next_n]

    matches = []
    difficulties = []

    for fixture in upcoming_sorted:
        is_home = fixture["team_h"] == team_id
        opponent_id = fixture["team_a"] if is_home else fixture["team_h"]
        opponent_name = team_map.get(opponent_id, "Unknown")
        difficulty = fixture["team_h_difficulty"] if is_home else fixture["team_a_difficulty"]
        difficulties.append(difficulty)

        matches.append(
            {
                "fixture_id": fixture["id"],
                "gameweek": fixture.get("event"),
                "kickoff_time": fixture.get("kickoff_time"),
                "home_or_away": "home" if is_home else "away",
                "opponent": opponent_name,
                "difficulty": difficulty,
            }
        )

    avg_difficulty = round(sum(difficulties) / len(difficulties), 2) if difficulties else None

    return {
        "team": team["team_name"],
        "next_n": len(matches),
        "fixtures": matches,
        "summary": {
            "average_difficulty": avg_difficulty,
        },
    }
async def get_team_recent_form(team_name: str, last_n: int = 5) -> dict[str, Any]:
    bootstrap = await fetch_bootstrap()
    team = await search_team(team_name)
    team_map = {t["id"]: t["name"] for t in bootstrap["teams"]}

    fixtures = await get_team_last_fixtures(team["team_id"], last_n=last_n)

    matches: list[dict[str, Any]] = []
    wins = 0
    draws = 0
    losses = 0
    goals_for_total = 0
    goals_against_total = 0
    clean_sheets = 0

    for fixture in fixtures:
        is_home = fixture["team_h"] == team["team_id"]
        opponent_id = fixture["team_a"] if is_home else fixture["team_h"]
        opponent_name = team_map.get(opponent_id, "Unknown")

        goals_for = _safe_int(fixture["team_h_score"] if is_home else fixture["team_a_score"])
        goals_against = _safe_int(fixture["team_a_score"] if is_home else fixture["team_h_score"])

        if goals_for > goals_against:
            result = "W"
            wins += 1
        elif goals_for < goals_against:
            result = "L"
            losses += 1
        else:
            result = "D"
            draws += 1

        if goals_against == 0:
            clean_sheets += 1

        goals_for_total += goals_for
        goals_against_total += goals_against

        matches.append(
            {
                "fixture_id": fixture["id"],
                "gameweek": fixture.get("event"),
                "kickoff_time": fixture.get("kickoff_time"),
                "home_or_away": "home" if is_home else "away",
                "team": team["team_name"],
                "opponent": opponent_name,
                "goals_for": goals_for,
                "goals_against": goals_against,
                "result": result,
            }
        )

    return {
        "team": team["team_name"],
        "last_n": len(matches),
        "matches": matches,
        "summary": {
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for_total,
            "goals_against": goals_against_total,
            "clean_sheets": clean_sheets,
        },
    }


async def get_head_to_head(team_a: str, team_b: str, last_n: int = 5) -> dict[str, Any]:
    bootstrap = await fetch_bootstrap()
    fixtures = await fetch_fixtures()

    team_a_resolved = await search_team(team_a)
    team_b_resolved = await search_team(team_b)

    team_map = {t["id"]: t["name"] for t in bootstrap["teams"]}

    h2h = [
        fixture
        for fixture in fixtures
        if fixture.get("finished") is True
        and {
            fixture["team_h"],
            fixture["team_a"],
        }
        == {team_a_resolved["team_id"], team_b_resolved["team_id"]}
    ]

    h2h_sorted = sorted(
        h2h,
        key=lambda fixture: (
            fixture.get("kickoff_time") or "",
            fixture.get("event") or 0,
            fixture.get("id") or 0,
        ),
        reverse=True,
    )[:last_n]

    matches: list[dict[str, Any]] = []
    team_a_wins = 0
    team_b_wins = 0
    draws = 0

    for fixture in h2h_sorted:
        home_team = team_map.get(fixture["team_h"], "Unknown")
        away_team = team_map.get(fixture["team_a"], "Unknown")
        home_goals = _safe_int(fixture["team_h_score"])
        away_goals = _safe_int(fixture["team_a_score"])

        if home_goals > away_goals:
            winner = home_team
        elif away_goals > home_goals:
            winner = away_team
        else:
            winner = "Draw"

        if winner == team_a_resolved["team_name"]:
            team_a_wins += 1
        elif winner == team_b_resolved["team_name"]:
            team_b_wins += 1
        else:
            draws += 1

        matches.append(
            {
                "fixture_id": fixture["id"],
                "gameweek": fixture.get("event"),
                "kickoff_time": fixture.get("kickoff_time"),
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "winner": winner,
            }
        )

    return {
        "team_a": team_a_resolved["team_name"],
        "team_b": team_b_resolved["team_name"],
        "last_n": len(matches),
        "matches": matches,
        "summary": {
            "team_a_wins": team_a_wins,
            "team_b_wins": team_b_wins,
            "draws": draws,
        },
    }