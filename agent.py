"""
Claude AI Agent — Zone Analysis
Uses claude-opus-4-6 with tool use to analyze a location
and generate a strategic report, just like Vectorive's Map Analytix.
"""
import json
import anthropic
from tools import geocode_address, get_competitors, get_commune_info, get_isochrone_estimate

client = anthropic.Anthropic()

# ── Tool definitions for Claude ────────────────────────────────────────────────

TOOLS = [
    {
        "name": "geocode_address",
        "description": "Géocode une adresse française et retourne les coordonnées GPS (lat/lon), le nom de commune et les infos administratives.",
        "input_schema": {
            "type": "object",
            "properties": {
                "address": {"type": "string", "description": "Adresse complète à géocoder (ex: '10 rue de Rivoli, Paris')"}
            },
            "required": ["address"],
        },
    },
    {
        "name": "get_commune_info",
        "description": "Récupère les données démographiques officielles de la commune : population, surface, densité, code INSEE. Utilise les coordonnées GPS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude GPS"},
                "lon": {"type": "number", "description": "Longitude GPS"},
            },
            "required": ["lat", "lon"],
        },
    },
    {
        "name": "get_competitors",
        "description": "Recherche les établissements concurrents ou points d'intérêt dans un rayon donné autour d'un point GPS. Utilise OpenStreetMap.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Latitude GPS"},
                "lon": {"type": "number", "description": "Longitude GPS"},
                "radius_m": {"type": "integer", "description": "Rayon de recherche en mètres (ex: 500, 1000, 2000)"},
                "category": {
                    "type": "string",
                    "description": "Catégorie à rechercher",
                    "enum": ["restaurant", "pharmacy", "supermarket", "bank", "cafe", "gym", "school", "hotel", "bakery"],
                },
            },
            "required": ["lat", "lon", "radius_m", "category"],
        },
    },
    {
        "name": "get_isochrone_estimate",
        "description": "Estime le rayon de zone de chalandise en fonction d'un temps de trajet (en minutes). Retourne les rayons à pied et en voiture.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "minutes": {"type": "integer", "description": "Temps de trajet en minutes (ex: 5, 10, 15, 30)"},
            },
            "required": ["lat", "lon", "minutes"],
        },
    },
]

SYSTEM_PROMPT = """Tu es ZoneAI, un expert en analyse géospatiale et stratégie d'implantation commerciale.
Tu analyses des emplacements pour aider les entreprises à prendre des décisions d'implantation éclairées.

Ton processus :
1. Géocode d'abord l'adresse pour obtenir les coordonnées
2. Récupère les données démographiques de la commune
3. Estime la zone de chalandise (isochrone 10 minutes)
4. Analyse la concurrence dans la zone (utilise les catégories pertinentes selon le type d'établissement)
5. Génère un rapport structuré avec : résumé exécutif, données démographiques, analyse concurrentielle, score d'attractivité et recommandations

Sois précis, factuel et actionnable. Formate ton rapport final en Markdown."""


# ── Tool execution dispatcher ──────────────────────────────────────────────────

async def execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "geocode_address":
            result = await geocode_address(**inputs)
        elif name == "get_commune_info":
            result = await get_commune_info(**inputs)
        elif name == "get_competitors":
            result = await get_competitors(**inputs)
        elif name == "get_isochrone_estimate":
            result = await get_isochrone_estimate(**inputs)
        else:
            result = {"error": f"Outil inconnu : {name}"}
    except Exception as e:
        result = {"error": str(e)}

    return json.dumps(result, ensure_ascii=False)


# ── Main agent function ────────────────────────────────────────────────────────

async def analyze_location(address: str, business_type: str) -> dict:
    """
    Run the Claude agent to analyze a location for a given business type.
    Returns the full report + intermediate tool calls for transparency.
    """
    messages = [
        {
            "role": "user",
            "content": (
                f"Analyse l'emplacement suivant pour l'implantation d'un(e) **{business_type}** :\n\n"
                f"**Adresse :** {address}\n\n"
                f"Génère une analyse complète de zone de chalandise avec tes outils, "
                f"puis rédige un rapport stratégique détaillé."
            ),
        }
    ]

    tool_calls_log = []
    final_report = ""
    geo_data = {}

    # ── Agentic loop ───────────────────────────────────────────────────────────
    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Append assistant response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract final text report
            for block in response.content:
                if block.type == "text":
                    final_report = block.text
            break

        if response.stop_reason != "tool_use":
            break

        # Execute all tool calls
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_input = block.input
            result_str = await execute_tool(block.name, tool_input)
            result_data = json.loads(result_str)

            # Capture geo coordinates from geocode result
            if block.name == "geocode_address" and "lat" in result_data:
                geo_data = result_data

            tool_calls_log.append({
                "tool": block.name,
                "input": tool_input,
                "result": result_data,
            })

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})

    return {
        "address": address,
        "business_type": business_type,
        "geo": geo_data,
        "report": final_report,
        "tool_calls": tool_calls_log,
    }
