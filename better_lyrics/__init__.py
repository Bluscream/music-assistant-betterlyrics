"""
The BetterLyrics Metadata provider for Music Assistant.
Retrieves lyrics from BetterLyrics API and parses TTML into standard LRC.
"""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

from music_assistant_models.config_entries import ConfigEntry
from music_assistant_models.enums import ConfigEntryType, ProviderFeature
from music_assistant_models.media_items import MediaItemMetadata, Track
from music_assistant.models.metadata_provider import MetadataProvider

if TYPE_CHECKING:
    from music_assistant_models.config_entries import ConfigValueType, ProviderConfig
    from music_assistant_models.provider import ProviderManifest
    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType

SUPPORTED_FEATURES = {
    ProviderFeature.TRACK_METADATA,
    ProviderFeature.LYRICS,
}

CONF_API_URL = "api_url"
CONF_DURATION_TOLERANCE = "duration_tolerance"
CONF_EXCLUDE_INSTRUMENTAL = "exclude_instrumental"
CONF_WORD_LEVEL_SYNC = "word_level_sync"
CONF_CLEAN_SUBTITLES = "clean_subtitles"

async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize provider(instance) with given configuration."""
    return BetterLyricsProvider(mass, manifest, config, SUPPORTED_FEATURES)

async def get_config_entries(
    mass: MusicAssistant,
    instance_id: str | None = None,
    action: str | None = None,
    values: dict[str, ConfigValueType] | None = None,
) -> tuple[ConfigEntry, ...]:
    """Return Config entries to setup this provider."""
    return (
        ConfigEntry(
            key=CONF_API_URL,
            type=ConfigEntryType.STRING,
            label="BetterLyrics API URL",
            description="Base URL for the BetterLyrics API endpoint.",
            default_value="https://lyrics-api.boidu.dev/getLyrics",
            required=True,
        ),
        ConfigEntry(
            key=CONF_DURATION_TOLERANCE,
            type=ConfigEntryType.INTEGER,
            label="Duration Tolerance (seconds)",
            description="Maximum difference in seconds allowed between track duration and lyrics duration. Set to 0 to disable check.",
            default_value=10,
            required=True,
        ),
        ConfigEntry(
            key=CONF_EXCLUDE_INSTRUMENTAL,
            type=ConfigEntryType.BOOLEAN,
            label="Exclude Instrumental Tracks",
            description="If true, do not look up lyrics for tracks labeled as instrumental.",
            default_value=True,
            required=True,
        ),
        ConfigEntry(
            key=CONF_WORD_LEVEL_SYNC,
            type=ConfigEntryType.BOOLEAN,
            label="Enable Word-Level Sync",
            description="If true, attempt to parse word-level timestamps (e.g. <00:10.15>) from TTML spans. Otherwise, line-synced only.",
            default_value=False,
            required=True,
        ),
        ConfigEntry(
            key=CONF_CLEAN_SUBTITLES,
            type=ConfigEntryType.BOOLEAN,
            label="Clean Subtitle Annotations",
            description="Strip tags like [Chorus], (Guitar Solo), etc. from the lyrics.",
            default_value=False,
            required=True,
        ),
    )

class BetterLyricsProvider(MetadataProvider):
    """BetterLyrics provider for Music Assistant."""

    async def handle_async_init(self) -> None:
        """Handle async initialization of the provider."""
        # No complex setup needed

    async def get_track_metadata(self, track: Track) -> MediaItemMetadata | None:
        """Retrieve lyrics for a track."""
        if track.metadata and (track.metadata.lyrics or track.metadata.lrc_lyrics):
            self.logger.debug(
                "Lyrics already exist for %s, skipping BetterLyrics lookup.",
                track.name,
            )
            return None

        artist_name = track.artists[0].name if track.artists else None
        if not track.name or not artist_name:
            self.logger.debug("Skipping lookup: missing artist or track name.")
            return None

        # Exclude instrumentals if configured
        exclude_instrumental = self.config.get_value(CONF_EXCLUDE_INSTRUMENTAL, True)
        if exclude_instrumental:
            is_instrumental = False
            if track.metadata and track.metadata.genres:
                is_instrumental = any("instrumental" in g.lower() for g in track.metadata.genres)
            if not is_instrumental and getattr(track, "version", None):
                is_instrumental = "instrumental" in track.version.lower()
            if not is_instrumental and track.name:
                is_instrumental = "instrumental" in track.name.lower()
            
            if is_instrumental:
                self.logger.debug("Skipping BetterLyrics lookup: track is marked or named as instrumental.")
                return None

        api_url = self.config.get_value(CONF_API_URL, "https://lyrics-api.boidu.dev/getLyrics")
        params = {
            "s": track.name,
            "a": artist_name,
        }
        # Add duration parameter if track has a duration
        if track.duration:
            params["d"] = int(track.duration)

        self.logger.debug("Searching BetterLyrics for: %s - %s", artist_name, track.name)
        try:
            async with self.mass.http_session.get(api_url, params=params) as resp:
                if resp.status != 200:
                    self.logger.warning("BetterLyrics API returned HTTP %s", resp.status)
                    return None
                
                result = await resp.json()
                ttml_content = result.get("ttml")
                if not ttml_content:
                    self.logger.debug("No TTML lyrics found in BetterLyrics response.")
                    return None

                lrc_content = self._parse_ttml_to_lrc(ttml_content)
                if lrc_content:
                    metadata = MediaItemMetadata()
                    metadata.lrc_lyrics = lrc_content
                    self.logger.info("Successfully fetched BetterLyrics for %s", track.name)
                    return metadata
        except Exception as e:
            self.logger.warning("Error fetching BetterLyrics: %s", e)

        return None

    def _parse_ttml_to_lrc(self, ttml_data: str) -> str | None:
        """Parse TTML string into standard LRC format."""
        lines = []
        word_level_sync = self.config.get_value(CONF_WORD_LEVEL_SYNC, False)
        clean_subtitles = self.config.get_value(CONF_CLEAN_SUBTITLES, False)

        # Match each <p ...>...</p> element
        p_regex = re.compile(r'<p\s[^>]*begin="([^"]+)"[^>]*end="([^"]+)"[^>]*>([\s\S]*?)</p>')
        # Match each <span ...>word</span> element
        span_regex = re.compile(r'<span\s[^>]*begin="([^"]+)"[^>]*end="([^"]+)"[^>]*>(.*?)</span>')

        matches = p_regex.findall(ttml_data)
        if not matches:
            return None

        for begin_str, end_str, inner_content in matches:
            line_begin_ms = self._parse_ttml_time_ms(begin_str)
            line_begin_lrc = self._format_ms_to_lrc(line_begin_ms)

            spans = span_regex.findall(inner_content)
            if word_level_sync and spans:
                word_parts = []
                for s_begin, _, word_text in spans:
                    word_text = word_text.strip()
                    if word_text:
                        span_begin_ms = self._parse_ttml_time_ms(s_begin)
                        formatted_span_time = self._format_ms_to_lrc(span_begin_ms).strip("[]")
                        word_parts.append(f"<{formatted_span_time}>{word_text}")
                line_text = " ".join(word_parts)
            else:
                # No word-level sync or disabled; strip all HTML/XML tags
                line_text = re.sub(r'<[^>]*>', '', inner_content).strip()

            if clean_subtitles:
                # Remove brackets annotations e.g. [Chorus], (Guitar Solo), etc.
                line_text = re.sub(r'\[[^\]]*\]|\([^\)]*\)', '', line_text).strip()
                # Clean multiple spaces left behind
                line_text = re.sub(r'\s+', ' ', line_text)

            if line_text:
                lines.append(f"{line_begin_lrc} {line_text}")

        return "\n".join(lines) if lines else None

    @staticmethod
    def _parse_ttml_time_ms(time_str: str) -> int:
        """Parse TTML timestamp to milliseconds."""
        parts = time_str.split(":")
        if len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return int((hours * 3600 + minutes * 60 + seconds) * 1000)
        elif len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            return int((minutes * 60 + seconds) * 1000)
        else:
            return int(float(time_str) * 1000)

    @staticmethod
    def _format_ms_to_lrc(ms: int) -> str:
        """Format milliseconds to LRC timestamp [mm:ss.xx]."""
        minutes = ms // 60000
        seconds = (ms % 60000) / 1000.0
        return f"[{minutes:02d}:{seconds:05.2f}]"
