from __future__ import annotations

from typing import Any

import httpx

BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

POSITION_MAP = {
    "GK": 1,
    "DEF": 2,
    "MID": 3,
    "FWD": 4,
}

POSITION_ALIASES = {
    "GK": "GK",
    "GOALKEEPER": "GK",
    "GOALKEEPERS": "GK",
    "DEF": "DEF",
    "DEFENDER": "DEF",
    "DEFENDERS": "DEF",
    "MID": "MID",
    "MIDFIELDER": "MID",
    "MIDFIELDERS": "MID",
    "FWD": "FWD",
    "FORWARD": "FWD",
    "FORWARDS": "FWD",
    "STRIKER": "FWD",
    "STRIKERS": "FWD",
}


async def fetch_bootstrap() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(BOOTSTRAP_URL)
        response.raise_for_status()
        return response.json()


def _team_lookup(data: dict[str, Any]) -> dict[int, str]:
    return {team["id"]: team["name"] for team in data["teams"]}


def _normalize_position(position: str) -> str:
    normalized = position.upper().strip()
    mapped = POSITION_ALIASES.get(normalized)
    if mapped is None:
        raise ValueError(
            "position must be one of: GK, DEF, MID, FWD "
            "(or goalkeeper, defender, midfielder, forward)"
        )
    return mapped


def _position_id(position: str) -> int:
    return POSITION_MAP[_normalize_position(position)]


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _player_payload(player: dict[str, Any], team_map: dict[int, str], position: str) -> dict[str, Any]:
    return {
        "name": f'{player["first_name"]} {player["second_name"]}',
        "team": team_map.get(player["team"], "Unknown"),
        "position": position,
        "cost": (player.get("now_cost", 0) or 0) / 10.0,
        "total_points": player.get("total_points"),
        "form": _safe_float(player.get("form")),
        "points_per_game": _safe_float(player.get("points_per_game")),
        "selected_by_percent": _safe_float(player.get("selected_by_percent")),
        "minutes": player.get("minutes"),
        "goals_scored": player.get("goals_scored"),
        "assists": player.get("assists"),
        "clean_sheets": player.get("clean_sheets"),
    }


def _sort_key(sort_by: str) -> str:
    allowed = {
        "form",
        "total_points",
        "cost",
        "points_per_game",
        "selected_by_percent",
        "minutes",
    }
    normalized = sort_by.strip().lower()
    if normalized not in allowed:
        raise ValueError(
            "sort_by must be one of: "
            "form, total_points, cost, points_per_game, selected_by_percent, minutes"
        )
    return normalized


async def get_players(
    position: str,
    limit: int = 10,
    sort_by: str = "form",
    max_selected_percent: float | None = None,
    max_cost: float | None = None,
) -> list[dict[str, Any]]:
    data = await fetch_bootstrap()
    team_map = _team_lookup(data)

    normalized_position = _normalize_position(position)
    pos_id = _position_id(position)
    sort_field = _sort_key(sort_by)

    players = [player for player in data["elements"] if player["element_type"] == pos_id]

    payload = [_player_payload(player, team_map, normalized_position) for player in players]

    if max_selected_percent is not None:
        payload = [
            player
            for player in payload
            if player["selected_by_percent"] <= max_selected_percent
        ]

    if max_cost is not None:
        payload = [player for player in payload if player["cost"] <= max_cost]

    reverse = sort_field != "cost"
    payload_sorted = sorted(
        payload,
        key=lambda player: player.get(sort_field, 0) or 0,
        reverse=reverse,
    )

    return payload_sorted[:limit]


async def find_player(name: str, limit: int = 10) -> list[dict[str, Any]]:
    data = await fetch_bootstrap()
    team_map = _team_lookup(data)
    query = name.strip().lower()

    matches: list[dict[str, Any]] = []
    for player in data["elements"]:
        full_name = f'{player["first_name"]} {player["second_name"]}'
        if query in full_name.lower() or query in player["second_name"].lower():
            normalized_position = {
                1: "GK",
                2: "DEF",
                3: "MID",
                4: "FWD",
            }.get(player["element_type"], "UNK")
            matches.append(_player_payload(player, team_map, normalized_position))

    return matches[:limit]