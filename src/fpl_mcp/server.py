from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from fpl_mcp.fpl_api import find_player, get_players

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

    Optional filters (Use only if query demands it):
    - max_selected_percent: Can be used to handle user queries like "differential" (< = 10 percent), or most common (>80 percent)
      Example: 10.0 means only players selected by 10 percent or fewer managers
    - max_cost: maximum player price in FPL

    Examples:
    - Top 5 midfielders by form:
      position='MID', limit=5, sort_by='form'

    - Differential midfielders by cost:
      position='midfielder', sort_by='cost', max_selected_percent=10.0

    - Cheap forwards:
      position='forward', max_cost=6.5, sort_by='form'
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
        return {
            "ok": False,
            "error": str(exc),
        }


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
        return {
            "ok": False,
            "error": str(exc),
        }


if __name__ == "__main__":
    mcp.run()