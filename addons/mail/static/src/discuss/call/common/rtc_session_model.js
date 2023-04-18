/* @odoo-module */

import { createLocalId } from "@mail/utils/common/misc";

export class RtcSession {
    // Server data
    channelId;
    channelMemberId;
    isCameraOn;
    id;
    isDeaf;
    isSelfMuted;
    isSendingVideo;
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
    /** @type {import("@mail/core/common/store_service").Store} */
    _store;
    // RTC stats
    connectionState;
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

    async setAudioStream(stream, { volume = 0.5, mute = false } = {}) {
        const audioElement = this.audioElement || new window.Audio();
        audioElement.srcObject = stream;
        audioElement.load();
        audioElement.muted = mute;
        audioElement.volume = volume;
        // Using both autoplay and play() as safari may prevent play() outside of user interactions
        // while some browsers may not support or block autoplay.
        audioElement.autoplay = true;
        this.audioElement = audioElement;
        this.audioStream = stream;
        this.isSelfMuted = false;
        this.isTalking = false;
        await this.playAudio();
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
}
