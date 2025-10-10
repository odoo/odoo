import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

export const CALL_PROMOTE_FULLSCREEN = Object.freeze({
    INACTIVE: "INACTIVE",
    ACTIVE: "ACTIVE",
    DISCARDED: "DISCARDED",
});

/** @type {import("models").Thread} */
const ThreadPatch = {
    setup() {
        super.setup(...arguments);
        this.activeRtcSession = fields.One("discuss.channel.rtc.session", {
            /** @this {import("models").Thread} */
            onAdd(r) {
                this.store.allActiveRtcSessions.add(r);
            },
            /** @this {import("models").Thread} */
            onDelete(r) {
                this.store.allActiveRtcSessions.delete(r);
            },
        });
        /** @type {typeof CALL_PROMOTE_FULLSCREEN[keyof CALL_PROMOTE_FULLSCREEN]} */
        this.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.DISABLED;
        this.hadSelfSession = false;
        /** @type {Set<number>} */
        this.lastSessionIds = new Set();
        /** @type {number|undefined} */
        this.cancelRtcInvitationTimeout;
        this.rtc_session_ids = fields.Many("discuss.channel.rtc.session", {
            onDelete: (r) => r?.delete(),
            /** @this {import("models").Thread} */
            async onUpdate() {
                const hadSelfSession = this.hadSelfSession;
                const lastSessionIds = this.lastSessionIds;
                this.hadSelfSession = Boolean(this.store.rtc.selfSession?.in(this.rtc_session_ids));
                this.lastSessionIds = new Set(this.rtc_session_ids.map((s) => s.id));
                const shouldPlayJoinSound = [...this.lastSessionIds].some(
                    (id) => !lastSessionIds.has(id)
                );
                const shouldPlayLeaveSound = [...lastSessionIds].some(
                    (id) => !this.lastSessionIds.has(id)
                );
                if (
                    !hadSelfSession || // sound for self-join is played instead
                    !this.hadSelfSession || // sound for self-leave is played instead
                    !(await this.store.env.services["multi_tab"].isOnMainTab()) // another tab playing sound
                ) {
                    return;
                }
                if (shouldPlayJoinSound) {
                    this.store.env.services["mail.sound_effects"].play("call-join");
                    this.store.rtc.call({ asFallback: true });
                }
                if (shouldPlayLeaveSound) {
                    this.store.env.services["mail.sound_effects"].play("member-leave");
                }
            },
        });
        this.videoCountNotSelf = fields.Attr(0, {
            compute() {
                return this.rtc_session_ids.filter(
                    (s) => s.hasVideo && s.notEq(this.store.rtc.selfSession)
                ).length;
            },
            onUpdate() {
                if (this.promoteFullscreen === CALL_PROMOTE_FULLSCREEN.DISCARDED) {
                    return;
                }
                this.promoteFullscreen =
                    this.videoCountNotSelf > 0 && this.chat_window?.isOpen
                        ? CALL_PROMOTE_FULLSCREEN.ACTIVE
                        : CALL_PROMOTE_FULLSCREEN.INACTIVE;
            },
        });
        this.videoCount = fields.Attr(0, {
            compute() {
                return this.rtc_session_ids.filter((s) => s.hasVideo).length;
            },
        });
        this.focusStack = fields.Many("discuss.channel.rtc.session");
        /** @type {import("@mail/discuss/call/common/call").CardData[]} */
        this.visibleCards = fields.Attr([], {
            compute() {
                const raisingHandCards = [];
                const sessionCards = [];
                const invitationCards = [];
                const filterVideos = this.store.settings.showOnlyVideo && this.videoCount > 0;
                for (const session of this.rtc_session_ids) {
                    const target = session.raisingHand ? raisingHandCards : sessionCards;
                    const cameraStream = session.is_camera_on
                        ? session.videoStreams.get("camera")
                        : undefined;
                    if (!filterVideos || cameraStream) {
                        target.push({
                            key: "session_main_" + session.id,
                            session,
                            type: "camera",
                            videoStream: cameraStream,
                        });
                    }
                    const screenStream = session.is_screen_sharing_on
                        ? session.videoStreams.get("screen")
                        : undefined;
                    if (screenStream) {
                        target.push({
                            key: "session_secondary_" + session.id,
                            session,
                            type: "screen",
                            videoStream: screenStream,
                        });
                    }
                }
                if (!filterVideos) {
                    for (const member of this.invited_member_ids) {
                        invitationCards.push({ key: "member_" + member.id, member });
                    }
                }
                raisingHandCards.sort((c1, c2) => c1.session.raisingHand - c2.session.raisingHand);
                sessionCards.sort(
                    (c1, c2) =>
                        c1.session.channel_member_id?.persona?.name?.localeCompare(
                            c2.session.channel_member_id?.persona?.name
                        ) ?? 1
                );
                invitationCards.sort(
                    (c1, c2) => c1.member.persona?.name?.localeCompare(c2.member.persona?.name) ?? 1
                );
                return raisingHandCards.concat(sessionCards, invitationCards);
            },
        });
        this.useCameraByDefault = fields.Attr(null, {
            /** @this {import("models").Thread} */
            compute() {
                if (
                    this.channel?.channel_type === "chat" &&
                    this.store.rtc.selfSession?.channel?.eq(this.channel)
                ) {
                    return this.store.rtc.selfSession.is_camera_on;
                }
                return JSON.parse(
                    localStorage.getItem(`discuss_channel_camera_default_${this.id}`)
                );
            },
            /** @this {import("models").Thread} */
            onUpdate() {
                if (this.useCameraByDefault !== null) {
                    localStorage.setItem(
                        `discuss_channel_camera_default_${this.id}`,
                        JSON.stringify(this.useCameraByDefault)
                    );
                }
            },
        });
    },
    get showCallView() {
        return !this.store.rtc.state.isFullscreen && this.rtc_session_ids.length > 0;
    },
    focusAvailableVideo() {
        if (this.isDisplayedInDiscussAppDesktop || !this.store.settings.useCallAutoFocus) {
            return;
        }
        const otherStreamingSession = this.rtc_session_ids.find((session) => {
            session.notEq(this.store.rtc.selfSession) && session.hasVideo;
        });
        if (!otherStreamingSession) {
            return;
        }
        this.activeRtcSession = otherStreamingSession;
        otherStreamingSession.mainVideoStreamType = otherStreamingSession.is_screen_sharing_on
            ? "screen"
            : "camera";
    },
    open(options) {
        if (this.store.fullscreenChannel?.notEq(this.channel)) {
            this.store.rtc.exitFullscreen();
        }
        super.open(...arguments);
    },
    /**
     * @param {import("models").RtcSession} session
     */
    updateCallFocusStack(session) {
        if (
            this.channel?.notEq(this.store.rtc?.channel) ||
            session.eq(this.store.rtc.selfSession) ||
            !this.activeRtcSession ||
            !this.store.settings.useCallAutoFocus ||
            this.activeRtcSession?.mainVideoStreamType === "screen"
        ) {
            return;
        }
        this.focusStack.delete(session);
        if (session.isTalking && !session.isMute) {
            this.focusStack.push(session);
        }
        const activeSession = this.focusStack.at(-1);
        if (!activeSession) {
            return;
        }
        this.activeRtcSession = activeSession;
        activeSession.mainVideoStreamType = "camera";
    },
};
patch(Thread.prototype, ThreadPatch);
