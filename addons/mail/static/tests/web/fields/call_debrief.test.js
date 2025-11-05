/** @odoo-module **/

import { expect, describe, test } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
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

test("CallDebrief: active call uses the current time", async () => {
    mockDate("2023-01-01 10:02:00", 0);
    _setupCallDebriefPatch();
    const pyEnv = await startServer();
    const artifactId = _createRecording(pyEnv, { start: 60 });
    const discussCallHistoryId = pyEnv["discuss.call.history"].create({
        start_date: "2023-01-01 10:00:00",
        artifact_ids: [artifactId],
    });

    await start();
    await _openDebriefView(pyEnv, discussCallHistoryId);

    expect(".text-danger").toHaveCount(0);
    const segment = queryOne(".o-CallDebriefTimeline-media-segment");
    expect(parseFloat(segment.style.width)).toBeCloseTo(50, { margin: 0.1 });
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
    await click("[data-icon='play_arrow']");
    await animationFrame();
    expect("[data-icon='pause']").toHaveCount(1);
    expect(".o_feedback_indicator [data-icon='play_arrow']").toHaveClass("oi-stack");

    // Wait for actual playback to start before pausing
    await playingPromise;
    const { width, height } = video.getBoundingClientRect();
    expect(width / height).toBeCloseTo(video.videoWidth / video.videoHeight, { margin: 0.01 });

    // Stop playback to avoid AbortError when the test destroys the video element
    await click("[data-icon='pause']");
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
    // One animationFrame: OWL renders new <audio> (segment 2) and useEffect sets currentTime=30
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

    const finalTimestampText = queryOne(
        ".o-CallDebriefMediaControls-timeLabel .o_current_time"
    ).innerText;
    const [finalM, finalS] = finalTimestampText.split(":").map(Number);
    const finalTotalSeconds = finalM * 60 + finalS;
    // Segment 2 starts at 60s, so 60 + 6 = 66s (01:06)
    expect(Math.abs(finalTotalSeconds - 66) <= 1).toBe(true, {
        message: "Timestamp should be close to 66s (01:06), but was " + finalTimestampText,
    });
});

test("CallDebrief: generates silence gaps in timeline", async () => {
    _setupCallDebriefPatch();
    const pyEnv = await startServer();

    // Create a call of 240 seconds total:
    // 0s to 60s: Media 1 (60s duration)
    // 60s to 120s: Silence Gap 1 (60s)
    // 120s to 180s: Media 2 (60s duration)
    // 180s to 240s: Silence Gap 2 (60s)
    const art1 = _createRecording(pyEnv, { start: 0 });
    const art2 = _createRecording(pyEnv, { start: 120 });

    const discussCallHistoryId = pyEnv["discuss.call.history"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:04:00", // 240s total duration
        artifact_ids: [art1, art2],
    });

    await start();
    await _openDebriefView(pyEnv, discussCallHistoryId);

    // Timeline track is rendered
    expect(".o-CallDebriefTimeline-track").toHaveCount(1);

    // There should be 4 segments total:
    // 1. Media segment (0s to 60s) -> 25% width
    // 2. Silence segment (60s to 120s) -> 25% width
    // 3. Media segment (120s to 180s) -> 25% width
    // 4. Silence segment (180s to 240s) -> 25% width
    expect(".o-CallDebriefTimeline-segment").toHaveCount(4);
    expect(".o-CallDebriefTimeline-media-segment").toHaveCount(2);
    expect(".o-CallDebriefTimeline-silence-segment").toHaveCount(2);

    // Verify coordinates
    const segments = document.querySelectorAll(".o-CallDebriefTimeline-segment");
    expect(segments[0].style.width).toBe("25%");
    expect(segments[0].classList.contains("o-CallDebriefTimeline-media-segment")).toBe(true);

    expect(segments[1].style.width).toBe("25%");
    expect(segments[1].classList.contains("o-CallDebriefTimeline-silence-segment")).toBe(true);

    expect(segments[2].style.width).toBe("25%");
    expect(segments[2].classList.contains("o-CallDebriefTimeline-media-segment")).toBe(true);

    expect(segments[3].style.width).toBe("25%");
    expect(segments[3].classList.contains("o-CallDebriefTimeline-silence-segment")).toBe(true);
});
