/** @odoo-module */

import { createLocalId } from "../utils/misc";

export class RtcSession {
    // Server data
    channelId;
    channelMemberId;
    isCameraOn;
    id;
    isDeaf;
    isSelfMuted;
    isScreenSharingOn;
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
    /** @type {MediaStream} */
    videoStream;
    /** @type {import("@mail/core/store_service").Store} */
    _store;
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

    get channelMember() {
        return this._store.channelMembers[this.channelMemberId];
    }

    get channel() {
        return this._store.threads[createLocalId("discuss.channel", this.channelId)];
    }

    get isMute() {
        return this.isSelfMuted || this.isDeaf;
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
