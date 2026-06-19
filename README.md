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

### Persistent Installation (Docker / Unraid)

To prevent custom providers from being wiped when the Music Assistant Docker container is updated or restarted, you can use a startup hook script:

1. Create a `custom_providers` directory in your persistent appdata volume (e.g., `/mnt/user/appdata/music-assistant/custom_providers/`).
2. Place the provider folder (`better_lyrics`) inside that directory:
   `/mnt/user/appdata/music-assistant/custom_providers/better_lyrics`
3. Create an entrypoint hook script at `/mnt/user/appdata/music-assistant/entrypoint_hook.sh` with the following content:

```bash
#!/bin/sh

# Find site-packages directory
PROVIDERS_DIR=$(find /app/venv/lib/ -name "providers" -path "*/music_assistant/providers" | head -n 1)

if [ -n "${PROVIDERS_DIR}" ]; then
    # Copy custom providers from /data/custom_providers/
    if [ -d "/data/custom_providers" ]; then
        for provider in /data/custom_providers/*; do
            if [ -d "$provider" ]; then
                name=$(basename "$provider")
                rm -rf "${PROVIDERS_DIR}/${name}"
                cp -R "$provider" "${PROVIDERS_DIR}/${name}"
            fi
        done
    fi

    # Install dependencies if simplyrics is present
    if [ -d "${PROVIDERS_DIR}/simplyrics" ]; then
        /app/venv/bin/uv pip install ytmusicapi
    fi
fi

# Run the original entrypoint logic
for path in /usr/lib/*/libjemalloc.so.2; do
    [ -f "$path" ] && export LD_PRELOAD="$path" MALLOC_CONF="background_thread:true,dirty_decay_ms:5000,muzzy_decay_ms:5000" && break
done
exec mass "$@"
```

4. Make the script executable:
   ```bash
   chmod +x /mnt/user/appdata/music-assistant/entrypoint_hook.sh
   ```
5. Map this hook script in your Docker/Unraid container volume config:
   - **Host Path**: `/mnt/user/appdata/music-assistant/entrypoint_hook.sh`
   - **Container Path**: `/usr/local/bin/entrypoint.sh`
   - **Mode**: `Read/Write` (or `Read Only`)


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
