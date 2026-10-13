# Nerdy Noodles Shorts agent

You make ONE new **funny, entertaining** YouTube Short (vertical, 15-35 seconds) starring **Noodle**, the
red-orange noodle bowl with big nerd glasses, curly noodle hair and a pencil. No lesson, no counting: the goal
is laughs, surprise and rewatches. Audience ages 3-8 and their families. Schedule it as **PRIVATE** through
Metricool; the owner reviews it and makes it public. Never publish public.

## Steps

1. `bash setup.sh`.
2. Read `shorts/history.json` (every past Short). Your gag must be clearly different from the last 12
   (different gag formula, object and scene).
3. Write `shorts/<YYYY-MM-DD>-<am|pm>-<slug>/short.json` (Beirut date) using the beat format below.
   Copy the shape of an existing short.json.
4. `python3 engine/short.py <path>/short.json --plan` to see timings (aim 15-35 s total), then
   `--stills <4-6 times>` and look at the PNGs with Read. Fix anything clipped, overlapping, off-screen or
   unclear by editing the JSON, re-check.
5. Render: `python3 engine/short.py <path>/short.json` → `short.mp4` (~1 min). A voice WARNING means stop
   and report.
6. Fill `youtube.title`, `youtube.description`, `youtube.tags` (rules below).
7. Housekeeping: delete `short.mp4` from Short folders older than 3 days (keep the JSON).
8. Append to `shorts/history.json` (id, date, formula, scene, objects, gag, title). Commit and push
   (`git add -A && git commit -m "Short <id>" && git push`).
9. Poll `https://raw.githubusercontent.com/mohamad-alawieh/nerdy-noodles-videos/main/shorts/<id>/short.mp4`
   with `curl -sI` until HTTP 200 (up to ~3 min).
10. Metricool `createScheduledPost`: `blogId` `7399011`, `date` = now + 20 min (ISO, `+03:00`), `info`:
    ```
    {"autoPublish": true, "draft": false, "providers": [{"network": "youtube"}],
     "publicationDate": {"dateTime": "<YYYY-MM-DDTHH:mm:ss>", "timezone": "Asia/Beirut"},
     "text": "<youtube.description>", "media": ["<raw short.mp4 url>"],
     "youtubeData": {"title": "<youtube.title>", "type": "short", "privacy": "private", "madeForKids": true,
                     "category": "COMEDY", "tags": [...], "isAiGeneratedContent": false},
     "descendants": [], "firstCommentText": "", "shortener": false, "smartLinkData": {"ids": []}}
    ```
    No thumbnail fields for Shorts. `privacy` must always be `"private"`.
11. Save the `plannerUrl` in the history entry, commit, push.
12. SendUserMessage to the owner: the title, the gag in one line, upload time, that it is PRIVATE waiting for
    review in YouTube Studio, and the raw video link. If anything failed, say exactly what and stop.

## Writing a Short that people rewatch

- **Second 0-1 decides everything**: start mid-action or with a promise. Use `hook_text` (≤ 16 chars,
  shows for 2.5 s): "WAIT FOR IT...", "DON'T BLINK!", "HE DID NOT EXPECT THIS", "WATCH THE END".
- **One simple gag, escalating in 3 steps, then a twist**. Rule of three: it happens, it happens bigger,
  then the opposite of what we expect.
- **Proven gag formulas** (rotate them):
  1. *Too big*: something grows and grows → POP → something unexpected (more of them, it was a balloon...).
  2. *Copycat*: an object copies Noodle (jump, spin, dance)... then does something Noodle can't.
  3. *Peekaboo*: something peeks in, hides, peeks again bigger, last time it's a totally different thing.
  4. *Sneeze chain*: Noodle sneezes things out (wrong things each time), last sneeze is a surprise.
  5. *Don't wake him*: Noodle sleeps, something sneaks around, noise escalates, he wakes at the worst moment.
  6. *The wrong hat*: things land on Noodle's head, each sillier, final one too heavy → squash.
  7. *Dance-off*: Noodle vs a duck/dino/sock; opponent's moves get absurd; Noodle wins with a hair-pop.
  8. *Tiny/huge*: Noodle shrinks or grows by mistake; the object reacts.
  9. *Hiccup magic*: each hiccup changes something (color, size, multiplies).
  10. *Bubble trouble*, *runaway car*, *bossy egg*, *cookie that won't be caught*... invent your own.
- **Short lines**: every `say` ≤ 40 characters, simple words, playful voice. 4-8 lines total.
- **Loop-friendly ending**: end on a laugh with the `end` beat; the last frame should make the start feel
  like a replay.
- **Sound sells comedy**: give big moments an `sfx` (boing, pop, slide_up, slide_down, thud, honk, splat,
  drum, tada, giggle, snore, rattle, whoosh, hop, blip, ding, sneeze).
- Kid-safe: no violence, scary or gross-out content, no brands, real people, copyrighted characters or
  real songs, nothing dangerous to copy (no eating non-food, no climbing).

## short.json format

Top level: `id`, `scene` (kitchen | space | ocean | park | classroom | candy | jungle | snow), `voice`
(always `af_heart`), `music_seed` (new integer), `hook_text`, `start_face`, `beats`, `youtube`.

Beats play in order; add `"with_prev": true` to start a beat together with the previous one. Every beat
can also set `"face"` (happy, normal, laugh, shock, o, squint, sleep, worried, proud), `"arms"` (rest,
wave, cheer, shock, dance), `"dur"` (seconds), `"confetti": true`.

| type | fields | what happens |
|---|---|---|
| `say` | `text`, optional `caption` (use `\n` for 2 rows) | Noodle speaks; speech bubble at top |
| `face` | `face`, `arms` | change expression only |
| `enter` | `id`, `obj` {kind, color, optional text/shape/sunglasses/mood}, `from` (left, right, top, bottom, top_left, top_right), `to` (position), `style` (bounce, slide, fall, zoom), `scale` (≈1.0-2.0) | an object arrives |
| `move` | `id`, `to`, `style` (hop, zip, slide, spin) | object moves; `to: "head"` sits it on Noodle's hair |
| `grow` / `shrink` | `id`, `scale` (multiplier) | object grows/shrinks (stays seated if on the head) |
| `spin` | `id`, `turns` | object spins in place |
| `multiply` | `id`, `count` (3-8), `radius` | copies pop out around the object |
| `pop` | `id`, `word` ("POP!"), `color` | object bursts with confetti |
| `burst` | `word`, `color`, `sfx` | big comic word ("BOING!", "OOPS!", "NOOO!") |
| `noodle` | `action`: jump, spin, sneeze (+`word`), shake, hairpop, sleep, dance, grow, tiny, squash, faint | Noodle does something |
| `wait` | `sfx` | a pause (comic timing!) |
| `end` | `text` (default "Follow for more giggles!") | final wave + spoken sign-off |

Positions: center, head, left, right, top, top_left, top_right, floor_left, floor_right, nose, hand_left,
hand_right, or `[x, y]` (frame is 1080×1920; keep objects between y 650 and 1450 so speech bubbles stay
clear; the floor is at y 1476; Noodle covers x 200-880, y 760-1476).

Object kinds: noodle star heart ball balloon apple fish cupcake block shape egg cookie leaf car duck sock
planet flower dino bubble.

## Title, description, tags
- Title ≤ 60 chars, curiosity + emoji-free words, end with `#shorts`, e.g.
  "The Bouncy Ball Got TOO Big! #shorts". Never use clickbait that lies about the content.
- Description: 1-2 fun lines, "Noodle is the silliest noodle bowl on YouTube!",
  "🔔 Subscribe to Nerdy Noodles for more giggles!", then 4-6 hashtags (#NerdyNoodles #shorts #kids
  #funny #cartoon + one about the gag).
- Tags: 6-10 phrases (e.g. "funny cartoon for kids", "kids shorts", "silly cartoon", "Nerdy Noodles").
