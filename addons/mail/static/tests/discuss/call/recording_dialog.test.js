import { click, defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { RecordingDialog } from "@mail/discuss/call/common/recording_dialog";

import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { getService } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

function configureRecording() {
    const rtc = getService("discuss.rtc");
    rtc.can_record_audio = true;
    rtc.can_record_transcription = true;
    rtc.can_record_video = true;
    return rtc;
}

async function openRecordingDialog() {
    getService("dialog").add(RecordingDialog, {});
    await waitFor(".o-discuss-RecordingDialog:count(1)");
}

test("video records audio and video", async () => {
    await start();
    const rtc = configureRecording();
    patch(rtc, {
        setRecording(options) {
            expect(options).toEqual({ audio: true, transcription: false, video: true });
            expect.step("start recording");
        },
    });

    await openRecordingDialog();
    await waitFor(".o-discuss-RecordingDialog .o-checkbox:count(2)");
    await waitForNone(".o-discuss-RecordingDialog :text('Generate recording file')");
    await waitFor(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input:checked:count(1)"
    );
    await waitFor(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription')) input:not(:checked):count(1)"
    );
    await click(".o-discuss-RecordingDialog button:text('Start recording')");
    expect.verifySteps(["start recording"]);
});

test("transcription can be selected with or without video", async () => {
    await start();
    const rtc = configureRecording();
    patch(rtc, {
        setRecording(options) {
            expect(options).toEqual({ audio: false, transcription: true, video: false });
            expect.step("start transcription");
        },
    });

    await openRecordingDialog();
    await click(".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription')) input");
    await waitFor(".o-discuss-RecordingDialog .o-checkbox input:checked:count(2)");
    await click(".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input");
    await waitFor(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription')) input:checked:count(1)"
    );
    await waitFor(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input:not(:checked):count(1)"
    );
    await click(".o-discuss-RecordingDialog button:text('Start recording')");
    expect.verifySteps(["start transcription"]);
});

test("start is disabled without a selected output", async () => {
    await start();
    configureRecording();

    await openRecordingDialog();
    await click(".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input");
    await waitForNone(".o-discuss-RecordingDialog .o-checkbox input:checked");
    await waitFor(".o-discuss-RecordingDialog button:text('Start recording'):disabled:count(1)");
});

test("audio-only permission can stop a legacy cycle but cannot start one", async () => {
    await start();
    const rtc = getService("discuss.rtc");
    rtc.can_record_audio = true;

    expect(rtc.canRecord()).toBe(false);
    rtc.recordingState = {
        audio: true,
        transcription: false,
        video: false,
    };
    expect(rtc.canRecord()).toBe(true);
});

test("active recording keeps video immutable and transcription reactive", async () => {
    await start();
    const rtc = configureRecording();
    rtc.recordingState = {
        audio: true,
        transcription: true,
        video: false,
    };
    patch(rtc, {
        setRecording(options) {
            expect(options).toEqual({ transcription: true });
            expect.step("update transcription");
        },
    });
    await openRecordingDialog();
    await waitFor(".o-discuss-RecordingDialog span:text('Transcription in progress'):count(1)");
    await waitForNone(".o-discuss-RecordingDialog :text('Audio recording')");
    const videoOption = ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video'))";
    await waitFor(`${videoOption} input:disabled:not(:checked):count(1)`);
    await click(videoOption);
    await waitFor(`${videoOption} input:disabled:not(:checked):count(1)`);
    rtc.recordingState = { ...rtc.recordingState, transcription: false };
    const transcriptionOption =
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription'))";
    await waitFor(`${transcriptionOption} input:not(:checked):not(:disabled):count(1)`);
    await click(`${transcriptionOption} input`);
    await waitFor(`${transcriptionOption} input:checked:count(1)`);
    await click(".o-discuss-RecordingDialog button:text('Update')");
    expect.verifySteps(["update transcription"]);
});

test("transcription-only recording must be stopped instead of updated", async () => {
    await start();
    const rtc = configureRecording();
    rtc.recordingState = {
        audio: false,
        transcription: true,
        video: false,
    };
    patch(rtc, {
        setRecording(options) {
            expect(options).toEqual({ audio: false, transcription: false, video: false });
            expect.step("stop recording");
        },
    });
    await openRecordingDialog();
    const transcriptionOption =
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription'))";
    await waitFor(`${transcriptionOption} input:checked:disabled:count(1)`);
    await waitForNone(".o-discuss-RecordingDialog button:text('Update')");
    await click(".o-discuss-RecordingDialog button:text('Stop recording')");
    expect.verifySteps(["stop recording"]);
});
