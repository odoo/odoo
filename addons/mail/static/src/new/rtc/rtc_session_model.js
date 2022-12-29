/** @odoo-module */

import { createLocalId } from "../utils/misc";

export class RtcSession {
    // Server data
    isCameraOn;
    id;
    isDeaf;
    isSelfMuted;
    isScreenSharingOn;
    // Client data
    audioElement;
    audioStream;
    isAudioInError;
    localVolume;
    isTalking;
    videoStream;
    connectionState;
    // "relational data"
    channelId;
    channelMemberId;
    /** @type {RTCDataChannel} */
    dataChannel;
    /** @type {RTCPeerConnection} */
    peerConnection;
    /** @type {import("@mail/new/core/store_service").Store} */
    _store;
    videoComponentCount = 0;

    get channelMember() {
        return this._store.channelMembers[this.channelMemberId];
    }

    get channel() {
        return this._store.threads[createLocalId("mail.channel", this.channelId)];
    }

    get isMute() {
        return this.isSelfMuted || this.isDeaf;
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
        if (this.audioElement) {
            return this.audioElement.volume;
        }
        return undefined;
    }
}
