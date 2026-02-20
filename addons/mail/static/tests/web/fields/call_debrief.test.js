/** @odoo-module **/

import { expect, describe, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { click, queryAll, queryOne } from "@odoo/hoot-dom";
import { startServer, start, openFormView, mailModels } from "@mail/../tests/mail_test_helpers";
import { fields, models, defineModels, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CallDebrief } from "@mail/views/fields/call_debrief/call_debrief";

describe.current.tags("desktop");

class CallArtifact extends models.Model {
    _name = "call.artifact";

    transcript = fields.Text();
    is_stt = fields.Boolean();
    media_id = fields.Many2one({ relation: "ir.attachment" });
    start_ms = fields.Integer();
    end_ms = fields.Integer();
    call_id = fields.Many2one({ relation: "voip.call" });
}

class VoipCall extends models.Model {
    _name = "voip.call";

    start_date = fields.Datetime();
    end_date = fields.Datetime();
    artifact_ids = fields.One2many({ relation: "call.artifact", relation_field: "call_id" });
}

defineModels({ ...mailModels, CallArtifact, VoipCall });

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
        name: `fixture_${start}_${type}.webm`,
        mimetype: type === "video" ? "video/webm" : "audio/webm",
    });
    return pyEnv["call.artifact"].create({
        media_id: attachmentId,
        is_stt: false,
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

async function _openDebriefView(pyEnv, voipCallId) {
    await openFormView("voip.call", voipCallId, {
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
    const voipCallId = pyEnv["voip.call"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:00:10",
        artifact_ids: [],
    });
    await start();
    await _openDebriefView(pyEnv, voipCallId);

    const labels = queryAll(".o-CallDebriefTimeline-labels span");
    expect(labels[0]).toHaveText("00:00");
    expect(labels[1]).toHaveText("00:10");
});

test("CallDebrief: transcript only interactions", async () => {
    const pyEnv = await startServer();
    const voipCallId = pyEnv["voip.call"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:00:10",
        artifact_ids: [
            pyEnv["call.artifact"].create({
                transcript: "1\n00:00:01,000 --> 00:00:03,000\nHello world",
                is_stt: true,
                start_ms: 0,
                end_ms: 10000,
            }),
        ],
    });
    await start();
    await _openDebriefView(pyEnv, voipCallId);

    expect(".o-CallDebrief-media-container").toHaveClass("o-CallDebrief-media-container--no-video");

    const line = queryOne("p[data-timestamp]");
    await click(line);
    await animationFrame();
    expect(".o-CallDebriefTimeline-playhead-timestamp").toHaveText("00:01");
});

test("CallDebrief: renders video and transcript with playback", async () => {
    _setupCallDebriefPatch();

    const pyEnv = await startServer();

    // Create artifacts: 1 transcript, 1 video (60s)
    const transcriptId = pyEnv["call.artifact"].create({
        transcript: "1\n00:00:01,000 --> 00:00:03,000\nHello world",
        is_stt: true,
        start_ms: 0,
        end_ms: 60000,
    });

    const videoId = _createRecording(pyEnv, { start: 0, type: "video" });

    const voipCallId = pyEnv["voip.call"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:01:00", // 60s call
        artifact_ids: [transcriptId, videoId],
    });

    await start();
    await _openDebriefView(pyEnv, voipCallId);

    expect(".o-CallDebrief-media-container").not.toHaveClass(
        "o-CallDebrief-media-container--no-video"
    );
    expect(".o-CallDebrief-video video").toHaveCount(1);

    // Mute first to avoid noise
    await click("button[title*='Mute']");

    // Start playback
    await click(".fa-play");
    await animationFrame();
    expect(".fa-pause").toHaveCount(1);
});

test("CallDebrief: timeline-transcript-media synchronization", async () => {
    _setupCallDebriefPatch();
    const pyEnv = await startServer();

    // Create 3 segments of 60s each = 180s total duration
    const art1 = _createRecording(pyEnv, { start: 0, type: "audio" });
    const art2 = _createRecording(pyEnv, { start: 60, type: "audio" });
    const art3 = _createRecording(pyEnv, { start: 120, type: "audio" });

    // Transcripts associated with each segment time range
    const trans1 = pyEnv["call.artifact"].create({
        transcript: "1\n00:00:05,000 --> 00:00:08,000\nSegment 1 Text",
        is_stt: true,
        start_ms: 0,
        end_ms: 60000,
    });
    const trans2 = pyEnv["call.artifact"].create({
        // Relative 2s -> Global 62s
        transcript: "1\n00:00:02,000 --> 00:00:04,000\nSegment 2 Text",
        is_stt: true,
        start_ms: 60000,
        end_ms: 120000,
    });
    const trans3 = pyEnv["call.artifact"].create({
        // Relative 5s -> Global 125s
        transcript: "1\n00:00:05,000 --> 00:00:07,000\nSegment 3 Text",
        is_stt: true,
        start_ms: 120000,
        end_ms: 180000,
    });

    const voipCallId = pyEnv["voip.call"].create({
        start_date: "2023-01-01 10:00:00",
        end_date: "2023-01-01 10:03:00",
        artifact_ids: [art1, trans1, art2, trans2, art3, trans3],
    });

    await start();
    await _openDebriefView(pyEnv, voipCallId);
    const lines = queryAll("p[data-timestamp]");

    // Select transcript line -> Adjusts playhead and audio
    await click(lines[0]);
    await animationFrame();
    expect(".o-CallDebriefTimeline-playhead-timestamp").toHaveText("00:05");
    expect(lines[0]).toHaveClass("o-CallDebrief-transcript-highlight");
    const audioTime1 = queryOne("audio").currentTime;
    expect(Math.abs(audioTime1 - 5) <= 1).toBe(true, {
        message: `Audio currentTime should be close to 30s, but was ${audioTime1}`,
    });

    // Move playhead -> Seeks audio and scroll to nearest transcript line
    // Clicking the timeline defaults to center (50%). Total duration 180s -> 90s (01:30).
    await click(".o-CallDebriefTimeline");
    await animationFrame();

    // Manually trigger loadeddata to ensure the seek callback runs immediately
    queryOne("audio").dispatchEvent(new Event("loadeddata"));
    await animationFrame();

    const timestampText = queryOne(".o-CallDebriefTimeline-playhead-timestamp").innerText;
    const [minutes, seconds] = timestampText.split(":").map(Number);
    const totalSeconds = minutes * 60 + seconds;
    expect(Math.abs(totalSeconds - 90) <= 2).toBe(true, {
        message: `Playhead should move close to 90s (01:30), but was ${timestampText}`,
    });
    // 90s is closer to Segment 2 (62s) than Segment 3 (125s)
    expect(lines[1]).toHaveClass("o-CallDebrief-transcript-highlight");
    // Global 90s is 30s relative to Segment 2 (starts at 60s)
    const audioTime2 = queryOne("audio").currentTime;
    expect(Math.abs(audioTime2 - 30) <= 1).toBe(true, {
        message: `Audio currentTime should be close to 30s, but was ${audioTime2}`,
    });

    // Media timestamp change (simulates playing) -> Updates playhead position and transcript highlight
    const audio = queryOne("audio");
    audio.currentTime = 6;
    audio.dispatchEvent(new Event("timeupdate"));
    await animationFrame();
    const finalTimestampText = queryOne(".o-CallDebriefTimeline-playhead-timestamp").innerText;
    const [finalM, finalS] = finalTimestampText.split(":").map(Number);
    const finalTotalSeconds = finalM * 60 + finalS;
    // Segment 2 starts at 60s, so 60 + 6 = 66s (01:06)
    expect(Math.abs(finalTotalSeconds - 66) <= 1).toBe(true, {
        message: `Timestamp should be close to 66s (01:06), but was ${finalTimestampText}`,
    });
    // Global 66s is within Segment 2, so the second transcript line (starts at 62s) should be highlighted
    expect(lines[1]).toHaveClass("o-CallDebrief-transcript-highlight");
});
