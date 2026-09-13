// @ts-check
/** @odoo-module native */
import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import {
    readLocalStorageItem,
    setLocalStorageItem,
} from "@mail/utils/common/local_storage";
import { makeLogger } from "@web/core/debug/debug_logger";
import { patch } from "@web/core/utils/patch";

const log = makeLogger("mail.rtc");
export const CALL_PROMOTE_FULLSCREEN = Object.freeze({
    INACTIVE: "INACTIVE",
    ACTIVE: "ACTIVE",
    DISCARDED: "DISCARDED",
});

/** @type {Partial<import("models").Thread> & ThisType<import("models").Thread>} */
const ThreadPatch = {
    setup() {
        super.setup();
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
        this.promoteFullscreen = CALL_PROMOTE_FULLSCREEN.INACTIVE;
        this.hadSelfSession = false;
        /** @type {Set<number>} */
        this.lastSessionIds = new Set();
        /** @type {number|undefined} */
        this.cancelRtcInvitationTimeout;
        this.rtc_session_ids = fields.Many("discuss.channel.rtc.session", {
            /** @this {import("models").Thread} */
            onDelete(r) {
                this.store.env.services["discuss.rtc"].removeSession(r.id);
            },
            /** @this {import("models").Thread} */
            async onUpdate() {
                await this._onRtcSessionIdsUpdate();
            },
        });
        this.videoCountNotSelf = fields.Attr(0, {
            /** @this {import("models").Thread} */
            compute() {
                return this.rtc_session_ids.filter(
                    (s) => s.hasVideo && s.notEq(this.store.rtc.selfSession),
                ).length;
            },
            /** @this {import("models").Thread} */
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
            /** @this {import("models").Thread} */
            compute() {
                return this.rtc_session_ids.filter((s) => s.hasVideo).length;
            },
        });
        this.focusStack = fields.Many("discuss.channel.rtc.session");
        /** @type {import("@mail/discuss/call/common/call").CardData[]} */
        this.visibleCards = fields.Attr([], {
            /** @this {import("models").Thread} */
            compute() {
                return this._computeVisibleCards();
            },
        });
        this.useCameraByDefault = fields.Attr(null, {
            /** @this {import("models").Thread} */
            compute() {
                return this._computeUseCameraByDefault();
            },
            /** @this {import("models").Thread} */
            onUpdate() {
                if (this.useCameraByDefault !== null) {
                    setLocalStorageItem(
                        this.store,
                        this.cameraDefaultStorageKey,
                        JSON.stringify(this.useCameraByDefault),
                    );
                }
            },
        });
    },
    get hasCameraDefault() {
        return typeof this.useCameraByDefault === "boolean";
    },
    get cameraDefaultStorageKey() {
        return `discuss_channel_camera_default_${this.id}`;
    },
    /** @returns {any} */
    _computeUseCameraByDefault() {
        if (this.isDirectChat && this.store.rtc.selfSession?.channel?.eq(this)) {
            return this.store.rtc.selfSession.is_camera_on;
        }
        const raw = readLocalStorageItem(this.store, this.cameraDefaultStorageKey);
        if (!raw || raw === "undefined") {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    },
    /** @returns {import("@mail/discuss/call/common/call").CardData[]} */
    _computeVisibleCards() {
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
        raisingHandCards.sort(
            (c1, c2) => c1.session.raisingHand - c2.session.raisingHand,
        );
        sessionCards.sort(
            (c1, c2) =>
                c1.session.channel_member_id?.persona?.name?.localeCompare(
                    c2.session.channel_member_id?.persona?.name,
                ) ?? 1,
        );
        invitationCards.sort(
            (c1, c2) =>
                c1.member.persona?.name?.localeCompare(c2.member.persona?.name) ?? 1,
        );
        return raisingHandCards.concat(sessionCards, invitationCards);
    },
    async _onRtcSessionIdsUpdate() {
        const hadSelfSession = this.hadSelfSession;
        const lastSessionIds = this.lastSessionIds;
        this.hadSelfSession = Boolean(
            this.store.rtc.selfSession?.in(this.rtc_session_ids),
        );
        this.lastSessionIds = new Set(this.rtc_session_ids.map((s) => s.id));
        const shouldPlayJoinSound = [...this.lastSessionIds].some(
            (id) => !lastSessionIds.has(id),
        );
        const shouldPlayLeaveSound = [...lastSessionIds].some(
            (id) => !this.lastSessionIds.has(id),
        );
        if (
            !hadSelfSession ||
            !this.hadSelfSession ||
            !(await this.store.env.services["multi_tab"].isOnMainTab())
        ) {
            return;
        }
        log.pipeline("rtcSessionIds update", () => ({
            thread: this.localId,
            sessions: this.lastSessionIds.size,
            joined: shouldPlayJoinSound,
            left: shouldPlayLeaveSound,
        }));
        if (shouldPlayJoinSound) {
            this.store.env.services["mail.sound_effects"].play("call-join");
            this.store.rtc.call({ asFallback: true });
        }
        if (shouldPlayLeaveSound) {
            this.store.env.services["mail.sound_effects"].play("member-leave");
        }
    },
    get isCallDisplayedInChatWindow() {
        return this.chat_window?.isOpen && !this.store.meetingViewOpened;
    },
    get isSelfInCall() {
        return this.store.rtc.selfSession && this.eq(this.store.rtc.channel);
    },
    get showCallView() {
        return !this.store.rtc.state.isFullscreen && this.rtc_session_ids.length > 0;
    },
    focusAvailableVideo() {
        if (
            !this.store.settings.useCallAutoFocus ||
            !(
                this.store.env.services.ui.isSmall ||
                this.store.rtc.state.isPipMode ||
                this.isCallDisplayedInChatWindow
            )
        ) {
            return;
        }
        const otherStreamingSession = this.rtc_session_ids.find(
            (session) => session.notEq(this.store.rtc.selfSession) && session.hasVideo,
        );
        if (!otherStreamingSession) {
            return;
        }
        log.logic("focusAvailableVideo", () => ({
            thread: this.localId,
            session: otherStreamingSession.id,
        }));
        this.activeRtcSession = otherStreamingSession;
        otherStreamingSession.mainVideoStreamType =
            otherStreamingSession.is_screen_sharing_on ? "screen" : "camera";
    },
    /** @param {Object} [options] */
    open(options) {
        if (this.store.fullscreenChannel?.notEq(this)) {
            log.logic("open exits fullscreen of another channel", () => ({
                thread: this.localId,
                fullscreen: this.store.fullscreenChannel.localId,
            }));
            this.store.rtc.exitFullscreen();
        }
        return super.open(...arguments);
    },
    /** @param {import("models").RtcSession} session */
    updateCallFocusStack(session) {
        if (
            this.notEq(this.store.rtc?.channel) ||
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
