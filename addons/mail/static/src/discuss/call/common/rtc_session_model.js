/* @odoo-module */

import { Record } from "@mail/core/common/record";

export class RtcSession extends Record {
    static id = "id";
    /** @type {Object.<number, import("models").RtcSession>} */
    static records = {};
    /** @returns {import("models").RtcSession} */
    static new(data) {
        return super.new(data);
    }
    /** @returns {import("models").RtcSession} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @param {Object} data
     * @returns {number, import("models").RtcSession}
     */
    static insert(data) {
        const session = this.get(data) ?? this.new(data);
        const { channelMember, ...remainingData } = data;
        for (const key in remainingData) {
            session[key] = remainingData[key];
        }
        if (channelMember?.channel) {
            session.channelId = channelMember.channel.id;
        }
        if (channelMember) {
            const channelMemberRecord = this.store.ChannelMember.insert(channelMember);
            channelMemberRecord.rtcSession = session;
            session.channelMemberId = channelMemberRecord.id;
            channelMemberRecord.thread?.rtcSessions.add(session);
        }
        return session;
    }

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
    /** @type {Map<'screen'|'camera', MediaStream>} */
    videoStreams = new Map();
    /** @type {MediaStream} */
    mainVideoStream;
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
        return this._store.ChannelMember.get(this.channelMemberId);
    }

    get channel() {
        return this._store.Thread.get({ model: "discuss.channel", id: this.channelId });
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

RtcSession.register();
