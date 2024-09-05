import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, globals, test } from "@odoo/hoot";
import { Deferred, mockDate } from "@odoo/hoot-mock";
import { Command, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { browser } from "@web/core/browser/browser";

/** @type {AudioWorkletNode} */
let audioProcessor;

describe.current.tags("desktop");
defineMailModels();

function patchAudio() {
    const {
        AnalyserNode,
        AudioBufferSourceNode,
        AudioContext,
        AudioWorkletNode,
        GainNode,
        MediaStreamAudioSourceNode,
    } = browser;
    Object.assign(browser, {
        AnalyserNode: class {
            connect() {}
            disconnect() {}
        },
        AudioBufferSourceNode: class {
            buffer;
            constructor() {}
            connect() {}
            disconnect() {}
            start() {}
            stop() {}
        },
        AudioContext: class {
            audioWorklet;
            currentTime;
            destination;
            sampleRate;
            state;
            constructor() {
                this.audioWorklet = {
                    addModule(url) {},
                };
            }
            close() {}
            /** @returns {AnalyserNode} */
            createAnalyser() {
                return new browser.AnalyserNode();
            }
            /** @returns {AudioBufferSourceNode} */
            createBufferSource() {
                return new browser.AudioBufferSourceNode();
            }
            /** @returns {GainNode} */
            createGain() {
                return new browser.GainNode();
            }
            /** @returns {MediaStreamAudioSourceNode} */
            createMediaStreamSource(microphone) {
                return new browser.MediaStreamAudioSourceNode();
            }
            /** @returns {AudioBuffer} */
            decodeAudioData(...args) {
                return new AudioContext().decodeAudioData(...args);
            }
        },
        AudioWorkletNode: class {
            port;
            constructor(audioContext, processorName) {
                this.port = {
                    onmessage(e) {},
                    postMessage(data) {
                        this.onmessage({ data, timeStamp: new Date().getTime() });
                    },
                };
                audioProcessor = this;
            }
            connect() {
                this.port.postMessage();
            }
            disconnect() {}
            process(allInputs) {
                const inputs = allInputs[0][0];
                this.port.postMessage(inputs);
                return true;
            }
        },
        GainNode: class {
            connect() {}
            close() {}
            disconnect() {}
        },
        MediaStreamAudioSourceNode: class {
            connect(processor) {}
            disconnect() {}
        },
    });
    return () => {
        Object.assign(browser, {
            AnalyserNode,
            AudioBufferSourceNode,
            AudioContext,
            AudioWorkletNode,
            GainNode,
            MediaStreamAudioSourceNode,
        });
    };
}

test("make voice message in chat", async () => {
    const file = new File([new Uint8Array(25000)], "test.mp3", { type: "audio/mp3" });
    const voicePlayerDrawing = new Deferred();
    patchWithCleanup(VoiceRecorder.prototype, {
        _encode() {},
        _getEncoderBuffer() {
            return Array(500).map(() => new Int8Array());
        },
        _makeFile() {
            return file;
        },
    });
    patchWithCleanup(VoicePlayer.prototype, {
        async drawWave(...args) {
            voicePlayerDrawing.resolve();
            return super.drawWave(...args);
        },
        async fetchFile() {
            return super.fetchFile("/mail/static/src/audio/call_02_in_.mp3");
        },
        _fetch(url) {
            if (url.includes("call_02_in_.mp3")) {
                const realFetch = globals.fetch;
                return realFetch(...arguments);
            }
            return super._fetch(...arguments);
        },
    });
    mockGetMedia();
    const cleanUp = patchAudio();
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
    await contains("button[title='Voice Message']");
    mockDate("2023-07-31 13:00:00");
    await click("button[title='Voice Message']");
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
    audioProcessor.process([[new Float32Array(128)]]);
    await contains(".o-mail-VoiceRecorder", { text: "00 : 10" });
    await click("button[title='Stop Recording']");
    await contains(".o-mail-VoicePlayer");
    // wait for audio stream decode + drawing of waves
    await voicePlayerDrawing;
    await contains(".o-mail-VoicePlayer button[title='Play']");
    await contains(".o-mail-VoicePlayer canvas", { count: 2 }); // 1 for global waveforms, 1 for played waveforms
    await contains(".o-mail-VoicePlayer", { text: "00 : 04" }); // duration of call_02_in_.mp3
    await contains("button[title='Voice Message']:disabled");
    cleanUp();
});
