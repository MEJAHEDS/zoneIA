# ZoneAI — Analyse de zone de chalandise par IA

> Mini Map Analytix powered by Claude AI · Portfolio project

## Demo

Entrez une adresse + type d'établissement → Claude analyse automatiquement la zone et génère un rapport stratégique.

**Stack :** FastAPI · Python · Claude Opus 4.6 (Anthropic) · OpenStreetMap · API Gouv · Leaflet.js

## Architecture

```
User Input (adresse + type)
        ↓
FastAPI /analyze
        ↓
Claude Agent (claude-opus-4-6 + tool use)
    ├── geocode_address()     → Nominatim OSM
    ├── get_commune_info()    → api.gouv.fr
    ├── get_isochrone_estimate()
    └── get_competitors()     → Overpass API OSM
        ↓
Rapport stratégique Markdown
        ↓
Dashboard interactif (Leaflet map + stats)
```

## Lancer le projet

```bash
# 1. Cloner et installer les dépendances
pip install -r requirements.txt

# 2. Configurer la clé API
cp .env.example .env
# Ajouter votre ANTHROPIC_API_KEY dans .env

# 3. Lancer le serveur
uvicorn main:app --reload

# 4. Ouvrir http://localhost:8000
```

## API

### POST /analyze

```json
{
  "address": "10 rue de Rivoli, Paris",
  "business_type": "restaurant"
}
```

**Réponse :**
```json
{
  "address": "...",
  "business_type": "...",
  "geo": { "lat": 48.85, "lon": 2.35 },
  "report": "## Rapport stratégique\n...",
  "tool_calls": [...]
}
```

## Ce que Claude fait

1. **Géocode** l'adresse
2. **Récupère** les données démographiques INSEE (population, densité)
3. **Estime** la zone de chalandise (isochrone 10 minutes)
4. **Analyse** la concurrence dans la zone (catégorie adaptée au type d'établissement)
5. **Génère** un rapport Markdown avec score d'attractivité et recommandations
# zoneIA
