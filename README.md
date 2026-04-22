# davo-daily-briefing

Daily briefing service that pulls data from integrations, generates a morning briefing, emails it, and exposes stored briefings via API.

## Environment variables

- `BRIEFING_API_SECRET`: shared bearer token for briefing API auth.
- `BRIEFING_DB_PATH`: SQLite file path for stored briefings (default `briefings.db`).

For Railway, point `BRIEFING_DB_PATH` to a mounted volume so data persists across deploys (for example: `/data/briefings.db`).
