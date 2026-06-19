# Music Assistant BetterLyrics Metadata Provider

A custom metadata provider plugin for [Music Assistant](https://github.com/music-assistant/server) that retrieves track lyrics from the BetterLyrics API, converting TTML lyrics into time-synced LRC formats `[mm:ss.xx] Lyric text`.

## Features

- **Synced Lyrics:** Parses TTML from the BetterLyrics API into standard `LRC` format so that Music Assistant can render them as synced/karaoke-style lyrics.
- **Word-Level Sync:** Optional feature to parse word-level timestamps (e.g. `<00:10.15>`) from TTML span elements.
- **Clean Subtitle Annotations:** Option to strip annotations such as `[Chorus]`, `(Guitar Solo)`, etc., to keep lyrics clean.
- **Exclude Instrumentals:** Skips lyrics lookups for tracks marked or named as instrumental.
- **Duration Tolerance:** Configurable duration matching checks to ensure the retrieved lyrics match your audio file's duration.

---

## Installation

Run the following command in a shell that has access to the host's Docker daemon (e.g., via the Advanced SSH & Web Terminal add-on with Protection Mode turned off):

```bash
curl -fsSL https://raw.githubusercontent.com/Bluscream/music-assistant-betterlyrics/main/scripts/install_provider.sh | sh
```

### Options
You can customize the installation by running the script with options:
```bash
sh install_provider.sh --force --ma-id <container_name> --python-version <python_version>
```

---

## Configuration Settings

Once installed and activated in **Music Assistant -> Settings -> Integration / Plugins -> Add BetterLyrics**:

1. **BetterLyrics API URL:** Base URL for the BetterLyrics API endpoint. Default is:
   ```text
   https://lyrics-api.boidu.dev/getLyrics
   ```
2. **Duration Tolerance (seconds):** Maximum difference in seconds allowed between track duration and lyrics duration. Set to `0` to disable the check. Default is `10`.
3. **Exclude Instrumental Tracks:** Toggle whether to skip looking up lyrics for tracks labeled as instrumental. Default is `true`.
4. **Enable Word-Level Sync:** Toggle whether to parse word-level timestamps from TTML spans or keep it line-synced only. Default is `false`.
5. **Clean Subtitle Annotations:** Toggle to strip tags like `[Chorus]`, `(Guitar Solo)`, etc. from the lyrics. Default is `false`.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
