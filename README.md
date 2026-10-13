# Nerdy Noodles videos

Automatic episode maker for the Nerdy Noodles kids' YouTube channel.

- `engine/` – draws Noodle and friends, animates a 60-second episode, makes music, voice and the thumbnail.
- `episodes/<id>/` – one folder per episode: `episode.json` (the idea and script), `video.mp4`, `thumbnail.jpg`.
- `episodes/history.json` – every episode made so far.
- `AGENT.md` – the instructions the scheduled Claude task follows twice a day.

Make an episode by hand: `bash setup.sh && python3 engine/episode.py episodes/<id>/episode.json`
