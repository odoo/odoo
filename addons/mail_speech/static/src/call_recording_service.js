/** @odoo-module native */
import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";

import { CallRecorder, isRecordingSupported } from "./call_recorder.js";

export class CallRecordingService {
    /** @type {CallRecorder|undefined} */
    recorder;

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    constructor(env, services) {
        this.env = env;
        this.rtc = services["discuss.rtc"];
        this.notification = services.notification;
        this.state = reactive({ recording: false, channelId: null, pending: 0 });
    }

    /** @returns {boolean} */
    get isSupported() {
        return isRecordingSupported();
    }

    /** @param {import("models").Thread} channel */
    async toggle(channel) {
        if (this.state.recording) {
            await this.stop();
        } else {
            await this.start(channel);
        }
    }

    /** @param {import("models").Thread} channel */
    async start(channel) {
        if (this.state.recording || !this.isSupported) {
            return;
        }
        const claim = await rpc("/discuss/call/recording/start", {
            channel_id: channel.id,
        });
        if (claim.error) {
            this.notification.add(_t("Someone else is already recording this call."), {
                type: "warning",
            });
            return;
        }
        this.state.channelId = channel.id;
        this.recorder = new CallRecorder({
            localTrack: () => this.rtc.state.audioTrack,
            remoteStreams: () => this._remoteStreams(),
            onSegment: (blob, startMs, endMs) =>
                this._upload(channel.id, blob, startMs, endMs),
        });
        this.recorder.start();
        this.state.recording = true;
    }

    async stop() {
        if (!this.state.recording) {
            return;
        }
        this.state.recording = false;
        await this.recorder?.stop();
        this.recorder = undefined;
        const channelId = this.state.channelId;
        this.state.channelId = null;
        await rpc("/discuss/call/recording/stop", { channel_id: channelId });
    }

    /** @returns {MediaStream[]} */
    _remoteStreams() {
        const channel = this.rtc.state.channel;
        if (!channel) {
            return [];
        }
        return channel.rtc_session_ids
            .filter((session) => session.audioStream && !session.isSelf)
            .map((session) => session.audioStream);
    }

    /**
     * @param {number} channelId
     * @param {Blob} blob
     * @param {number} startMs
     * @param {number} endMs
     */
    async _upload(channelId, blob, startMs, endMs) {
        const body = new FormData();
        body.append("csrf_token", odoo.csrf_token);
        body.append("channel_id", channelId);
        body.append("start_ms", startMs);
        body.append("end_ms", endMs);
        body.append("ufile", blob, `call-${channelId}-${startMs}.webm`);
        this.state.pending++;
        try {
            const response = await browser.fetch("/discuss/call/upload_recording", {
                method: "POST",
                body,
            });
            if (!response.ok) {
                throw new Error(response.statusText);
            }
        } catch {
            this.notification.add(_t("A part of the recording could not be saved."), {
                type: "warning",
            });
        } finally {
            this.state.pending--;
        }
    }
}

export const callRecordingService = {
    dependencies: ["discuss.rtc", "notification"],

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {import("services").ServiceFactories} services
     */
    start(env, services) {
        return reactive(new CallRecordingService(env, services));
    },
};

registry.category("services").add("discuss.call_recording", callRecordingService);
