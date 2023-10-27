/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class RtcSession extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").RtcSession>} */
    static records = {};
    /** @returns {import("models").RtcSession} */
    static get(data) {
        return super.get(data);
    }
    /** @returns {import("models").RtcSession|import("models").RtcSession[]} */
    static insert(data) {
        return super.insert(...arguments);
    }
    static _insert() {
        /** @type {import("models").RtcSession} */
        const session = super._insert(...arguments);
        session.channel?.rtcSessions.add(session);
        return session;
    }

    // Server data
    /** @type {boolean} */
    channelMember = Record.one("ChannelMember", { inverse: "rtcSession" });
    /** @type {boolean} */
    isCameraOn;
    /** @type {boolean} */
    isScreenSharingOn;
    /** @type {number} */
    id;
    /** @type {boolean} */
    isDeaf;
    /** @type {boolean} */
    isSelfMuted;
    // Client data
    /** @type {HTMLAudioElement} */
    audioElement;
    /** @type {MediaStream} */
    audioStream;
    /** @type {RTCDataChannel} */
    dataChannel;
    audioError;
    videoError;
    isTalking;
    localVolume;
    /** @type {RTCPeerConnection} */
    peerConnection;
    /** @type {Date|undefined} */
    raisingHand;
    videoComponentCount = 0;
    /** @type {Map<'screen'|'camera', MediaStream>} */
    videoStreams = new Map();
    /** @type {string} */
    mainVideoStreamType;
    // RTC stats
    connectionState;
    localCandidateType;
    remoteCandidateType;
    dataChannelState;
    packetsReceived;
    packetsSent;
    dtlsState;
    iceState;
    iceGatheringState;
    logStep;

    get channel() {
        return this.channelMember?.thread;
    }

    get isMute() {
        return this.isSelfMuted || this.isDeaf;
    }

    get mainVideoStream() {
        return this.isMainVideoStreamActive && this.videoStreams.get(this.mainVideoStreamType);
    }

    get isMainVideoStreamActive() {
        if (!this.mainVideoStreamType) {
            return false;
        }
        return this.mainVideoStreamType === "camera" ? this.isCameraOn : this.isScreenSharingOn;
    }

    get hasVideo() {
        return this.isScreenSharingOn || this.isCameraOn;
    }

    getStream(type) {
        const isActive = type === "camera" ? this.isCameraOn : this.isScreenSharingOn;
        return isActive && this.videoStreams.get(type);
    }

    get partnerId() {
        const persona = this.channelMember?.persona;
        return persona.type === "partner" ? persona.id : undefined;
    }

    get guestId() {
        const persona = this.channelMember?.persona;
        return persona.type === "guest" ? persona.id : undefined;
    }

    /**
     * @returns {string}
     */
    get name() {
        return this.channelMember?.persona.name;
    }

    /**
     * @returns {number} float
     */
    get volume() {
        return this.audioElement?.volume || this.localVolume;
    }

    set volume(value) {
        if (this.audioElement) {
            this.audioElement.volume = value;
        }
        this.localVolume = value;
    }

    async playAudio() {
        if (!this.audioElement) {
            return;
        }
        try {
            await this.audioElement.play();
            this.audioError = undefined;
        } catch (error) {
            this.audioError = error.name;
        }
    }

    /**
     * @param {"audio" | "camera" | "screen"} type
     * @param {boolean} state
     */
    updateStreamState(type, state) {
        if (type === "camera") {
            this.isCameraOn = state;
        } else if (type === "screen") {
            this.isScreenSharingOn = state;
        }
    }

    async updateStats() {
        delete this.localCandidateType;
        delete this.remoteCandidateType;
        delete this.dataChannelState;
        delete this.packetsReceived;
        delete this.packetsSent;
        delete this.dtlsState;
        delete this.iceState;
        delete this.iceGatheringState;
        if (!this.peerConnection) {
            return;
        }
        let stats;
        try {
            stats = await this.peerConnection.getStats();
        } catch {
            return;
        }
        this.iceGatheringState = this.peerConnection.iceGatheringState;
        for (const value of stats.values() || []) {
            switch (value.type) {
                case "candidate-pair":
                    if (value.state === "succeeded" && value.localCandidateId) {
                        this.localCandidateType =
                            stats.get(value.localCandidateId)?.candidateType || "";
                        this.remoteCandidateType =
                            stats.get(value.remoteCandidateId)?.candidateType || "";
                    }
                    break;
                case "data-channel":
                    this.dataChannelState = value.state;
                    break;
                case "transport":
                    this.dtlsState = value.dtlsState;
                    this.iceState = value.iceState;
                    this.packetsReceived = value.packetsReceived;
                    this.packetsSent = value.packetsSent;
                    break;
            }
        }
    }
}

RtcSession.register();
