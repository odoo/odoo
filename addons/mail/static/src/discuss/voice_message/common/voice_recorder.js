import { Component, onWillUnmount, props, proxy, status, types } from "@odoo/owl";

import { useComponent } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Mp3Encoder } from "./mp3_encoder";
import { CallPermissionDeniedDialog } from "@mail/discuss/call/common/call_permission_denied_dialog";
import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";
import { monitorAudio } from "@mail/utils/common/media_monitoring";

/** @typedef {import("@mail/discuss/call/common/rtc_service").ContextOptions} ContextOptions */

export class VoiceRecorder extends Component {
    static template = "mail.VoiceRecorder";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            composer: types.instanceOf(this.store["Composer"].Class),
            state: types.object({
                cancelRecording: types.function([]),
                elapsed: types.string(),
                limitWarning: types.boolean(),
                onClick: types.function([]),
                volumes: types.array(types.number()),
            }),
        });
    }

    get title() {
        return _t("Stop Recording");
    }
    get cancelTitle() {
        return _t("Cancel");
    }
}

export const patchable = {
    makeFile(file) {
        return file;
    },
};

/**
 * @param {Object} [params={}]
 * @param {number} [params.maxDuration=60] Maximum recording duration in seconds.
 * @param {Function} params.onRecordReady Callback when recording is finished.
 * @param {ContextOptions} [options]
 */
export function useVoiceRecorder(params = {}, options = {}) {
    const maxDuration = params.maxDuration ?? 60;
    const component = useComponent();
    const onRecordReady = params.onRecordReady;
    /** @type {MediaStream} */
    let microphone;
    /** @type {number} */
    let startTimeStamp;
    /** @type {AudioContext} */
    let audioContext;
    /** @type {MediaStreamAudioSourceNode} */
    let streamSource;
    /** @type {AudioWorkletNode} */
    let processor;
    /** @type {Mp3Encoder} */
    let encoder;
    /** @type {Function} */
    let disconnectAudioMonitor;

    const state = proxy({
        limitWarning: false,
        isActionPending: false,
        recording: false,
        elapsed: "00 : 00",
        volumes: new Array(3).fill(0),
        onClick() {
            if (state.recording) {
                return stopRecording();
            } else {
                return startRecording();
            }
        },
        /**
         * Stops the recording without uploading the file
         */
        cancelRecording() {
            if (state.recording) {
                cleanUp();
            }
        },
    });
    /** @type {ReturnType<typeof import("@web/core/notifications/notification_service").notificationService.start>} */
    const dialog = useService("dialog");
    const notification = useService("notification");
    const store = useService("mail.store");
    const config = { bitRate: 128 }; // 128 or 160 kbit/s – mid-range bitrate quality
    onWillUnmount(() => {
        if (state.recording) {
            notification.add(_t("Voice recording stopped"), { type: "warning" });
            stopRecording();
        } else {
            cleanUp();
        }
    });

    function filename() {
        return (
            "Voice-" +
            new Date().toISOString().split("T")[0] +
            "-" +
            Math.floor(Math.random() * 100000) +
            ".mp3"
        );
    }

    async function startRecording() {
        if (state.isActionPending) {
            return;
        }
        state.isActionPending = true;
        if (!microphone) {
            try {
                const sourceWindow = options.rootRef?.()?.ownerDocument?.defaultView || browser;
                microphone = await sourceWindow.navigator.mediaDevices.getUserMedia({
                    audio: store.settings.audioConstraints,
                });
                if (status(component) === "destroyed") {
                    cleanUp();
                    return;
                }
            } catch {
                dialog.add(
                    CallPermissionDeniedDialog,
                    { permissionType: "microphone" },
                    { rootRef: options.rootRef }
                );
                state.isActionPending = false;
                return;
            }
        }
        state.elapsed = "00 : 00";
        state.recording = true;
        audioContext = new browser.AudioContext();

        await loadLamejs();
        await audioContext.audioWorklet.addModule("/discuss/voice/worklet_processor");
        processor = new browser.AudioWorkletNode(audioContext, "processor");
        processor.port.onmessage = (e) => {
            if (state.recording && !startTimeStamp) {
                startTimeStamp = e.timeStamp;
            }
            if (!startTimeStamp) {
                return;
            }
            const elapsedSeconds = Math.floor((e.timeStamp - startTimeStamp) / 1000);
            const second = elapsedSeconds % 60;
            const minute = Math.floor(elapsedSeconds / 60);
            state.elapsed =
                (minute < 10 ? "0" + minute : minute) +
                " : " +
                (second < 10 ? "0" + second : second);
            if (elapsedSeconds > maxDuration - 5 && elapsedSeconds < maxDuration) {
                state.limitWarning = true;
            }
            if (elapsedSeconds >= maxDuration) {
                notification.add(
                    _t(
                        "The duration of voice messages is limited to %s minute(s).",
                        Math.round(maxDuration / 60)
                    ),
                    {
                        type: "warning",
                    }
                );
                stopRecording();
            }
            if (!e.data) {
                return;
            }
            _encode(e.data);
        };
        streamSource = audioContext.createMediaStreamSource(microphone);

        // Start to get microphone data
        streamSource.connect(processor);
        processor.connect(audioContext.destination);
        config.sampleRate = audioContext.sampleRate;
        encoder = new Mp3Encoder(config);
        state.isActionPending = false;

        // Live waveform audio feedback
        let lastTic = 0;
        const track = microphone.getAudioTracks()[0];
        const monitorPromise = monitorAudio(track, {
            onTic: (volume) => {
                const now = Date.now();
                if (now - lastTic < 80) {
                    return;
                }
                lastTic = now;
                state.volumes = [...state.volumes.slice(1), volume];
            },
        });
        disconnectAudioMonitor = await monitorPromise;
        if (!state.recording) {
            disconnectAudioMonitor();
            disconnectAudioMonitor = undefined;
        }
    }

    function _encode(data) {
        encoder.encode(data);
    }

    function _getEncoderBuffer() {
        return encoder.finish();
    }

    function _makeFile(buffer, type) {
        return patchable.makeFile(new File(buffer, filename(), { type }));
    }

    /**
     * @returns {Promise} a promise that resolves when the recording
     * is finished and the file upload has been initiated
     */
    function stopRecording() {
        const promise = getMp3()
            .then((buffer) => {
                const file = _makeFile(buffer, "audio/mp3");
                if (file.size === 0) {
                    return;
                }
                return onRecordReady(file);
            })
            .catch(() => {});
        cleanUp();
        return promise;
    }

    function cleanUp() {
        if (processor && streamSource) {
            // Clean up the Web Audio API resources.
            streamSource.disconnect();
            processor.disconnect();

            if (audioContext && audioContext.state !== "closed") {
                // If all references using audioContext are destroyed, context is
                // closed automatically. DOMException is fired when trying to close again
                audioContext.close();
            }
        }

        disconnectAudioMonitor?.();
        disconnectAudioMonitor = undefined;
        state.volumes = new Array(3).fill(0);
        startTimeStamp = false;
        microphone?.getTracks().forEach((track) => track.stop());
        microphone = null;
        state.recording = false;
        state.limitWarning = false;
    }

    function getMp3() {
        const finalBuffer = _getEncoderBuffer();
        return new Promise((resolve, reject) => {
            if (finalBuffer.length === 0) {
                reject(new Error("No buffer to send"));
            } else {
                resolve(finalBuffer);
                encoder.clearBuffer();
            }
        });
    }

    return state;
}
