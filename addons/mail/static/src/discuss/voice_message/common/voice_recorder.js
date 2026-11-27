import {
    Component,
    onWillUnmount,
    proxy,
    types,
    usePlugin,
    useProps,
    useScope,
    xml,
} from "@odoo/owl";

import { BaseAction } from "@mail/core/common/action_list";

import { CallPermissionDeniedDialog } from "@mail/discuss/call/common/call_permission_denied_dialog";
import {
    formatVoiceTime,
    getVolumeLevel,
    getVolumePeak,
    loadLamejs,
} from "@mail/discuss/voice_message/common/voice_message_service";
import { _t } from "@web/core/l10n/translation";
import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { useService } from "@web/core/utils/hooks";
import { Mp3Encoder } from "./mp3_encoder";

/** @typedef {import("@mail/discuss/call/common/rtc_service").ContextOptions} ContextOptions */

// Used to draw the live waveform while recording, kept in sync with the CSS scroll duration.
// A bar every 80ms gives 2-3 bars per syllable (speech is ~4-5 syllables/s),
// and 16 bars of 3px with 2px gaps take 78px, which fits the pill next to the timer.
const VOLUME_LEVEL_HISTORY_SIZE = 16;
const BAR_DURATION_MS = 80;

export class VoiceRecorder extends Component {
    static template = "mail.VoiceRecorder";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            composer: types.instanceOf(this.store["Composer"]),
            state: types.object({
                cancelRecording: types.function([]),
                elapsed: types.string(),
                isActionPending: types.boolean(),
                limit: types.string(),
                limitWarning: types.boolean(),
                onClick: types.function([]),
                volumeLevels: types.array(types.number()),
                volumeLevelsOffset: types.number(),
            }),
        });
    }

    get title() {
        return _t("Stop Recording");
    }
    get cancelTitle() {
        return _t("Discard (%(keyboard_command)s)", { keyboard_command: "Esc" });
    }
}

/** Component of the voice-recording action of a composer, @see BaseAction */
export class VoiceRecorderAction extends BaseAction {
    static components = { VoiceRecorder };
    static template = xml`
        <VoiceRecorder composer="this.action.params.composer" state="this.action.owner.voiceRecorder"/>
    `;
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
    const scope = useScope();
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
    /** @type {number} */
    let barVolumePeak;
    /** @type {number} */
    let lastBarTimeStamp;

    const state = proxy({
        limitWarning: false,
        isActionPending: false,
        recording: false,
        elapsed: formatVoiceTime(0),
        limit: formatVoiceTime(maxDuration),
        volumeLevels: [],
        volumeLevelsOffset: 0,
        onClick() {
            if (state.recording) {
                return stopRecording();
            } else {
                return startRecording();
            }
        },
        stopRecording,
        /**
         * Stops the recording without uploading the file
         */
        cancelRecording() {
            if (state.recording && !state.isActionPending) {
                cleanUp();
            }
        },
    });
    const dialog = useService("dialog");
    const notification = usePlugin(NotificationPlugin);
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
                const sourceWindow = options.rootRef?.()?.ownerDocument?.defaultView || window;
                microphone = await sourceWindow.navigator.mediaDevices.getUserMedia({
                    audio: store.settings.audioConstraints,
                });
                if (scope.status === 3 /* destroyed */) {
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
        state.elapsed = formatVoiceTime(0);
        state.recording = true;
        state.volumeLevels = Array.from({ length: VOLUME_LEVEL_HISTORY_SIZE }, () => 0);
        state.volumeLevelsOffset = 0;
        barVolumePeak = 0;
        lastBarTimeStamp = 0;
        audioContext = new window.AudioContext();

        await loadLamejs();
        await audioContext.audioWorklet.addModule("/discuss/voice/worklet_processor");
        processor = new window.AudioWorkletNode(audioContext, "processor");
        processor.port.onmessage = (e) => {
            if (state.recording && !startTimeStamp) {
                startTimeStamp = e.timeStamp;
            }
            if (!startTimeStamp) {
                return;
            }
            const elapsedSeconds = Math.floor((e.timeStamp - startTimeStamp) / 1000);
            state.elapsed = formatVoiceTime(elapsedSeconds);
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
                return;
            }
            if (!e.data) {
                return;
            }
            _encode(e.data);
            barVolumePeak = Math.max(barVolumePeak, getVolumePeak(e.data));
            if (e.timeStamp - lastBarTimeStamp >= BAR_DURATION_MS) {
                lastBarTimeStamp = e.timeStamp;
                state.volumeLevels = [
                    ...state.volumeLevels.slice(1),
                    getVolumeLevel(barVolumePeak),
                ];
                state.volumeLevelsOffset++;
                barVolumePeak = 0;
            }
        };
        streamSource = audioContext.createMediaStreamSource(microphone);

        // Start to get microphone data
        streamSource.connect(processor);
        processor.connect(audioContext.destination);
        config.sampleRate = audioContext.sampleRate;
        encoder = new Mp3Encoder(config);
        state.isActionPending = false;
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
