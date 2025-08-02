import { fields } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { browser } from "@web/core/browser/browser";

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
        this.rtcInvitingSession = fields.One("discuss.channel.rtc.session", {
            /** @this {import("models").Thread} */
            onAdd(r) {
                this.rtc_session_ids.add(r);
                this.store.ringingThreads.add(this);
                this.cancelRtcInvitationTimeout = browser.setTimeout(() => {
                    this.store.env.services["discuss.rtc"].leaveCall(this);
                }, 30000);
            },
            /** @this {import("models").Thread} */
            onDelete(r) {
                browser.clearTimeout(this.cancelRtcInvitationTimeout);
                this.store.ringingThreads.delete(this);
            },
        });
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
        this._screenStack = [];
        this._cameraStack = [];
    },
    get showCallView() {
        return !this.store.rtc.state.isFullscreen && this.rtc_session_ids.length > 0;
    },
    /**
     * @param {number} sessionId
     * @param {"add"|"remove"} action
     * @param {"screen"|"camera"} type
     */
    updateCallFocusStack(sessionId, action, type) {
        if (!this.eq(this.store.rtc?.channel)) {
            return;
        }
        const stack = type === "screen" ? this._screenStack : this._cameraStack;
        const index = stack.indexOf(sessionId);
        if (index !== -1) {
            stack.splice(index, 1);
        }
        if (action === "add") {
            stack.push(sessionId);
        }
        this._updateActiveSession();
    },

    _updateActiveSession() {
        if (!this.store.settings.useCallAutoFocus) {
            return;
        }
        let type = "screen";
        let activeSessionId = this._screenStack.at(-1);
        if (!activeSessionId) {
            type = "camera";
            activeSessionId = this._cameraStack.at(-1);
        }
        if (!activeSessionId) {
            // Ends the recursion if both stacks are emptied.
            return;
        }
        const activeSession = this.store["discuss.channel.rtc.session"].get(activeSessionId);
        if (activeSession) {
            this.activeRtcSession = activeSession;
            activeSession.mainVideoStreamType = type;
        } else {
            this.activeRtcSession = undefined;
            // Recursively clean and obtain the last existing session.
            this.updateCallFocusStack(activeSessionId, "remove", type);
        }
    },
};
patch(Thread.prototype, ThreadPatch);
