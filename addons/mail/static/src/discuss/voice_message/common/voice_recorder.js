import { Component, useState, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { Mp3Encoder } from "./mp3_encoder";
import { loadLamejs } from "@mail/discuss/voice_message/common/voice_message_service";

/**
 * @typedef {Object} Props
 * @property {import("models").Composer} composer
 * @property {function} [attachmentUploader]
 * @property {function} [onchangeRecording]
 * @extends {Component<Props, Env>}
 */
export class VoiceRecorder extends Component {
    static props = ["composer", "attachmentUploader", "onchangeRecording?"];
    static template = "mail.VoiceRecorder";

    /** @type {MediaStream} */
    microphone;
    /** @type {number} */
    startTimeStamp;
    /** @type {AudioContext} */
    audioContext;
    /** @type {MediaStreamAudioSourceNode} */
    streamSource;
    /** @type {AudioWorkletNode} */
    processor;
    /** @type {Mp3Encoder} */
    encoder;
    /** @type {import("models").Store} */
    store;
    /** @type {ReturnType<typeof import("@web/core/notifications/notification_service").notificationService.start>} */
    notification;
    /** @type {Object} */
    config;
    /** @type {import("@mail/discuss/voice_message/common/voice_message_service").VoiceMessageService} */
    voiceMessageService;

    setup() {
        super.setup();
        this.state = useState({
            limitWarning: false,
            isActionPending: false,
            recording: false,
            elapsed: "00 : 00",
        });
        this.notification = useService("notification");
        this.store = useState(useService("mail.store"));
        this.voiceMessageService = useState(useService("discuss.voice_message"));
        this.config = {
            // 128 or 160 kbit/s – mid-range bitrate quality
            bitRate: 128,
        };
        onWillUnmount(() => {
            if (this.state.recording) {
                this.notification.add(_t("Voice recording stopped"), { type: "warning" });
                this.stopRecording();
            } else {
                this.cleanUp({ unmounting: true });
            }
        });
    }

    filename() {
        return (
            "Voice-" +
            new Date().toISOString().split("T")[0] +
            "-" +
            Math.floor(Math.random() * 100000) +
            ".mp3"
        );
    }

    async startRecording() {
        if (this.state.isActionPending) {
            return;
        }
        this.state.isActionPending = true;
        if (!this.microphone) {
            try {
                this.microphone = await browser.navigator.mediaDevices.getUserMedia({
                    audio: this.store.settings.audioConstraints,
                });
            } catch {
                this.notification.add(
                    _t('"%(hostname)s" needs to access your microphone', {
                        hostname: window.location.host,
                    }),
                    { type: "warning" }
                );
                this.state.isActionPending = false;
                return;
            }
        }
        this.state.elapsed = "00 : 00";
        this.props.onchangeRecording?.();
        this.state.recording = true;
        this.audioContext = new browser.AudioContext();

        await loadLamejs();
        await this.audioContext.audioWorklet.addModule("/discuss/voice/worklet_processor");
        this.processor = new browser.AudioWorkletNode(this.audioContext, "processor");
        this.processor.port.onmessage = (e) => {
            if (this.state.recording && !this.startTimeStamp) {
                this.startTimeStamp = e.timeStamp;
            }
            if (!this.startTimeStamp) {
                return;
            }
            const elapsedSeconds = Math.floor((e.timeStamp - this.startTimeStamp) / 1000);
            const second = elapsedSeconds % 60;
            const minute = Math.floor(elapsedSeconds / 60);
            this.state.elapsed =
                (minute < 10 ? "0" + minute : minute) +
                " : " +
                (second < 10 ? "0" + second : second);
            if (elapsedSeconds > 55 && elapsedSeconds < 60) {
                this.state.limitWarning = true;
            }
            if (elapsedSeconds === 60) {
                this.notification.add(
                    _t("The duration of voice messages is limited to 1 minute."),
                    { type: "warning" }
                );
                this.stopRecording();
            }
            if (!e.data) {
                return;
            }
            this._encode(e.data);
        };
        this.streamSource = this.audioContext.createMediaStreamSource(this.microphone);

        // Start to get microphone data
        this.streamSource.connect(this.processor);
        this.processor.connect(this.audioContext.destination);
        this.config.sampleRate = this.audioContext.sampleRate;
        this.encoder = new Mp3Encoder(this.config);
        this.state.isActionPending = false;
    }

    _encode(data) {
        this.encoder.encode(data);
    }

    _getEncoderBuffer() {
        return this.encoder.finish();
    }

    _makeFile(buffer, type) {
        return new File(buffer, this.filename(), { type });
    }

    stopRecording() {
        this.getMp3()
            .then((buffer) => {
                const file = this._makeFile(buffer, "audio/mp3");
                this.props.attachmentUploader.uploadFile(file, { voice: true });
            })
            .catch(() => {});
        this.cleanUp();
    }

    cleanUp({ unmounting = false } = {}) {
        if (this.processor && this.streamSource) {
            // Clean up the Web Audio API resources.
            this.streamSource.disconnect();
            this.processor.disconnect();

            if (this.audioContext && this.audioContext.state !== "closed") {
                // If all references using this.audioContext are destroyed, context is
                // closed automatically. DOMException is fired when trying to close again
                this.audioContext.close();
            }
        }

        this.startTimeStamp = false;
        this.microphone?.getTracks().forEach((track) => track.stop());
        this.microphone = null;
        this.state.recording = false;
        this.state.limitWarning = false;
        if (!unmounting) {
            this.props.onchangeRecording?.();
        }
    }

    getMp3() {
        const finalBuffer = this._getEncoderBuffer();
        return new Promise((resolve, reject) => {
            if (finalBuffer.length === 0) {
                reject(new Error("No buffer to send"));
            } else {
                resolve(finalBuffer);
                this.encoder.clearBuffer();
            }
        });
    }

    onClick(ev) {
        if (this.state.recording) {
            this.stopRecording();
        } else {
            this.startRecording();
        }
    }
}
