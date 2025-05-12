import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchVoiceMessageAudio,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, globals, test } from "@odoo/hoot";
import { Deferred, mockDate } from "@odoo/hoot-mock";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { patchable } from "@mail/discuss/voice_message/common/voice_recorder";
import { Mp3Encoder } from "@mail/discuss/voice_message/common/mp3_encoder";

describe.current.tags("desktop");
defineMailModels();

test("make voice message in chat", async () => {
    const file = new File([new Uint8Array(25000)], "test.mp3", { type: "audio/mp3" });
    const voicePlayerDrawing = new Deferred();
    patchWithCleanup(Mp3Encoder.prototype, {
        encode() {},
        finish() {
            return Array(500).map(() => new Int8Array());
        },
    });
    patchWithCleanup(patchable, { makeFile: () => file });
    patchWithCleanup(VoicePlayer.prototype, {
        async drawWave(...args) {
            voicePlayerDrawing.resolve();
            return super.drawWave(...args);
        },
        async fetchFile() {
            return super.fetchFile("/mail/static/src/audio/call-invitation.mp3");
        },
        _fetch(url) {
            if (url.includes("call-invitation.mp3")) {
                const realFetch = globals.fetch;
                return realFetch(...arguments);
            }
            return super._fetch(...arguments);
        },
    });
    mockGetMedia();
    const resources = patchVoiceMessageAudio();
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
    await contains(".o-mail-VoiceRecorder", { text: "00 : 00" });
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
    await contains(".o-mail-VoiceRecorder", { text: "00 : 10" });
    await click(".o-mail-Composer button[title='Stop Recording']");
    await contains(".o-mail-VoicePlayer");
    // wait for audio stream decode + drawing of waves
    await voicePlayerDrawing;
    await contains(".o-mail-VoicePlayer button[title='Play']");
    await contains(".o-mail-VoicePlayer canvas", { count: 2 }); // 1 for global waveforms, 1 for played waveforms
    await contains(".o-mail-VoicePlayer", { text: "00 : 03" }); // duration of call-invitation_.mp3
    await click(".o-mail-Composer button[title='More Actions']");
    await contains(".dropdown-item:contains('Attach Files')"); // check menu loaded
    await contains(".dropdown-item:contains('Voice Message')", { count: 0 }); // only 1 voice message at a time
});
