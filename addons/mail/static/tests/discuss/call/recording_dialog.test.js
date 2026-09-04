import { click, contains, defineMailModels, start } from "@mail/../tests/mail_test_helpers";
import { RecordingDialog } from "@mail/discuss/call/common/recording_dialog";

import { describe, expect, test } from "@odoo/hoot";
import { getService, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

function configureRecording() {
    const rtc = getService("discuss.rtc");
    rtc.canRecordAudio = true;
    rtc.canRecordTranscription = true;
    rtc.canRecordVideo = true;
    return rtc;
}

async function openRecordingDialog() {
    getService("dialog").add(RecordingDialog, {});
    await contains(".o-discuss-RecordingDialog");
}

test("video records audio and video", async () => {
    await start();
    const rtc = configureRecording();
    patchWithCleanup(rtc, {
        startRecordingDebounce(options) {
            expect(options).toEqual({ audio: true, transcription: false, video: true });
            expect.step("start recording");
        },
    });

    await openRecordingDialog();
    await contains(".o-discuss-RecordingDialog .o-checkbox", { count: 2 });
    await contains(".o-discuss-RecordingDialog :text('Generate recording file')", { count: 0 });
    await contains(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input:checked"
    );
    await contains(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription')) input:not(:checked)"
    );
    await click(".o-discuss-RecordingDialog button:text('Start recording')");
    expect.verifySteps(["start recording"]);
});

test("transcription can be selected with or without video", async () => {
    await start();
    const rtc = configureRecording();
    patchWithCleanup(rtc, {
        startRecordingDebounce(options) {
            expect(options).toEqual({ audio: false, transcription: true, video: false });
            expect.step("start transcription");
        },
    });

    await openRecordingDialog();
    await click(".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription')) input");
    await contains(".o-discuss-RecordingDialog .o-checkbox input:checked", { count: 2 });
    await click(".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input");
    await contains(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription')) input:checked"
    );
    await contains(
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input:not(:checked)"
    );
    await click(".o-discuss-RecordingDialog button:text('Start recording')");
    expect.verifySteps(["start transcription"]);
});

test("start is disabled without a selected output", async () => {
    await start();
    configureRecording();

    await openRecordingDialog();
    await click(".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video')) input");
    await contains(".o-discuss-RecordingDialog .o-checkbox input:checked", { count: 0 });
    await contains(".o-discuss-RecordingDialog button:text('Start recording'):disabled");
});

test("audio-only permission can stop a legacy cycle but cannot start one", async () => {
    await start();
    const rtc = getService("discuss.rtc");
    rtc.canRecordAudio = true;

    expect(rtc.canRecord).toBe(false);
    rtc.recordingState = {
        audio: true,
        recording: true,
        transcription: false,
        video: false,
    };
    expect(rtc.canRecord).toBe(true);
});

test("active recording keeps video immutable and transcription reactive", async () => {
    await start();
    const rtc = configureRecording();
    rtc.recordingState = {
        audio: false,
        recording: true,
        transcription: true,
        video: false,
    };
    patchWithCleanup(rtc, {
        startRecordingDebounce(options) {
            expect(options).toEqual({ transcription: true });
            expect.step("update transcription");
        },
    });

    await openRecordingDialog();
    await contains(".o-discuss-RecordingDialog span:text('Transcription in progress')");
    await contains(".o-discuss-RecordingDialog :text('Audio recording')", { count: 0 });
    const videoOption = ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record video'))";
    await contains(`${videoOption} input:disabled:not(:checked)`);
    await click(videoOption);
    await contains(`${videoOption} input:disabled:not(:checked)`);

    rtc.recordingState = { ...rtc.recordingState, transcription: false };
    const transcriptionOption =
        ".o-discuss-RecordingDialog .o-checkbox:has(:text('Record transcription'))";
    await contains(`${transcriptionOption} input:not(:checked):not(:disabled)`);
    await click(`${transcriptionOption} input`);
    await contains(`${transcriptionOption} input:checked`);
    await click(".o-discuss-RecordingDialog button:text('Update')");
    expect.verifySteps(["update transcription"]);
});
