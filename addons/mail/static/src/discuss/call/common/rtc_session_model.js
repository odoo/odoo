import { fields, Record } from "@mail/core/common/record";
import { Deferred } from "@web/core/utils/concurrency";

export class RtcSession extends Record {
    static _name = "discuss.channel.rtc.session";
    static id = "id";
    static awaitedRecords = new Map();
    static _insert() {
        /** @type {import("models").RtcSession} */
        const session = super._insert(...arguments);
        session.channel?.rtc_session_ids.add(session);
        return session;
    }
    /** @returns {Promise<import("models").RtcSession>} */
    static async getWhenReady(id) {
        const session = this.get(id);
        if (!session) {
            let deferred = this.awaitedRecords.get(id);
            if (!deferred) {
                deferred = new Deferred();
                this.awaitedRecords.set(id, deferred);
                setTimeout(() => {
                    deferred.resolve();
                    this.awaitedRecords.delete(id);
                }, 120_000);
            }
            return deferred;
        }
        return session;
    }
    /** @returns {import("models").RtcSession} */
    static new() {
        const record = super.new(...arguments);
        this.awaitedRecords.get(record.id)?.resolve(record);
        this.awaitedRecords.delete(record.id);
        return record;
    }

    // Server data
    channel_member_id = fields.One("discuss.channel.member", { inverse: "rtcSession" });
    partner_id = fields.One("res.partner", {
        compute() {
            return this.channel_member_id?.partner_id;
        },
    });
    guest_id = fields.One("mail.guest", {
        compute() {
            return this.channel_member_id?.guest_id;
        },
    });
    get persona() {
        return this.partner_id || this.guest_id;
    }
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
    isTalking = fields.Attr(false, {
        /** @this {import("models").RtcSession} */
        onUpdate() {
            if (this.isTalking && !this.isMute) {
                this.talkingTime = this.store.nextTalkingTime++;
            }
            this.channel?.updateCallFocusStack(this);
        },
    });
    isActuallyTalking = fields.Attr(false, {
        /** @this {import("models").RtcSession} */
        compute() {
            return this.isTalking && !this.isMute;
        },
    });
    isVideoStreaming = fields.Attr(false, {
        /** @this {import("models").RtcSession} */
        compute() {
            return this.is_screen_sharing_on || this.is_camera_on;
        },
    });
    shortStatus = fields.Attr(undefined, {
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
    /**
     * Represents the sequence of the last valid connection with that session. This can be used to
     * compare connection attempts (if they follow the last valid connection) and to validate information
     * (if they match the sequence).
     *
     *  @type {number}
     */
    sequence = 0;
    // RTC stats
    connectionState;
    logStep;

    get channel() {
        return this.channel_member_id?.channel_id;
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

    /**
     * @returns {string}
     */
    get name() {
        return this.channel_member_id?.name;
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
        if (this.store.settings.audioOutputDeviceId) {
            // skipping, it will use the default device.
            await this.audioElement.setSinkId(this.store.settings.audioOutputDeviceId).catch();
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
