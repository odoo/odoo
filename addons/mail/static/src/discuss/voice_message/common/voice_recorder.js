import { useState, onWillUnmount, status, useComponent } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Mp3Encoder } from "./mp3_encoder";
import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";

export const patchable = {
    makeFile(file) {
        return file;
    },
};

export function useVoiceRecorder() {
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

    const component = useComponent();
    const state = useState({
        limitWarning: false,
        isActionPending: false,
        recording: component.props.state?.recording ?? false,
        elapsed: "00 : 00",
        onClick() {
            if (state.recording) {
                stopRecording();
            } else {
                startRecording();
            }
        },
    });
    /** @type {ReturnType<typeof import("@web/core/notifications/notification_service").notificationService.start>} */
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
                microphone = await browser.navigator.mediaDevices.getUserMedia({
                    audio: store.settings.audioConstraints,
                });
                if (status(component) === "destroyed") {
                    cleanUp();
                    return;
                }
            } catch {
                notification.add(
                    _t('"%(hostname)s" needs to access your microphone', {
                        hostname: window.location.host,
                    }),
                    { type: "warning" }
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
            if (elapsedSeconds > 55 && elapsedSeconds < 60) {
                state.limitWarning = true;
            }
            if (elapsedSeconds === 60) {
                notification.add(_t("The duration of voice messages is limited to 1 minute."), {
                    type: "warning",
                });
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

    function stopRecording() {
        getMp3()
            .then((buffer) => {
                const file = _makeFile(buffer, "audio/mp3");
                if (file.size === 0) {
                    return;
                }
                component.attachmentUploader.uploadFile(file, { voice: true });
            })
            .catch(() => {});
        cleanUp();
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
