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
            /** @this {import("models").Thread} */
            onDelete(r) {
                this.store.env.services["discuss.rtc"].deleteSession(r.id);
            },
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
        /** @type {import("@mail/discuss/call/common/call").CardData[]"} */
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
    },
    get showCallView() {
        return !this.store.rtc.state.isFullscreen && this.rtc_session_ids.length > 0;
    },
};
patch(Thread.prototype, ThreadPatch);
