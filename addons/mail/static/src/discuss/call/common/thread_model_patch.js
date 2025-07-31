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
    },
    get showCallView() {
        return !this.store.rtc.state.isFullscreen && this.rtc_session_ids.length > 0;
    },
};
patch(Thread.prototype, ThreadPatch);
