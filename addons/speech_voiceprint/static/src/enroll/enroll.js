// @ts-check
/** @odoo-module native */

import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ConfirmationDialog } from "@web/ui/dialog";
import { _t } from "@web/core/translation";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions";

const MIMETYPES = [
    "audio/webm;codecs=opus",
    "audio/ogg;codecs=opus",
    "audio/webm",
    "audio/mp4",
];
export const TARGET_SECONDS = 25;
const MIN_SECONDS = 12;

/** @returns {string} */
function preferredMimetype() {
    const supported = globalThis.MediaRecorder?.isTypeSupported;
    if (!supported) {
        return "";
    }
    return (
        MIMETYPES.find((type) => globalThis.MediaRecorder.isTypeSupported(type)) ?? ""
    );
}

export class VoiceprintEnroll extends Component {
    static template = "speech_voiceprint.Enroll";
    static props = { ...standardActionServiceProps };

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.blob = null;
        this.state = useState({
            loading: true,
            status: null,
            recording: false,
            seconds: 0,
            hasBlob: false,
            blobUrl: "",
            consent: false,
            sending: false,
            supported:
                Boolean(browser.navigator?.mediaDevices?.getUserMedia) &&
                Boolean(preferredMimetype()),
            error: "",
        });
        this.target = TARGET_SECONDS;
        onWillStart(() => this.refresh());
        onWillUnmount(() => this.stopTracks());
    }

    /** @returns {string} */
    get phrase() {
        return this.state.status?.phrase || "";
    }

    async refresh() {
        this.state.loading = true;
        try {
            this.state.status = await rpc("/speech/voiceprint/status");
            this.state.error = "";
        } catch (error) {
            this.state.error = error.data?.message || error.message;
        }
        this.state.loading = false;
    }

    async start() {
        this.state.error = "";
        this.clearBlob();
        try {
            this.stream = await browser.navigator.mediaDevices.getUserMedia({
                audio: true,
            });
        } catch {
            this.state.error = _t("Microphone access was denied.");
            return;
        }
        this.chunks = [];
        this.recorder = new globalThis.MediaRecorder(this.stream, {
            mimeType: preferredMimetype(),
        });
        this.recorder.ondataavailable = (event) =>
            event.data.size && this.chunks.push(event.data);
        this.recorder.onstop = () => this.onStopped();
        this.recorder.start(1000);
        this.state.recording = true;
        this.state.seconds = 0;
        this.timer = browser.setInterval(() => {
            this.state.seconds += 1;
            if (this.state.seconds >= this.target) {
                this.stop();
            }
        }, 1000);
    }

    stop() {
        browser.clearInterval(this.timer);
        this.timer = null;
        if (this.recorder && this.recorder.state !== "inactive") {
            this.recorder.stop();
        }
        this.state.recording = false;
    }

    onStopped() {
        this.stopTracks();
        const blob = new Blob(this.chunks, { type: this.recorder.mimeType });
        if (this.state.seconds < MIN_SECONDS) {
            this.state.error = _t(
                "Too short (%s s). Read the whole phrase.",
                this.state.seconds,
            );
            return;
        }
        this.blob = blob;
        this.state.hasBlob = true;
        this.state.blobUrl = URL.createObjectURL(blob);
    }

    stopTracks() {
        this.stream?.getTracks().forEach((track) => track.stop());
        this.stream = null;
    }

    clearBlob() {
        if (this.state.blobUrl) {
            URL.revokeObjectURL(this.state.blobUrl);
        }
        this.blob = null;
        this.state.hasBlob = false;
        this.state.blobUrl = "";
    }

    async send() {
        if (!this.blob || !this.state.consent) {
            return;
        }
        this.state.sending = true;
        try {
            const audio = await this.toBase64(this.blob);
            const result = await rpc("/speech/voiceprint/enroll", {
                audio,
                consent: true,
            });
            this.notification.add(
                _t("Voice stored (%s s of audio).", result.sample_seconds),
                { type: "success" },
            );
            this.clearBlob();
            await this.refresh();
        } catch (error) {
            this.state.error = error.data?.message || error.message;
        }
        this.state.sending = false;
    }

    revoke() {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete my voiceprint"),
            body: _t(
                "Your voice will no longer be recognised in recorded calls and meetings. Delete it?",
            ),
            confirmLabel: _t("Delete"),
            confirm: async () => {
                try {
                    await rpc("/speech/voiceprint/revoke");
                    this.notification.add(_t("Your voiceprint was deleted."), {
                        type: "info",
                    });
                } catch (error) {
                    this.state.error = error.data?.message || error.message;
                }
                await this.refresh();
            },
            cancel: () => {},
        });
    }

    /** @param {Blob} blob @returns {Promise<string>} */
    toBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result).split(",")[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
}

registry.category("actions").add("speech_voiceprint.enroll", VoiceprintEnroll);
