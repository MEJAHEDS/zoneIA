# ZoneAI — Analyse de zone de chalandise par IA

> Agent IA autonome qui analyse n'importe quelle adresse en France et génère un rapport stratégique d'implantation commerciale · Powered by Claude Opus 4.6

![ZoneAI Demo](demo.gif)

## Ce que ça fait

Entrez une adresse + un type d'établissement → Claude orchestre automatiquement :

1. **Géocodage** de l'adresse (Nominatim / OpenStreetMap)
2. **Données démographiques** de la commune (population, densité — api.gouv.fr)
3. **Zone de chalandise** estimée (isochrone 5/10/15 min à pied et en voiture)
4. **Analyse concurrentielle** dans la zone (Overpass API / OSM)
5. **Rapport stratégique Markdown** : score d'attractivité, synthèse, recommandations

Le tout visualisé sur une carte interactive Leaflet.js avec les concurrents géolocalisés.

## Stack

```
Frontend    Leaflet.js · Vanilla JS · marked.js
Backend     FastAPI (Python) · Uvicorn
Agent IA    Claude Opus 4.6 (Anthropic) · Boucle agentique + tool use
APIs        Nominatim OSM · Overpass API · api.gouv.fr
Sécurité    Rate limiting IP (SQLite · SHA-256) · 2 analyses / 24h
```

## Architecture

```
User Input (adresse + type)
        ↓
FastAPI /analyze  ──  Rate limiter (SQLite · IP hashed SHA-256)
        ↓
Claude Agent (claude-opus-4-6 + adaptive thinking)
    ├── geocode_address()       → Nominatim OSM
    ├── get_commune_info()      → api.gouv.fr / INSEE
    ├── get_isochrone_estimate() → calcul mathématique
    └── get_competitors()       → Overpass API (OSM)
        ↓
Rapport Markdown structuré
        ↓
Dashboard Leaflet (carte · stats · rapport)
```

## Lancer en local

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer la clé API Anthropic
cp .env.example .env
# → Ajouter votre ANTHROPIC_API_KEY dans .env

# 3. Lancer
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
  "address": "10 rue de Rivoli, Paris",
  "business_type": "restaurant",
  "geo": { "lat": 48.855, "lon": 2.360 },
  "report": "## Rapport stratégique\n...",
  "tool_calls": [
    { "tool": "geocode_address", "input": {...}, "result": {...} },
    { "tool": "get_commune_info", "input": {...}, "result": {...} },
    ...
  ],
  "remaining_requests": 1
}
```

### GET /health
```json
{ "status": "ok", "service": "ZoneAI" }
```

## Rate limiting

2 analyses par IP par 24h. Les IPs sont stockées sous forme de hash SHA-256 (jamais en clair).

---

Built by [Soufiane Mejahed](https://linkedin.com/in/soufiane-mejahed) · Epitech 2025
