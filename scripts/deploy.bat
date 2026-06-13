@echo off
set SSH_ASKPASS=C:\Users\blusc\.gemini\antigravity-ide\scratch\askpass.bat
set SSH_ASKPASS_REQUIRE=force
set DISPLAY=dummy

echo [1/3] Copying better_lyrics files to Unraid NAS...
ssh -o StrictHostKeyChecking=no root@192.168.2.10 "rm -rf /tmp/better_lyrics"
scp -o StrictHostKeyChecking=no -r d:\Projects\MusicAssistant\music-assistant-betterlyrics\better_lyrics root@192.168.2.10:/tmp/

echo [2/3] Injecting better_lyrics into music-assistant container...
ssh -o StrictHostKeyChecking=no root@192.168.2.10 "docker exec music-assistant rm -rf /app/venv/lib/python3.14/site-packages/music_assistant/providers/better_lyrics && docker cp /tmp/better_lyrics music-assistant:/app/venv/lib/python3.14/site-packages/music_assistant/providers/ && rm -rf /tmp/better_lyrics"

echo [3/3] Restarting music-assistant container to load new plugin...
ssh -o StrictHostKeyChecking=no root@192.168.2.10 "docker restart music-assistant"

echo Deployment finished!
