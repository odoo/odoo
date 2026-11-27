import {
    defineMailModels,
    focus,
    inputFiles,
    mockGetMedia,
    onRpcBefore,
    openDiscuss,
    patchVoiceMessageAudio,
    patchVoicePlayerFile,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import {
    animationFrame,
    describe,
    expect,
    mockDate,
    press,
    queryOne,
    test,
    waitFor,
    waitForNone,
} from "@odoo/hoot";
import { Command, contains, getService, serverState } from "@web/../tests/web_test_helpers";

import { Mp3Encoder } from "@mail/discuss/voice_message/common/mp3_encoder";
import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { patchable } from "@mail/discuss/voice_message/common/voice_recorder";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

test("make voice message in chat", async () => {
    const file = new File([new Uint8Array(25000)], "test.mp3", { type: "audio/mp3" });
    const { promise: voicePlayerDrawn, resolve: resolveVoicePlayerDrawn } = Promise.withResolvers();
    patch(Mp3Encoder.prototype, {
        encode() {},
        finish() {
            return Array(500).map(() => new Int8Array());
        },
    });
    patch(patchable, { makeFile: () => file });
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    patch(VoicePlayer.prototype, {
        async drawWave(...args) {
            const res = await super.drawWave(...args);
            resolveVoicePlayerDrawn();
            return res;
        },
    });
    mockGetMedia();
    const resources = patchVoiceMessageAudio();
    patch(AudioContext.prototype, {
        resume() {
            // Simulate a long delay for 'resume' to resolve
            return new Promise(() => {});
        },
    });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    await start();
    await openDiscuss(channelId);
    await loadLamejs(); // simulated AudioProcess.process() requires lamejs fully loaded
    await contains(".o-mail-Composer button[title='More Actions']:count(1)").click();
    await waitFor(".dropdown-item:contains('Voice Message'):count(1)");
    mockDate("2023-07-31 13:00:00");
    await contains(".dropdown-item:contains('Voice Message'):count(1)").click();
    await waitFor(".o-mail-VoiceRecorder:text('00 : 00'):count(1)");
    /**
     * Simulate 10 sec elapsed.
     * `patchDate` does not freeze the time, it merely changes the value of "now" at the time it was
     * called. The code of click following the first `patchDate` doesn't actually happen at the time
     * that was specified, but few miliseconds later (8 ms on my machine).
     * The process following the next `patchDate` is intended to be between 10s and 11s later than
     * the click, because the test wants to assert a 10 sec counter, and the two dates are
     * substracted and then rounded down in the code (it means absolute values are irrelevant here).
     * The problem with aiming too close to a 10s difference is that if the click is longer than
     * the following process, it will round down to 9s.
     * The problem with aiming too close to a 11s difference is that if the click is shorter than
     * the following process, it will round down to 11s.
     * The best bet is therefore to use 10s + 500ms difference.
     */
    mockDate("2023-07-31 13:00:10.500");
    // simulate some microphone data
    resources.audioProcessor.process([[new Float32Array(128)]]);
    await waitFor(".o-mail-VoiceRecorder:text('00 : 10')");
    await contains(".o-mail-Composer button[title='Stop Recording']:count(1)").click();
    await waitFor(".o-mail-VoicePlayer:count(1)");
    // wait for audio stream decode + drawing of waves
    await voicePlayerDrawn;
    await waitFor(".o-mail-VoicePlayer button[title='Play']:count(1)");
    await waitFor(".o-mail-VoicePlayer canvas:count(2)"); // 1 for global waveforms, 1 for played waveforms
    await waitFor(".o-mail-VoicePlayer-time:text('00 : 00 / 00 : 03'):count(1)"); // duration of call-invitation.mp3
    await contains(".o-mail-Composer button[title='More Actions']:count(1)").click();
    await waitFor(".dropdown-item:contains('Attach Files'):count(1)"); // check menu loaded
    await waitForNone(".dropdown-item:contains('Voice Message')"); // only 1 voice message at a time
});

function mockVoiceRecording() {
    mockGetMedia();
    patchVoiceMessageAudio();
    patch(Mp3Encoder.prototype, {
        encode() {},
        finish() {
            return Array(500).map(() => new Int8Array());
        },
    });
    const file = new File([new Uint8Array(25000)], "test.mp3", { type: "audio/mp3" });
    patch(patchable, { makeFile: () => file });
}

async function startVoiceRecording(composerSelector = ".o-mail-Composer") {
    await contains(`${composerSelector} button[title='More Actions']:count(1)`).click();
    await contains(".dropdown-item:contains('Voice Message'):count(1)").click();
    await waitFor(".o-mail-VoiceRecorder button[title='Stop Recording']:enabled:count(1)");
    await focus(`${composerSelector} .o-mail-Composer-html`);
}

test("pressing Enter while recording sends the voice message with the text", async () => {
    mockVoiceRecording();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await startVoiceRecording();
    await press("Enter");
    await waitFor(".o-mail-Message:contains(Hello):has(.o-mail-VoicePlayer):count(1)");
    await waitForNone(".o-mail-VoiceRecorder");
});

test("recording in a chat window shows the recorder above the input", async () => {
    mockVoiceRecording();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    setupChatHub({ opened: [channelId] });
    await start();
    await insertTextInComposer(".o-mail-ChatWindow .o-mail-Composer", "Hello");
    await startVoiceRecording(".o-mail-ChatWindow .o-mail-Composer");
    await waitFor(".o-mail-Composer-coreHeader .o-mail-VoiceRecorder:count(1)");
    await press("Enter");
    await waitFor(
        ".o-mail-ChatWindow .o-mail-Message:contains(Hello):has(.o-mail-VoicePlayer):count(1)"
    );
    await waitForNone(".o-mail-VoiceRecorder");
});

test("pressing Escape while recording discards the recording", async () => {
    mockVoiceRecording();
    onRpcBefore("/mail/attachment/upload", () => expect.step("upload"));
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await startVoiceRecording();
    await press("Escape");
    await waitForNone(".o-mail-VoiceRecorder");
    await animationFrame();
    expect.verifySteps([]);
});

test.tags("html composer");
test("pressing Escape with emoji suggestions open keeps the recording", async () => {
    mockVoiceRecording();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    getService("mail.composer").setHtmlComposer();
    await openDiscuss(channelId);
    await startVoiceRecording();
    await insertTextInComposer(".o-mail-Composer", ":smil");
    await waitFor(".o-we-SuggestionList .o-navigable:has(:text('😃')):count(1)");
    await press("Escape");
    await waitForNone(".o-we-SuggestionList");
    await waitFor(".o-mail-VoiceRecorder:count(1)");
});

test("sending while recording keeps the text when the voice message fails to upload", async () => {
    mockVoiceRecording();
    onRpcBefore("/mail/attachment/upload", () => {
        expect.step("upload");
        return { error: "Upload failed" };
    });
    onRpcBefore("/mail/message/post", () => expect.step("message_post"));
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await startVoiceRecording();
    await press("Enter");
    await waitForNone(".o-mail-VoiceRecorder");
    await expect.waitForSteps(["upload"]);
    await animationFrame();
    expect.verifySteps([]);
    await waitFor(".o-mail-Composer-html:text('Hello'):count(1)");
});

test("pressing Enter while recording in an edited message saves the voice message with it", async () => {
    mockVoiceRecording();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message").hover();
    await contains(".o-mail-Message [title='Expand']").click();
    await contains(".o-dropdown-item:contains('Edit'):count(1)").click();
    await startVoiceRecording(".o-mail-Message .o-mail-Composer");
    await press("Enter");
    await waitFor(
        ".o-mail-Message:not(.o-editing):contains(Hello):has(.o-mail-VoicePlayer):count(1)"
    );
    await waitForNone(".o-mail-VoiceRecorder");
});

test("pressing Enter while recording waits until the other attachments are uploaded", async () => {
    const { promise: uploaded, resolve: resolveUploaded } = Promise.withResolvers();
    mockVoiceRecording();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    onRpcBefore("/mail/attachment/upload", async () => await uploaded);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [
        new File(["hello, world"], "text.txt", { type: "text/plain" }),
    ]);
    await waitFor(".o-mail-AttachmentContainer.o-isUploading:contains(text.txt):count(1)");
    await startVoiceRecording();
    await press("Enter");
    await animationFrame();
    expect(".o-mail-VoiceRecorder").toHaveCount(1);
    resolveUploaded();
    await waitForNone(".o-mail-AttachmentContainer.o-isUploading");
    await press("Enter");
    await waitFor(".o-mail-Message:contains(text.txt):has(.o-mail-VoicePlayer):count(1)");
});

test("sending and discarding are ignored while the recorder is still starting", async () => {
    const { promise: workletLoaded, resolve: resolveWorkletLoaded } = Promise.withResolvers();
    mockVoiceRecording();
    patch(window, {
        AudioContext: class extends window.AudioContext {
            audioWorklet = { addModule: () => workletLoaded };
        },
    });
    onRpcBefore("/mail/message/post", () => expect.step("message_post"));
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertTextInComposer(".o-mail-Composer", "Hello");
    await contains(".o-mail-Composer button[title='More Actions']:count(1)").click();
    await contains(".dropdown-item:contains('Voice Message'):count(1)").click();
    await waitFor(".o-mail-Composer button[title='Send']:disabled:count(1)");
    await focus(".o-mail-Composer-html");
    await press("Enter");
    await press("Escape");
    await animationFrame();
    expect.verifySteps([]);
    resolveWorkletLoaded();
    await waitFor(".o-mail-VoiceRecorder button[title='Stop Recording']:enabled:count(1)");
});

test("playback rate control is only shown on voice messages", async () => {
    patchVoiceMessageAudio();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "channel", name: "General" });
    pyEnv["mail.message"].create([
        {
            attachment_ids: [
                Command.create({
                    mimetype: "audio/mpeg",
                    res_id: channelId,
                    res_model: "discuss.channel",
                    voice_ids: [Command.create({})],
                }),
            ],
            body: "Voice message",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
        {
            attachment_ids: [
                Command.create({
                    mimetype: "audio/mpeg",
                    res_id: channelId,
                    res_model: "discuss.channel",
                }),
            ],
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-AttachmentContainer:count(2)");
    await waitFor(".o-mail-VoicePlaybackRate:count(1)");
    await waitFor(".o-mail-Message:has(:text('Voice message')) .o-mail-VoicePlaybackRate:count(1)");
});

test("can change voice message playback speed and replay it once it ends", async () => {
    patchVoiceMessageAudio();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "channel", name: "General" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            Command.create({
                mimetype: "audio/mpeg",
                res_id: channelId,
                res_model: "discuss.channel",
                voice_ids: [Command.create({})],
            }),
        ],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-VoicePlayer-time:text('00 : 00 / 00 : 03'):count(1)"); // duration of call-invitation.mp3
    await contains(".o-mail-VoicePlayer button[title='Play']:count(1)").click();
    await waitFor(".o-mail-VoicePlayer button[title='Pause']:count(1)");
    await waitFor("button[title='Playback speed']:text('1x'):count(1)");
    await contains("button[title='Playback speed']:count(1)").click();
    await waitFor("button[title='Playback speed']:text('1.25x'):count(1)");
    const audio = queryOne(".o-mail-VoicePlayer audio");
    expect(audio.playbackRate).toBe(1.25);
    audio.currentTime = 3; // jump to the end of playback so replay has to rewind to 00 : 00
    audio.pause(); // stop playback, as browsers do when the audio ends
    audio.dispatchEvent(new Event("ended"));
    await contains(".o-mail-VoicePlayer button[title='Replay']:count(1)").click();
    await waitFor(".o-mail-VoicePlayer-time:text('00 : 00 / 00 : 03'):count(1)");
    await waitFor(".o-mail-VoicePlayer button[title='Pause']:count(1)");
});
