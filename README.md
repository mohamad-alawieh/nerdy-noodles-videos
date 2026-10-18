# Nerdy Noodles videos

Automatic episode maker for the Nerdy Noodles kids' YouTube channel.

- `engine/` – draws Noodle and friends, animates a 60-second episode, makes music, voice and the thumbnail.
- `episodes/<id>/` – one folder per episode: `episode.json` (the idea and script), `video.mp4`, `thumbnail.jpg`.
- `episodes/history.json` – every episode made so far.
- `AGENT.md` – instructions for the twice-daily learning episodes.
- `SHORTS.md` – instructions for the twice-daily sing-along Shorts (English and Arabic, alternating).

Make an episode by hand: `bash setup.sh && python3 engine/episode.py episodes/<id>/episode.json`

Shorts (vertical sing-along songs; older ones are talking gags): `engine/short.py` + `engine/singer.py`, `shorts/<id>/short.json`, instructions in `SHORTS.md`.
