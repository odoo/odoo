/** @odoo-module **/

import { expect, describe, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { click, queryOne } from "@odoo/hoot-dom";
import { startServer, start, openFormView, mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CallDebrief } from "@mail/views/fields/call_debrief/call_debrief";

describe.current.tags("desktop", "call_debrief");

defineModels(mailModels);

const AUDIO_FIXTURE_URL = "/mail/static/tests/fixtures/audio_60s.webm";
const VIDEO_FIXTURE_URL = "/mail/static/tests/fixtures/video_60s.webm";

/**
 * Creates a media artifact (audio or video) that maps to the 60-second fixture.
 * @param {Object} pyEnv The python environment
 * @param {Object} options
 * @param {number} options.start Start time in seconds relative to the call
 * @param {string} [options.type="audio"] "audio" or "video"
 * @returns {number} The created artifact ID
 */
function _createRecording(pyEnv, { start = 0, type = "audio" } = {}) {
    const duration = 60; // Always 60s to match the fixture length
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "fixture_" + start + "_" + type + ".webm",
        mimetype: type === "video" ? "video/webm" : "audio/webm",
    });
    return pyEnv["mail.call.artifact"].create({
        media_id: attachmentId,
        start_ms: start * 1000,
        end_ms: (start + duration) * 1000,
    });
}

function _setupCallDebriefPatch() {
    patchWithCleanup(CallDebrief.prototype, {
        async _loadData(props) {
            await super._loadData(props);
            if (!this.state.mediaSegments) {
                return;
            }
            // Automatically inject the correct static fixture URL based on type
            for (const segment of this.state.mediaSegments) {
                segment.mediaUrl = segment.type === "video" ? VIDEO_FIXTURE_URL : AUDIO_FIXTURE_URL;
            }
        },
    });
}

async function _openDebriefView(pyEnv, discussCallHistoryId) {
    await openFormView("discuss.call.history", discussCallHistoryId, {
        arch: `
            <form>
                <field name="start_date" invisible="1"/>
                <field name="end_date" invisible="1"/>
                <field name="artifact_ids" widget="call_debrief" options="{'callStartDateField': 'start_date', 'callEndDateField': 'end_date'}"/>
            </form>
        `,
    });
}

test("CallDebrief: basic render without artifacts", async () => {
    const pyEnv = await startServer();
    const discussCallHistoryId = pyEnv["discuss.call.history"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:00:10",
        artifact_ids: [],
    });
    await start();
    await _openDebriefView(pyEnv, discussCallHistoryId);

    // No media artifacts, hence the timeline should not be rendered
    expect(".o-CallDebriefTimeline").toHaveCount(0);
    expect(".text-danger").toHaveCount(0);
});

test("CallDebrief: renders video with playback", async () => {
    _setupCallDebriefPatch();

    const pyEnv = await startServer();

    const videoId = _createRecording(pyEnv, { start: 0, type: "video" });

    const discussCallHistoryId = pyEnv["discuss.call.history"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:01:00", // 60s call
        artifact_ids: [videoId],
    });

    await start();
    await _openDebriefView(pyEnv, discussCallHistoryId);

    expect(".o-CallDebrief-media-container").not.toHaveClass(
        "o-CallDebrief-media-container--no-video"
    );
    expect(".o-CallDebrief-video video").toHaveCount(1);

    // Mute first to avoid noise
    await click("button.o-CallDebrief-muteBtn");

    // Start playback
    const video = queryOne("video");
    const playingPromise = new Promise((r) => video.addEventListener("playing", r, { once: true }));
    await click(".fa-play");
    await animationFrame();
    expect(".fa-pause").toHaveCount(1);

    // Wait for actual playback to start before pausing
    await playingPromise;

    // Stop playback to avoid AbortError when the test destroys the video element
    await click(".fa-pause");
    await animationFrame();
});

test("CallDebrief: timeline-media synchronization", async () => {
    _setupCallDebriefPatch();
    const pyEnv = await startServer();

    // Create 3 segments of 60s each = 180s total duration
    const art1 = _createRecording(pyEnv, { start: 0, type: "audio" });
    const art2 = _createRecording(pyEnv, { start: 60, type: "audio" });
    const art3 = _createRecording(pyEnv, { start: 120, type: "audio" });

    const discussCallHistoryId = pyEnv["discuss.call.history"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:03:00",
        artifact_ids: [art1, art2, art3],
    });

    await start();
    await _openDebriefView(pyEnv, discussCallHistoryId);

    // Move playhead -> Seeks audio
    // Clicking the timeline defaults to center (50%). Total duration 180s -> 90s (01:30).
    await click(".o-CallDebriefTimeline");
    await animationFrame();

    // Manually trigger loadeddata to ensure the seek callback runs immediately
    queryOne("audio").dispatchEvent(new Event("loadeddata"));
    await animationFrame();

    const timestampText = queryOne(".o-CallDebriefTimeline-timestamp").innerText;
    const [minutes, seconds] = timestampText.split(":").map(Number);
    const totalSeconds = minutes * 60 + seconds;
    expect(Math.abs(totalSeconds - 90) <= 2).toBe(true, {
        message: "Playhead should move close to 90s (01:30), but was " + timestampText,
    });

    // Global 90s is 30s relative to Segment 2 (starts at 60s)
    const audioTime2 = queryOne("audio").currentTime;
    expect(Math.abs(audioTime2 - 30) <= 1).toBe(true, {
        message: "Audio currentTime should be close to 30s, but was " + audioTime2,
    });

    // Media timestamp change (simulates playing) -> Updates playhead position
    const audio = queryOne("audio");
    audio.currentTime = 6;
    // Wait for the seek to complete so the 'seeking' flag becomes false
    await new Promise((r) => audio.addEventListener("seeked", r, { once: true }));
    audio.dispatchEvent(new Event("timeupdate"));
    await animationFrame();

    const finalTimestampText = queryOne(".o-CallDebriefMediaControls-timeLabel .o_current_time").innerText;
    const [finalM, finalS] = finalTimestampText.split(":").map(Number);
    const finalTotalSeconds = finalM * 60 + finalS;
    // Segment 2 starts at 60s, so 60 + 6 = 66s (01:06)
    expect(Math.abs(finalTotalSeconds - 66) <= 1).toBe(true, {
        message: "Timestamp should be close to 66s (01:06), but was " + finalTimestampText,
    });
});
