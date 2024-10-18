import { Record } from "@mail/core/common/record";

export class RtcSession extends Record {
    static _name = "discuss.channel.rtc.session";
    static id = "id";
    /** @type {Object.<number, import("models").RtcSession>} */
    static records = {};
    /** @returns {import("models").RtcSession} */
    static get(data) {
        return super.get(data);
    }
    /**
     * @template T
     * @param {T} data
     * @returns {T extends any[] ? import("models").RtcSession[] : import("models").RtcSession}
     */
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
    channel_member_id = Record.one("discuss.channel.member", { inverse: "rtcSession" });
    persona = Record.one("Persona", {
        compute() {
            return this.channel_member_id?.persona;
        },
    });
    /** @type {boolean} */
    is_camera_on;
    /** @type {boolean} */
    is_screen_sharing_on;
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_deaf;
    /** @type {boolean} */
    is_muted;
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
            return this.is_screen_sharing_on || this.is_camera_on;
        },
    });
    shortStatus = Record.attr(undefined, {
        compute() {
            if (this.is_screen_sharing_on) {
                return "live";
            }
            if (this.is_deaf) {
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
        return this.channel_member_id?.thread;
    }

    get isMute() {
        return this.is_muted || this.is_deaf;
    }

    get mainVideoStream() {
        return this.isMainVideoStreamActive && this.videoStreams.get(this.mainVideoStreamType);
    }

    get isMainVideoStreamActive() {
        if (!this.mainVideoStreamType) {
            return false;
        }
        return this.mainVideoStreamType === "camera"
            ? this.is_camera_on
            : this.is_screen_sharing_on;
    }

    get hasVideo() {
        return this.is_screen_sharing_on || this.is_camera_on;
    }

    getStream(type) {
        const isActive = type === "camera" ? this.is_camera_on : this.is_screen_sharing_on;
        return isActive && this.videoStreams.get(type);
    }

    /**
     * @returns {{isSelfMuted: boolean, isDeaf: boolean, isTalking: boolean, isRaisingHand: boolean}}
     */
    get info() {
        return {
            isSelfMuted: this.is_muted,
            isRaisingHand: Boolean(this.raisingHand),
            isDeaf: this.is_deaf,
            isTalking: this.isTalking,
            isCameraOn: this.is_camera_on,
            isScreenSharingOn: this.is_screen_sharing_on,
        };
    }

    get partnerId() {
        const persona = this.channel_member_id?.persona;
        return persona.type === "partner" ? persona.id : undefined;
    }

    get guestId() {
        const persona = this.channel_member_id?.persona;
        return persona.type === "guest" ? persona.id : undefined;
    }

    /**
     * @returns {string}
     */
    get name() {
        return this.channel_member_id?.persona.name;
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
            this.is_camera_on = state;
        } else if (type === "screen") {
            this.is_screen_sharing_on = state;
        }
    }
}

RtcSession.register();
