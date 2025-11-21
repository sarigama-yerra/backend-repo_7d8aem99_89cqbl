# Blue Flame Prompts Runbook

This document explains when to call each prompt template in blueflame_prompts.json and the expected shapes. All prompts include tempo placeholders and describe how BPM affects generation.

1) instrumental
- When: After collecting tempo, key, style, and instrument list.
- Input fields: tempo (BPM), key, length_sec, style, instruments[]
- Output: stems[] each with instrument + signed URL (44.1kHz WAV)

2) melody
- When: After lyrics are provided; before vocal synthesis.
- Input: lyrics (text), style, tempo (BPM), key
- Output: midi_b64, guide_b64, timestamps[] per lyric line
- Constraints: avoid leaps > octave; timestamps align to tempo

3) vocal_synth
- When: After melody MIDI and voice profile are ready.
- Input: voice_name/locale/gender, melody_midi URL, lyrics, tempo
- Output: two WAV takes + alignment JSON

4) mix
- When: After stems + vocals are ready.
- Input: lufs, stems URLs, tempo (for time-based FX sync)
- Output: master WAV URL + processed stems URLs

5) video
- When: After master audio ready and timestamp map available.
- Input: aspect_ratio (16:9 or 9:16), style, tempo, timestamps
- Output: thumbnails[] and video_url (MP4 with burned-in subtitles)

6) pre_generated_voices
- When: Voice selector needs curated presets.
- Output: voices[] with id, name, locale, gender, demo_url, hints

7) promo
- When: After main video; creates a 30s 9:16 promo.
- Input: master_url, tempo, timestamps
- Output: promo_url

Replace orchestrator stub calls with production API calls, pass the fields above, and implement retries as recommended within the template metadata.
