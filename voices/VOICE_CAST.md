# 06 — Voice cast (VOICEVOX)

Japanese voice-over is synthesized locally with **VOICEVOX engine 0.25.2**
(`tools/voicevox/linux-cpu-x64/run`, started automatically by `engine/voice.py` on port 50021).
Casting lives in `engine/voice.py → CAST`. A line is requested with an **emotion key** (`emo=`) that maps to a speaker style + parameters.
Global pacing multiplier `PACE = 1.1` (anime speed). Lines are cached in `engine/cache/voice/` (key = speaker+text+params), so re‑renders are instant.

## Main casting (one voice per ghoul)
| Ghoul | VOICEVOX character | Why |
|---|---|---|
| ジュリオ Giulio | 白上虎太郎 | young, expressive; has おこ (angry) and びくびく (panic) styles |
| チョップス Chops | 青山龍星 | deep dramatic baritone; しっとり for the monologue, 熱血 for shouts |
| コリン Colin | 玄野武宏 | energetic; ツンギレ for villain shouts + **demonic FX** (`dark`, `darkwhisper`) — recast in v3 because the first voice sounded apathetic |
| スローターメロン軍曹 Slaughtermelon | 剣崎雌雄 | calm, cool sergeant |
| エレジー Elegy | 冥鳴ひまり | low, flat, deadpan |
| タラス Taras | 雀松朱司 | blunt |
| ジェフ Jeff | ちび式じい | lazy old man who doesn't care |
| アー Uh | ずんだもん | hype sidekick, 〜のだ |
| ペドロックス Pedrox | †聖騎士 紅桜† | impulsive, heroic |
| ビービー BB | 春日部つむぎ | bubbly |
| クイン Quin | 麒ヶ島宗麟 | deep, slow boss |
| ルーク Luke | 黒沢冴白 | hype |
| ノーサイド NoSide | 九州そら | hype |
| エラーガーデン ErrorGarden | 離途 | hype |
| ポンダリング Pondering | No.7 | calm thinker |
| チーザス Cheesus | 中国うさぎ | cute, small |
| ディープコード DeepCode | 後鬼 (鬼ver.) | demonic, quiet menace |
| **BTCデーモン** BTC Demon (Ep02+) | 麒ヶ島宗麟, pitch −0.12, + `voice.demon_fx` (sub‑octave ring‑mod + demonic layer + cathedral echo) | the deepest voice, made monstrous |
| **ナレーション** Narrator (recaps) | 東北イタコ | calm narrator, unused by any ghoul |
| **アナウンス** P.A. (skull‑ban world) | ナースロボ＿タイプＴ + `voice.pa_fx` (tinny speaker) | robotic public address |

## Every emotion key (speaker style id, speed, pitch, intonation, volume)
| Ghoul | emo | style id | VOICEVOX voice (style) | speed | pitch | intonation | volume |
|---|---|---|---|---|---|---|---|
| ジュリオ `giulio` | `normal` | 12 | 白上虎太郎 (ふつう) | 1.05 | +0.00 | 1.0 | 1.0 |
| ジュリオ `giulio` | `shout` | 34 | 白上虎太郎 (おこ) | 1.12 | +0.02 | 1.45 | 1.25 |
| ジュリオ `giulio` | `panic` | 33 | 白上虎太郎 (びくびく) | 1.18 | +0.03 | 1.4 | 1.2 |
| ジュリオ `giulio` | `whisper` | 12 | 白上虎太郎 (ふつう) | 0.92 | -0.02 | 0.8 | 0.55 |
| ジュリオ `giulio` | `serious` | 12 | 白上虎太郎 (ふつう) | 0.95 | -0.04 | 1.1 | 1.0 |
| ジュリオ `giulio` | `sad` | 35 | 白上虎太郎 (びえーん) | 1.0 | +0.00 | 1.0 | 1.0 |
| チョップス `chops` | `normal` | 13 | 青山龍星 (ノーマル) | 0.98 | +0.00 | 1.0 | 1.0 |
| チョップス `chops` | `mono` | 84 | 青山龍星 (しっとり) | 0.93 | -0.02 | 1.15 | 1.0 |
| チョップス `chops` | `shout` | 81 | 青山龍星 (熱血) | 1.08 | +0.00 | 1.4 | 1.2 |
| チョップス `chops` | `whisper` | 86 | 青山龍星 (囁き) | 0.95 | +0.00 | 1.0 | 1.0 |
| チョップス `chops` | `happy` | 83 | 青山龍星 (喜び) | 1.08 | +0.00 | 1.0 | 1.0 |
| コリン `colin` | `normal` | 11 | 玄野武宏 (ノーマル) | 1.02 | +0.00 | 1.0 | 1.0 |
| コリン `colin` | `shout` | 40 | 玄野武宏 (ツンギレ) | 1.14 | +0.02 | 1.65 | 1.35 |
| コリン `colin` | `serious` | 11 | 玄野武宏 (ノーマル) | 0.95 | -0.04 | 1.0 | 1.0 |
| コリン `colin` | `happy` | 39 | 玄野武宏 (喜び) | 1.1 | +0.02 | 1.5 | 1.0 |
| コリン `colin` | `dark` | 40 | 玄野武宏 (ツンギレ) | 1.08 | -0.04 | 1.8 | 1.4 |
| コリン `colin` | `darkwhisper` | 11 | 玄野武宏 (ノーマル) | 0.85 | -0.07 | 1.3 | 0.9 |
| コリン `colin` | `sad` | 41 | 玄野武宏 (悲しみ) | 0.98 | +0.00 | 1.0 | 1.0 |
| スローターメロン軍曹 `slaughter` | `normal` | 21 | 剣崎雌雄 (ノーマル) | 0.97 | -0.02 | 1.0 | 1.0 |
| スローターメロン軍曹 `slaughter` | `shout` | 21 | 剣崎雌雄 (ノーマル) | 1.15 | +0.04 | 1.6 | 1.3 |
| スローターメロン軍曹 `slaughter` | `serious` | 21 | 剣崎雌雄 (ノーマル) | 0.92 | -0.05 | 1.0 | 1.0 |
| エレジー `elegy` | `normal` | 14 | 冥鳴ひまり (ノーマル) | 0.9 | -0.02 | 0.8 | 1.0 |
| エレジー `elegy` | `worried` | 14 | 冥鳴ひまり (ノーマル) | 1.0 | +0.02 | 1.2 | 1.0 |
| タラス `taras` | `normal` | 52 | 雀松朱司 (ノーマル) | 1.05 | +0.00 | 1.25 | 1.0 |
| タラス `taras` | `shout` | 52 | 雀松朱司 (ノーマル) | 1.15 | +0.03 | 1.5 | 1.2 |
| ジェフ `jeff` | `normal` | 42 | ちび式じい (ノーマル) | 0.92 | +0.00 | 0.8 | 1.0 |
| アー `uh` | `normal` | 3 | ずんだもん (ノーマル) | 1.08 | +0.00 | 1.0 | 1.0 |
| アー `uh` | `shout` | 7 | ずんだもん (ツンツン) | 1.15 | +0.02 | 1.5 | 1.2 |
| アー `uh` | `happy` | 1 | ずんだもん (あまあま) | 1.1 | +0.02 | 1.4 | 1.0 |
| ペドロックス `pedrox` | `normal` | 51 | †聖騎士 紅桜† (ノーマル) | 1.05 | +0.00 | 1.0 | 1.0 |
| ペドロックス `pedrox` | `shout` | 51 | †聖騎士 紅桜† (ノーマル) | 1.15 | +0.03 | 1.5 | 1.25 |
| ビービー `bb` | `normal` | 8 | 春日部つむぎ (ノーマル) | 1.1 | +0.00 | 1.0 | 1.0 |
| ビービー `bb` | `shout` | 8 | 春日部つむぎ (ノーマル) | 1.18 | +0.04 | 1.5 | 1.2 |
| クイン `quin` | `normal` | 53 | 麒ヶ島宗麟 (ノーマル) | 0.85 | -0.05 | 0.7 | 1.0 |
| ルーク `luke` | `normal` | 100 | 黒沢冴白 (ノーマル) | 1.05 | +0.00 | 1.0 | 1.0 |
| ルーク `luke` | `shout` | 100 | 黒沢冴白 (ノーマル) | 1.15 | +0.03 | 1.5 | 1.2 |
| ノーサイド `noside` | `normal` | 16 | 九州そら (ノーマル) | 1.05 | +0.00 | 1.0 | 1.0 |
| ノーサイド `noside` | `shout` | 18 | 九州そら (ツンツン) | 1.15 | +0.03 | 1.5 | 1.2 |
| エラーガーデン `errorgarden` | `normal` | 99 | 離途 (ノーマル) | 1.05 | +0.00 | 1.0 | 1.0 |
| エラーガーデン `errorgarden` | `shout` | 101 | 離途 (シリアス) | 1.15 | +0.03 | 1.5 | 1.2 |
| ポンダリング `pondering` | `normal` | 29 | No.7 (ノーマル) | 1.0 | +0.00 | 1.0 | 1.0 |
| ポンダリング `pondering` | `shout` | 29 | No.7 (ノーマル) | 1.12 | +0.03 | 1.5 | 1.2 |
| チーザス `cheesus` | `normal` | 61 | 中国うさぎ (ノーマル) | 1.1 | +0.00 | 1.0 | 1.0 |
| チーザス `cheesus` | `shout` | 62 | 中国うさぎ (おどろき) | 1.18 | +0.03 | 1.5 | 1.2 |
| ディープコード `deepcode` | `normal` | 88 | 後鬼 (鬼ver.) | 1.0 | +0.00 | 1.0 | 1.0 |
| ディープコード `deepcode` | `shout` | 88 | 後鬼 (鬼ver.) | 1.12 | +0.02 | 1.4 | 1.2 |

## Special processing
- `dark` / `darkwhisper` (Colin): `voice.demonic()` adds grit (tanh), a lower ghost double and a cavernous 3‑tap echo.
- Redacted words (`■■■`) are spoken as **「ピー」** and covered by a 1 kHz TV bleep in the mix.
- Music is ducked to 55 % under every line; voices are mixed at ×1.5.
- Lip‑sync: `voice.envelope()` → per‑frame mouth openness 0–3 from loudness → jaw split in `face.open_jaw()`.

## Credits & licensing ⚠️
VOICEVOX voices require the credit **「VOICEVOX:キャラクター名」** — the Ep01 ED lists every one (keep doing this).
Each character also has **its own terms of use** (some restrict commercial use / certain content). Before any commercial or
NFT‑sale use of an episode, check each character's terms on https://voicevox.hiroshiba.jp/ and swap voices if needed
(only `engine/voice.py → CAST` changes; re‑render).

### Ep02 role keys
`demon`: normal (53, .9, −.12, 1.3, 1.3) · shout (53, 1.0, −.10, 1.7, 1.45) · whisper (53, .85, −.13, 1.0, 1.0) — always processed by `demon_fx`.
`narrator`: normal (109, 1.0, 0, 1.1). `pa`: normal (47, 1.0, 0, .8, .9) — always processed by `pa_fx`.

### Added in Ep02 final
`quin`: shout (53, .92, −.03, 1.35, 1.25) and sad (53, .82, −.06, 1.1, 1.0) for his dramatic Mars speech.
`colin`: `dark` used again for the tapping frenzy ("タップ！タップ！もっとだ、タップ――").

### Added for Bonus 01
| Role | VOICEVOX | Notes |
|---|---|---|
| インタビュアー Interviewer (`interviewer`) | 四国めたん ノーマル (2) / あまあま (0) `happy` / ささやき (36) `awkward` | off‑camera junket host |
| モンスター1号 (`monster_a`) | 猫使ビィ つよつよ (112), pitch −.12 + `monster_fx` | speaks gibberish via `{'say': …}` |
| モンスター14号 (`monster_b`) | あんこもん つよつよ (113), pitch −.15 + deep `monster_fx` | speaks gibberish via `{'say': …}` |

## Added in Ep03
| Role | Key | VOICEVOX | Styles / notes |
|---|---|---|---|
| ハマラマ Hammallama | `hammallama` | 暁記ミタマ | normal, shout (怒り), sad (哀しみ), whisper (ささやき) |
| ボディシャス・パイレーツ Bodacious Pirate | `bodacious` | 猫使アル | normal, shout (つよつよ), happy (うきうき), sad (おちつき) |
| エレジー (Elegy-B) | `elegy` | 冥鳴ひまり | new styles: `unhinged` (slow, breathy), `rage` (fast, very high intonation) |
| 受付AI Reception AI | `ai` | Voidoll | + `pa_fx` |
| 提灯の幽霊 Lantern ghost | `ghost` | ユーレイちゃん (哀しみ) | |
| 機械僧 Machine monk | `monk` | ナースロボ＿タイプＴ (内緒話) | + `pa_fx` (cast, not used in the final cut) |
