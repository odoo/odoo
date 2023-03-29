/* @odoo-module */
import { Component, useState, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";

import Encoder from "./encoder";

/**
 * @typedef {Object} Props
 * @property {import("@mail/composer/composer_model").Composer} composer
 * @property {function} [attachmentUploader]
 * @property {function} [onchangeRecording]
 * @extends {Component<Props, Env>}
 */
export class VoiceRecorder extends Component {
    static props = ["composer", "attachmentUploader", "onchangeRecording"];
    static template = "mail.VoiceRecorder";

    microphone;
    startTimeStamp;
    context;
    streamSource;
    processor;
    encoder;

    setup() {
        this.state = useState({
            isActionPending: false,
            recording: false,
            intervalId: false,
            elapsed: "00 : 00",
        });
        this.notification = useService("notification");
        this.userSettings = useService("mail.user_settings");
        this.isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
        this.config = {
            // 128 or 160 kbit/s – mid-range bitrate quality
            bitRate: 128,
        };
        onWillUnmount(() => {
            this.unmount = true;
            this.cleanUp();
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

    async startRecording(ev) {
        if (this.state.isActionPending) {
            return;
        }
        this.state.isActionPending = true;
        if (!this.microphone) {
            try {
                this.microphone = await browser.navigator.mediaDevices.getUserMedia({
                    audio: this.userSettings.audioConstraints,
                });
            } catch {
                this.notification.add(
                    sprintf(_t('"%(hostname)s" needs to access your microphone'), {
                        hostname: window.location.host,
                    }),
                    { type: "warning" }
                );
                this.state.isActionPending = false;
                return;
            }
        }
        this.state.elapsed = "00 : 00";
        this.props.onchangeRecording();
        this.state.recording = true;
        this.context = new AudioContext();

        await this.context.audioWorklet.addModule("/discuss/voice/worklet_processor");
        this.processor = new AudioWorkletNode(this.context, "processor");
        this.processor.port.onmessage = (e) => {
            if (this.state.recording && !this.startTimeStamp) {
                let totalSeconds = 0;
                this.state.intervalId = setInterval(() => {
                    ++totalSeconds;
                    if (totalSeconds > 60) {
                        this.notification.add(
                            _t("The duration of voice messages is limited to 1 minute."),
                            { type: "warning" }
                        );
                        this.stopRecording();
                    }
                    const second = totalSeconds % 60;
                    const minute = Math.floor(totalSeconds / 60);
                    this.state.elapsed =
                        (minute < 10 ? "0" + minute : minute) +
                        " : " +
                        (second < 10 ? "0" + second : second);
                }, 1000);
                this.startTimeStamp = e.timeStamp;
            }
            this.encoder.encode(e.data);
        };
        this.streamSource = this.context.createMediaStreamSource(this.microphone);

        // Start to get microphone data
        this.streamSource.connect(this.processor);
        this.processor.connect(this.context.destination);
        this.config.sampleRate = this.context.sampleRate;
        this.encoder = new Encoder(this.config);
        this.state.isActionPending = false;
    }

    stopRecording(ev) {
        const duration = ev ? ev.timeStamp - this.startTimeStamp : 60000;
        this.getMp3().then(([buffer, blob]) => {
            const file = new File(buffer, this.filename(), {
                type: blob.type,
            });
            this.props.attachmentUploader.uploadFile(file, { voiceDuration: duration });
            this.props.composer.hasVoice = true;
        });
        this.cleanUp();
    }

    cleanUp() {
        if (this.processor && this.streamSource) {
            // Clean up the Web Audio API resources.
            this.streamSource.disconnect();
            this.processor.disconnect();

            // If all references using this.context are destroyed, context is closed
            // automatically. DOMException is fired when trying to close again
            if (this.context && this.context.state !== "closed") {
                this.context.close();
            }
        }

        clearInterval(this.state.intervalId);
        this.state.intervalId = false;
        this.startTimeStamp = false;
        this.microphone?.getTracks().forEach((track) => track.stop());
        this.microphone = null;
        this.state.recording = false;
        if (!this.unmount) {
            this.props.onchangeRecording();
        }
    }

    getMp3() {
        const finalBuffer = this.encoder.finish();
        return new Promise((resolve, reject) => {
            if (finalBuffer.length === 0) {
                reject(new Error("No buffer to send"));
            } else {
                resolve([finalBuffer, new Blob(finalBuffer, { type: "audio/mp3" })]);
                this.encoder.clearBuffer();
            }
        });
    }

    onClick(ev) {
        if (this.state.recording) {
            this.stopRecording(ev);
        } else {
            this.startRecording(ev);
        }
    }
}
