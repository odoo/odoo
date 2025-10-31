/** @odoo-module **/

/**
 * Parses a timestamp in SRT (HH:MM:SS,ms) or VTT (HH:MM:SS.ms) format transcript lines object
 * Handles optional hours (MM:SS) and optional milliseconds.
 * @param {string} timestamp
 * @returns {number|NaN} seconds or NaN if invalid
 **/
function parseTimestamp(timestamp) {
    if (!timestamp) {
        return NaN;
    }
    // Clean up settings/alignments after timestamp (e.g. "00:00:04.000 align:start")
    const cleanTimestamp = timestamp.split(" ")[0].trim();

    const parts = cleanTimestamp.split(":");
    // Must have at least MM:SS
    if (parts.length < 2 || parts.length > 3) {
        return NaN;
    }

    // Seconds part can contain dot or comma for milliseconds
    const lastPart = parts[parts.length - 1].replace(",", ".");
    const secondsValue = parseFloat(lastPart);
    if (isNaN(secondsValue)) {
        return NaN;
    }

    const seconds = secondsValue;
    let minutes = 0;
    let hours = 0;

    if (parts.length === 2) {
        // MM:SS.ms
        minutes = parseInt(parts[0], 10);
    } else {
        // HH:MM:SS.ms
        minutes = parseInt(parts[1], 10);
        hours = parseInt(parts[0], 10);
    }

    if (isNaN(minutes) || isNaN(hours)) {
        return NaN;
    }

    return hours * 3600 + minutes * 60 + seconds;
}

/**
 * Parses SRT or VTT file content into a structured array.
 * @param {string} timedTextContent The raw SRT or VTT string.
 * @returns {Array<Object>} An array of subtitle objects, e.g.,
 *   [{ startTime: 1.234, endTime: 3.456, text: "Hello world" }, ...]
 **/
export function parseTimedText(timedTextContent) {
    if (!timedTextContent) {
        return [];
    }
    const normalized = timedTextContent.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    const cleaned = normalized.replace(/^WEBVTT.*\n/g, "");
    const blocks = cleaned.trim().split(/\n\s*\n/);

    const cues = [];

    for (const block of blocks) {
        const blockLines = block.split("\n");
        if (blockLines.length === 0) {
            continue;
        }

        if (blockLines[0].trim().startsWith("NOTE")) {
            continue;
        }

        // Find the timestamp line. A valid cue MUST have a line with "-->"
        const tsIndex = blockLines.findIndex((l) => {
            if (!l.includes("-->")) {
                return false;
            }
            const parts = l.split("-->");
            if (parts.length !== 2) {
                return false;
            }
            return (
                !isNaN(parseTimestamp(parts[0].trim())) && !isNaN(parseTimestamp(parts[1].trim()))
            );
        });

        if (tsIndex !== -1) {
            // New valid cue found!
            const timestampLine = blockLines[tsIndex];
            const [startRaw, endRaw] = timestampLine.split("-->");

            cues.push({
                startTime: parseTimestamp(startRaw.trim()),
                endTime: parseTimestamp(endRaw.trim()),
                textLines: blockLines.slice(tsIndex + 1),
            });
        } else if (cues.length > 0) {
            // This block does not have a timestamp line. assume it's the previous cue's text.
            const lastCue = cues[cues.length - 1];
            lastCue.textLines.push(""); // Re-insert the blank line splitting the blocks
            lastCue.textLines.push(...blockLines);
        } else {
            // Lines before the first cue, assume it's a header -> garbage
            continue;
        }
    }

    return cues.map((c) => ({
        startSec: c.startTime,
        endSec: c.endTime,
        text: c.textLines.join("\n").trim(),
    }));
}
