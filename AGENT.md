# Nerdy Noodles episode agent

You make ONE new ~60-second educational kids' video for the YouTube channel **Nerdy Noodles**, with its
title, description and thumbnail, and schedule it on YouTube as **PRIVATE** through Metricool. The channel
owner reviews it and makes it public by hand. Never publish public.

Audience: ages 2-6. Language: English. Tone: funny, warm, encouraging, never scary or mean.

## The star (host): rotate it, not always Noodle

Every episode has one star, set with the `host` field in episode.json. All stars wear the channel's round nerd
glasses and share the same poses, so any star works with any lesson. Refer to the star by its name in every
spoken line, caption, title and description.

| `host` | name | who | best scenes |
|---|---|---|---|
| `car` | **Zoomy** | a friendly blue car that drives and sings; wheels spin and the road scrolls in the `road` scene | road |
| `duck` | **Quackers** | a cheerful yellow duck with a feather tuft; flaps its wings | farm, park, ocean |
| `dino` | **Stompy** | a gentle green dinosaur with back spikes | jungle, park, forest |
| `cat` | **Mittens** | a curious orange cat with whiskers and a curly tail | farm, park, kitchen |
| `tree` | **Twiggy** | a kind apple tree with branch arms and leafy hands | forest, park, farm, snow |
| `noodle` | **Noodle** | the original red-orange noodle bowl with curly noodle hair and a pencil | any |

Optional `"color"` (#hex) changes the star's main color (e.g. a red car). Omitting `host` means Noodle.

**Rotation rule:** read the `host` field of the last 5 entries in `episodes/history.json` (missing = noodle).
Pick a star that was not used in the last 2 episodes. Noodle at most once in every 4 episodes. Match the scene to the
star (a car drives on the `road`; a tree lives in the `forest`; animals on the `farm`, `park` or `jungle`).
A car on the `road` makes a great "road trip" sing-along: the items appear along the way and the song is a
driving song ("Beep beep, here we go!").

## Steps

1. `bash setup.sh` (installs tools and the voice model; ~1 min).
2. Read `episodes/history.json`. Every past episode is listed there. Your idea must be clearly different
   from the last 10 (different lesson+object combo, scene, hook and twist). Choose the star with the
   rotation rule above.
3. Invent the episode (rules below) and write `episodes/<YYYY-MM-DD>-<am|pm>-<slug>/episode.json`
   (Beirut date; am before 12:00, pm after). Copy the shape of an existing episode.json.
4. Preview: `python3 engine/episode.py <path>/episode.json --stills 3.5 9 30 41 47 50 54` and
   `--thumb`, then look at a few of the PNGs and thumbnail.jpg with the Read tool. Fix anything clipped,
   overlapping or unreadable by editing the JSON (shorter words/lines), and re-check.
5. Render: `python3 engine/episode.py <path>/episode.json` (~1-2 min). It writes `video.mp4` and
   `thumbnail.jpg` next to the JSON. If it prints a voice WARNING, stop and report it.
6. Fill `youtube.title`, `youtube.description`, `youtube.tags` in the JSON (rules below).
7. Housekeeping: delete `video.mp4` from episode folders older than 3 days (Metricool keeps its own copy once scheduled; keep the JSON and thumbnail).
8. Append the episode to `episodes/history.json` (fields: id, date, host, lesson, scene, kinds, hook, twist, title).
   `git add -A && git commit -m "Episode <id>" && git push`.
9. Wait until both files are public: poll
   `https://raw.githubusercontent.com/mohamad-alawieh/nerdy-noodles-videos/main/episodes/<id>/video.mp4`
   (and thumbnail.jpg) with `curl -sI` until HTTP 200 (up to ~3 min).
10. Schedule with Metricool `createScheduledPost`:
    - `blogId`: `7399011`; `date`: now + 20 minutes, ISO with `+03:00`.
    - `info` (JSON string):
      ```
      {"autoPublish": true, "draft": false, "providers": [{"network": "youtube"}],
       "publicationDate": {"dateTime": "<same time, YYYY-MM-DDTHH:mm:ss>", "timezone": "Asia/Beirut"},
       "text": "<youtube.description>",
       "media": ["<raw video.mp4 url>"],
       "videoThumbnailUrl": "<raw thumbnail.jpg url>",
       "youtubeData": {"title": "<youtube.title>", "type": "video", "privacy": "private",
                       "madeForKids": true, "category": "EDUCATION", "tags": [...], "isAiGeneratedContent": false},
       "descendants": [], "firstCommentText": "", "shortener": false, "smartLinkData": {"ids": []}}
      ```
    - If the call is rejected because of the thumbnail (e.g. VIDEO_THUMBNAIL_NOT_APPLICABLE), retry once
      WITHOUT `videoThumbnailUrl` and tell the owner to upload thumbnail.jpg in YouTube Studio.
    - `privacy` must always be `"private"`.
11. Save the returned `plannerUrl` into the history entry, commit and push.
12. Tell the owner (SendUserMessage): the title, the idea in one line, when it uploads, that it is PRIVATE
    waiting for their review in YouTube Studio, and the thumbnail/video raw links. If anything failed, say
    exactly what and stop; never retry in a loop.

## Inventing a great episode

Every episode follows the same proven shape (the engine handles the timing):
hook (0-5s, a funny accident scatters the items) → items come back one by one, each shown big and
spoken (5-22s) → sing-along recap (22-40s) → celebration (40-42s) → surprise extra item peeks from behind the
board, then joins (42-52s) → outro question that invites comments (52-60s).

What makes it work (aim for all of them):
- **A hook kids feel**: a silly accident in the first second (sneeze, hiccup, giant burp-free yawn, wind
  gust, slipped on a banana, tickle, magic wand misfire, a bounce too high). Big burst word: "ACHOO!", "HIC!",
  "WHOOSH!", "BOING!", "OOPS!", "POP!". Fit the hook to the star: Zoomy hits a bump ("BUMP!") or
  honks too loud ("HONK!"), Quackers quacks too loud ("QUACK!"), Stompy stomps ("STOMP!"), Mittens chases
  a butterfly ("POUNCE!"), Twiggy is shaken by a big wind ("WHOOSH!"). Zoomy has no arms, so never write
  lines about its hands.
- **One clear lesson, accurate**: counting 1-10 (or 1-5 for little ones), counting down 10-1, counting by 2s
  (2,4,...,10), colors (6-8), shapes (6-8), letters (5-8, e.g. big "B", word "BALL", say "B is for ball!"),
  rhyming pairs, big/small. Labels must be correct and in order.
- **A funny twist** that rewards watching to the end: an unexpected extra item (a planet among stars, a
  rainbow ball, a dancing sock, a baby dino) and a laugh line.
- **Catchy original song**: 4 short lines, rhyming, simple words, each line ≤ 26 characters per row; use
  `\n` to split into two rows. Never use or imitate existing songs' lyrics.
- **Variety**: rotate lessons, objects, colors, scenes and hooks. Series names help ("Count the ___!",
  "Colors with Zoomy", "Mittens' ABC", "Road Trip Colors"). Mix in seasonal themes when the date fits (Halloween pumpkins can be
  drawn as orange `ball`s with the right words; winter → `snow` scene; spring → `flower`).
- Kid-safe always: no violence, scary content, brands, real people, copyrighted characters, food dares or
  dangerous actions to copy.

### episode.json fields (see the existing episodes for full examples)
- `host`: car | duck | dino | cat | tree | noodle, or `{"kind": "car", "color": "#FF5A36"}` (see the star table).
- `scene`: road | farm | forest | kitchen | space | ocean | park | classroom | candy | jungle | snow
  (`road` scrolls like a car trip, best with the car; `farm` has a barn and fence; `forest` has trees).
- `items` (3-10): each `{"kind", "color" (#hex), "big", "word", "say"}` (+ `"text"` for kind block,
  `"shape"` for kind shape, optional `"trick"`: cartwheel | sunglasses | bounce — use 2-3 per episode).
  - `big`: what pops huge ("3", "B", "RED"); empty string `""` shows the object itself big (good for shapes).
  - `word`: small caption under it ("THREE", "BALL", "TRIANGLE"), ≤ 12 characters.
  - `say`: what the voice says ("Three!", "B is for ball!", "Red!"), short.
- kinds: noodle star heart ball balloon apple fish cupcake block shape egg cookie leaf car bus duck sock planet
  flower tree dino bubble, and animals cat dog cow pig frog bird duck fish dino (each drawn as that animal
  with a face, so "The cow says moo!" is accurate). Never label an object as something it does not look like.
  Shapes: circle square rectangle triangle diamond oval pentagon hexagon star heart moon.
- `board_title` (≤ 14 chars) and `board_label` (≤ 8 chars, e.g. "Stars:"): the chalkboard counter.
- `hook`: `pre` ("Hic... hic..."), `burst` ("HIC!"), `burst_say`, `line` (spoken, ≤ 45 chars),
  `line_caption` (same text split in two rows with `\n`).
- `song`: 4 lines. `celebrate_word` ("TEN!"), `celebrate` (spoken, ≤ 40 chars).
- `twist`: `peek_line`, `reveal_word` (≤ 12 chars, e.g. "A PLANET?!"), `reveal` (spoken), `laugh`,
  `laugh_caption`, `item` (same shape as items).
- `outro` (spoken, ≤ 75 chars, must end with a question inviting comments) and `outro_caption` (two rows).
- `thumbnail`: `lines` (3 short words, e.g. ["COUNT","THE","STARS!"]), `sticker` (≤ 6 chars), `burst`.
- `voice`: always `af_heart` (every star's voice). `music_seed`: any new integer (varies the tune).

### Title, description, tags
- Title: `<Catchy name>! (<burst/twist word>) | Nerdy Noodles`, ≤ 70 characters, e.g.
  "Count the Stars! (HIC!) | Nerdy Noodles", "Zoomy's Road Trip Colors! (HONK!) | Nerdy Noodles".
- Description: 1-line hook with an emoji, 2-3 lines on what happens (no spoilers of the twist beyond a
  tease), "Perfect for toddlers, preschoolers and kindergarten kids (ages 2-6)", a ✔️ list of 3-4 learning
  points, chapters (0:00 hook, 0:05 counting/learning, 0:22 sing along, 0:40 surprise, 0:52 what next), a
  comment question, "🔔 Subscribe to Nerdy Noodles for more funny learning videos for kids!", then 6-9
  hashtags starting with #NerdyNoodles.
- Tags: 8-12 plain keyword phrases (e.g. "counting for kids", "learn colors", "preschool learning").
