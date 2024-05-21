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
    isTalking = Record.attr(false, {
        /** @this {import("models").RtcSession} */
        onUpdate() {
            if (this.isTalking && !this.isMute) {
                this.talkingTime = this.store.nextTalkingTime++;
            }
        },
    });
    isActuallyTalking = Record.attr(false, {
        /** @this {import("models").RtcSession} */
        compute() {
            return this.isTalking && !this.isMute;
        },
    });
    isVideoStreaming = Record.attr(false, {
        /** @this {import("models").RtcSession} */
        compute() {
            return this.isScreenSharingOn || this.isCameraOn;
        },
    });
    shortStatus = Record.attr(undefined, {
        compute() {
            if (this.isScreenSharingOn) {
                return "live";
            }
            if (this.isDeaf) {
                return "deafen";
            }
            if (this.isMute) {
                return "mute";
            }
        },
    });
    talkingTime = 0;
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

    /**
     * @returns {{isSelfMuted: boolean, isDeaf: boolean, isTalking: boolean, isRaisingHand: boolean}}
     */
    get info() {
        return {
            isSelfMuted: this.isSelfMuted,
            isRaisingHand: Boolean(this.raisingHand),
            isDeaf: this.isDeaf,
            isTalking: this.isTalking,
            isCameraOn: this.isCameraOn,
            isScreenSharingOn: this.isScreenSharingOn,
        };
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
}

RtcSession.register();
