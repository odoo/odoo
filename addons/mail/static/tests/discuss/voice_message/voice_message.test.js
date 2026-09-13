import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchVoiceMessageAudio,
    patchVoicePlayerFile,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, mockDate, queryOne, test, waitFor } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

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
    await click(".o-mail-Composer button[title='More Actions']");
    await contains(".dropdown-item:contains('Voice Message')");
    mockDate("2023-07-31 13:00:00");
    await click(".dropdown-item:contains('Voice Message')");
    await contains(".o-mail-VoiceRecorder:text('00 : 00')");
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
    await click(".o-mail-Composer button[title='Stop Recording']");
    await contains(".o-mail-VoicePlayer");
    // wait for audio stream decode + drawing of waves
    await voicePlayerDrawn;
    await contains(".o-mail-VoicePlayer button[title='Play']");
    await contains(".o-mail-VoicePlayer canvas", { count: 2 }); // 1 for global waveforms, 1 for played waveforms
    await contains(".o-mail-VoicePlayer-time:text('00 : 00 / 00 : 03')"); // duration of call-invitation.mp3
    await click(".o-mail-Composer button[title='More Actions']");
    await contains(".dropdown-item:contains('Attach Files')"); // check menu loaded
    await contains(".dropdown-item:contains('Voice Message')", { count: 0 }); // only 1 voice message at a time
});

test("voice message controls are not shown on regular audio attachments", async () => {
    patchVoiceMessageAudio();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "channel", name: "General" });
    pyEnv["mail.message"].create([
        {
            attachment_ids: [
                Command.create({
                    mimetype: "audio/mpeg",
                    name: "voicemessage",
                    res_id: channelId,
                    res_model: "discuss.channel",
                    voice_ids: [Command.create({ display_name: "voicemessage" })],
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
                    name: "Audio.mp3",
                    res_id: channelId,
                    res_model: "discuss.channel",
                }),
            ],
            body: "Regular audio",
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentContainer", { count: 2 });
    await contains(".o-mail-VoicePlayerControls", { count: 1 });
    await contains(".o-mail-Message", {
        text: "Voice message",
        contains: [".o-mail-VoicePlayerControls"],
    });
    await contains(".o-mail-Message", {
        text: "Regular audio",
        contains: [".o-mail-AttachmentCard-image.o_image"],
    });
});

test("can change voice message playback speed", async () => {
    patchVoiceMessageAudio();
    patchVoicePlayerFile("/mail/static/src/audio/call-invitation.mp3");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "channel", name: "General" });
    pyEnv["mail.message"].create({
        attachment_ids: [
            Command.create({
                mimetype: "audio/mpeg",
                name: "voicemessage",
                res_id: channelId,
                res_model: "discuss.channel",
                voice_ids: [Command.create({ display_name: "voicemessage" })],
            }),
        ],
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-VoicePlayer-time:text('00 : 00 / 00 : 03')"); // duration of call-invitation.mp3
    await click(".o-mail-VoicePlayer button[title='Play']");
    await contains(".o-mail-VoicePlayer button[title='Pause']");
    await contains("button[title='Playback speed']:contains('1x')");
    await click("button[title='Playback speed']");
    await contains("button[title='Playback speed']:contains('1.25x')");
    expect(queryOne(".o-mail-VoicePlayer audio").playbackRate).toBe(1.25);
    queryOne(".o-mail-VoicePlayer audio").dispatchEvent(new Event("ended"));
    await contains(".o-mail-VoicePlayer button[title='Replay']");
});
