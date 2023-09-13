/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { Command } from "@mail/../tests/helpers/command";
import { mockGetMedia, start } from "@mail/../tests/helpers/test_utils";

import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { url } from "@web/core/utils/urls";
import { patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains, createFile } from "@web/../tests/utils";

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

QUnit.test("make voice message in chat", async () => {
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
    openDiscuss(channelId);
    await click("button[title='Voice Message']");
    await contains(".o-mail-VoiceRecorder", { text: "00 : 00" });
    await Promise.resolve();
    // simulate 10 sec elapsed
    patchDate(2023, 6, 31, 13, 0, 11); // +1 so exactly 10 sec elapsed
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
    await contains(".o-mail-VoiceRecorder button[title='Voice Message']:disabled");
    cleanUp();
});
