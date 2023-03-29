/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";
import {
    click,
    createFile,
    mockGetMedia,
    nextAnimationFrame,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { url } from "@web/core/utils/urls";

QUnit.module("voice message");

let audioProcessor;

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

QUnit.test("make voice message in chat", async (assert) => {
    const file = await createFile({
        content: Array(500).map(() => new Int8Array()), // some non-empty content
        contentType: "audio/mp3",
        name: "test.mp3",
        size: 25_000,
    });
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
            return super.fetchFile(url("/mail/static/src/audio/call_02_in_.mp3"));
        },
    });
    patchDate(2023, 6, 31, 13, 0, 0);
    mockGetMedia();
    const cleanUp = patchAudio();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "chat",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, "button[title='Voice Message']");
    await click("button[title='Voice Message']");
    assert.containsOnce($, ".o-mail-VoiceRecorder");
    assert.containsOnce($, ".o-mail-VoiceRecorder:contains(00 : 00)");
    // simulate 10 sec elapsed
    patchDate(2023, 6, 31, 13, 0, 11); // +1 so exactly 10 sec elapsed
    // simulate some microphone data
    audioProcessor.process([[new Float32Array(128)]]);
    await waitUntil(".o-mail-VoiceRecorder:contains(00 : 10)");
    assert.containsOnce($, "button[title='Stop Recording']");
    await click("button[title='Stop Recording']");
    assert.containsOnce($, ".o-mail-VoicePlayer");
    // wait for audio stream decode + drawing of waves
    await voicePlayerDrawing;
    await nextAnimationFrame();
    assert.containsOnce($, ".o-mail-VoicePlayer button[title='Play']");
    assert.containsN($, ".o-mail-VoicePlayer canvas", 2); // 1 for global waveforms, 1 for played waveforms
    assert.containsOnce($, ".o-mail-VoicePlayer:contains(00 : 04)"); // duration of call_02_in_.mp3
    assert.containsOnce($, ".o-mail-VoiceRecorder button[title='Voice Message']");
    assert.ok($(".o-mail-VoiceRecorder button[title='Voice Message']")[0].disabled);
    cleanUp();
});
