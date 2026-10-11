import {
    click,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchVoiceMessageAudio,
    patchVoicePlayerFile,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, mockDate, queryOne, test, waitFor, waitForNone } from "@odoo/hoot";
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
    await waitFor(".dropdown-item:contains('Voice Message'):count(1)");
    mockDate("2023-07-31 13:00:00");
    await click(".dropdown-item:contains('Voice Message')");
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
    await click(".o-mail-Composer button[title='Stop Recording']");
    await waitFor(".o-mail-VoicePlayer:count(1)");
    // wait for audio stream decode + drawing of waves
    await voicePlayerDrawn;
    await waitFor(".o-mail-VoicePlayer button[title='Play']:count(1)");
    await waitFor(".o-mail-VoicePlayer canvas:count(2)"); // 1 for global waveforms, 1 for played waveforms
    await waitFor(".o-mail-VoicePlayer-time:text('00 : 00 / 00 : 03'):count(1)"); // duration of call-invitation.mp3
    await click(".o-mail-Composer button[title='More Actions']");
    await waitFor(".dropdown-item:contains('Attach Files'):count(1)"); // check menu loaded
    await waitForNone(".dropdown-item:contains('Voice Message')"); // only 1 voice message at a time
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
    await waitFor(".o-mail-VoicePlayer-time:text('00 : 00 / 00 : 03'):count(1)"); // duration of call-invitation.mp3
    await click(".o-mail-VoicePlayer button[title='Play']");
    await waitFor(".o-mail-VoicePlayer button[title='Pause']:count(1)");
    await waitFor("button[title='Playback speed']:text('1x'):count(1)");
    await click("button[title='Playback speed']");
    await waitFor("button[title='Playback speed']:text('1.25x'):count(1)");
    expect(queryOne(".o-mail-VoicePlayer audio").playbackRate).toBe(1.25);
    queryOne(".o-mail-VoicePlayer audio").dispatchEvent(new Event("ended"));
    await waitFor(".o-mail-VoicePlayer button[title='Replay']:count(1)");
});
