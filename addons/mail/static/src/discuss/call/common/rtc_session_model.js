import { fields } from "@mail/core/common/record";
import { DiscussChannelRtcSession } from "@mail/core/common/model_definitions";

import { Deferred } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";

/**
 * @typedef {object} ServerSessionInfo
 * @property {boolean} [is_camera_on]
 * @property {boolean} [is_screen_sharing_on]
 * @property {boolean} [is_muted]
 * @property {boolean} [is_deaf]
 */

/**
 * @typedef {object} SessionInfo
 * @property {boolean} [isSelfMuted]
 * @property {boolean} [isDeaf]
 * @property {boolean} [isTalking]
 * @property {boolean} [isRaisingHand]
 * @property {boolean} [isCameraOn]
 * @property {boolean} [isScreenSharingOn]
 */

patch(DiscussChannelRtcSession, {
    awaitedRecords: new Map(),
    _insert() {
        /** @type {import("models").RtcSession} */
        const session = super._insert(...arguments);
        session.channel?.rtc_session_ids.add(session);
        return session;
    },
    /** @returns {Promise<import("models").RtcSession>} */
    async getWhenReady(id) {
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
    },
    /** @returns {import("models").RtcSession} */
    new() {
        const record = super.new(...arguments);
        this.awaitedRecords.get(record.id)?.resolve(record);
        this.awaitedRecords.delete(record.id);
        return record;
    },
});

/** @this {import("models").RtcSession} */
function setup() {
    /** @type {HTMLAudioElement} */
    this.audioElement;
    /** @type {MediaStream} */
    this.audioStream;
    /** @type {RTCDataChannel} */
    this.dataChannel;
    this.audioError;
    this.videoError;
    this.isTalking = fields.Attr(false, {
        /** @this {import("models").RtcSession} */
        onUpdate() {
            if (this.isTalking && !this.isMute) {
                this.talkingTime = this.store.nextTalkingTime++;
            }
            this.channel?.updateCallFocusStack(this);
        },
    });
    this.isActuallyTalking = fields.Attr(false, {
        /** @this {import("models").RtcSession} */
        compute() {
            return this.isTalking && !this.isMute;
        },
    });
    this.isVideoStreaming = fields.Attr(false, {
        /** @this {import("models").RtcSession} */
        compute() {
            return this.is_screen_sharing_on || this.is_camera_on;
        },
    });
    this.shortStatus = fields.Attr(undefined, {
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
    this.talkingTime = 0;
    this.localVolume;
    /** @type {RTCPeerConnection} */
    this.peerConnection;
    /** @type {Date|undefined} */
    this.raisingHand;
    this.videoComponentCount = 0;
    /** @type {Map<import("@mail/discuss/call/common/rtc_service").VideoType, MediaStream>} */
    this.videoStreams = new Map();
    /** @type {import("@mail/discuss/call/common/rtc_service").VideoType} */
    this.mainVideoStreamType;
    /**
     * Represents the sequence of the last valid connection with that session. This can be used to
     * compare connection attempts (if they follow the last valid connection) and to validate information
     * (if they match the sequence).
     *
     * @type {number}
     */
    this.sequence = 0;
    // RTC stats
    this.connectionState;
    this.logStep;
}

patch(DiscussChannelRtcSession.prototype, {
    setup() {
        super.setup(...arguments);
        setup.call(this);
    },
    _compute_partner_id() {
        return this.channel_member_id?.partner_id;
    },
    _compute_guest_id() {
        return this.channel_member_id?.guest_id;
    },
    _is_screen_sharing_on_onUpdate() {
        if (
            this.eq(this.channel?.activeRtcSession) &&
            this.mainVideoStreamType === "screen" &&
            !this.is_screen_sharing_on
        ) {
            this.channel.activeRtcSession = undefined;
        }
    },
    get persona() {
        return this.partner_id || this.guest_id;
    },
    get channel() {
        return this.channel_member_id?.channel_id?.channel;
    },
    get isMute() {
        return this.is_muted || this.is_deaf;
    },
    get mainVideoStream() {
        return this.isMainVideoStreamActive && this.videoStreams.get(this.mainVideoStreamType);
    },
    get isMainVideoStreamActive() {
        if (!this.mainVideoStreamType) {
            return false;
        }
        return this.mainVideoStreamType === "camera"
            ? this.is_camera_on
            : this.is_screen_sharing_on;
    },
    get hasVideo() {
        return this.is_screen_sharing_on || this.is_camera_on;
    },
    getStream(type) {
        const isActive = type === "camera" ? this.is_camera_on : this.is_screen_sharing_on;
        return isActive && this.videoStreams.get(type);
    },
    /** @returns {SessionInfo} */
    get info() {
        return {
            isSelfMuted: this.is_muted,
            isRaisingHand: Boolean(this.raisingHand),
            isDeaf: this.is_deaf,
            isTalking: this.isTalking,
            isCameraOn: this.is_camera_on,
            isScreenSharingOn: this.is_screen_sharing_on,
        };
    },
    /**
     * @returns {string}
     */
    get name() {
        return this.channel_member_id?.name;
    },
    /**
     * @returns {number} float
     */
    get volume() {
        return this.audioElement?.volume || this.localVolume;
    },
    /** @param {number} value */
    set volume(value) {
        if (this.audioElement) {
            this.audioElement.volume = value;
        }
        this.localVolume = value;
    },
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
    },
    /**
     * @param {import("@mail/discuss/call/common/rtc_service").StreamType} type
     * @param {boolean} state
     */
    updateStreamState(type, state) {
        if (type === "camera") {
            this.is_camera_on = state;
        } else if (type === "screen") {
            this.is_screen_sharing_on = state;
        }
    },
    delete() {
        if (this.eq(this.store.rtc.localSession)) {
            this.store.rtc.log(this, "self session deleted, ending call", { important: true });
            this.store.rtc.endCall();
        }
        this.store.rtc.disconnect(this);
        super.delete(...arguments);
    },
});
export const RtcSession = DiscussChannelRtcSession;
