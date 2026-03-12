from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from fpl_mcp.fpl_api import find_player, get_players
from fpl_mcp.official_fpl_fixtures import get_head_to_head, get_team_recent_form

mcp = FastMCP("fpl-mcp")


@mcp.tool()
async def get_players_tool(
    position: str,
    limit: int = 10,
    sort_by: str = "form",
    max_selected_percent: float | None = None,
    max_cost: float | None = None,
) -> dict:
    """
    Return Fantasy Premier League players for a position.

    Supported positions:
    - GK, goalkeeper
    - DEF, defender
    - MID, midfielder
    - FWD, forward

    Supported sort_by values:
    - form
    - total_points
    - cost
    - points_per_game
    - selected_by_percent
    - minutes

    Optional filters:
    - max_selected_percent: use this to find differentials
    - max_cost: maximum FPL price
    """
    try:
        players = await get_players(
            position=position,
            limit=limit,
            sort_by=sort_by,
            max_selected_percent=max_selected_percent,
            max_cost=max_cost,
        )
        return {
            "ok": True,
            "position": position,
            "count": len(players),
            "sort_by": sort_by,
            "max_selected_percent": max_selected_percent,
            "max_cost": max_cost,
            "players": players,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
async def find_player_tool(name: str) -> dict:
    """
    Search Fantasy Premier League players by name.
    """
    try:
        players = await find_player(name=name)
        return {
            "ok": True,
            "query": name,
            "count": len(players),
            "players": players,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
async def get_team_recent_form_tool(
    team_name: str,
    last_n: int = 5,
) -> dict:
    """
    Return a Premier League team's recent form using official FPL fixture results.

    This tool uses finished fixtures from the official FPL dataset for the
    current season and is intended for recent form analysis, such as the last
    5 finished league matches.
    """
    try:
        result = await get_team_recent_form(
            team_name=team_name,
            last_n=last_n,
        )
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@mcp.tool()
async def get_recent_head_to_head_tool(
    team_a: str,
    team_b: str,
    last_n: int = 5,
) -> dict:
    """
    Return recent finished Premier League meetings between two teams using
    official FPL fixture results.

    This tool uses only fixtures available in the official FPL dataset and is
    best for recent same-season comparisons. It returns up to the requested
    number of finished meetings, but it does not guarantee full multi-season
    historical head-to-head coverage.
    """
    try:
        result = await get_head_to_head(
            team_a=team_a,
            team_b=team_b,
            last_n=last_n,
        )
        return {"ok": True, **result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    mcp.run()