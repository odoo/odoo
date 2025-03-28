import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { browser } from "@web/core/browser/browser";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const ThreadPatch = {
    setup() {
        super.setup(...arguments);
        this.activeRtcSession = Record.one("RtcSession", {
            /** @this {import("models").Thread} */
            onAdd(r) {
                this.store.allActiveRtcSessions.add(r);
            },
            /** @this {import("models").Thread} */
            onDelete(r) {
                this.store.allActiveRtcSessions.delete(r);
            },
        });
        this.hadSelfSession = false;
        this.lastSessionIds = new Set();
        /** @type {number|undefined} */
        this.cancelRtcInvitationTimeout;
        this.rtcInvitingSession = Record.one("RtcSession", {
            /** @this {import("models").Thread} */
            onAdd(r) {
                this.rtcSessions.add(r);
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
        this.rtcSessions = Record.many("RtcSession", {
            /** @this {import("models").Thread} */
            onDelete(r) {
                this.store.env.services["discuss.rtc"].deleteSession(r.id);
            },
            /** @this {import("models").Thread} */
            onUpdate() {
                const hadSelfSession = this.hadSelfSession;
                const lastSessionIds = this.lastSessionIds;
                this.hadSelfSession = Boolean(this.store.rtc.selfSession?.in(this.rtcSessions));
                this.lastSessionIds = new Set(this.rtcSessions.map((s) => s.id));
                if (
                    !hadSelfSession || // sound for self-join is played instead
                    !this.hadSelfSession || // sound for self-leave is played instead
                    !this.store.env.services["multi_tab"].isOnMainTab() // another tab playing sound
                ) {
                    return;
                }
                if ([...this.lastSessionIds].some((id) => !lastSessionIds.has(id))) {
                    this.store.env.services["mail.sound_effects"].play("channel-join");
                    this.store.rtc.call({ asFallback: true });
                }
                if ([...lastSessionIds].some((id) => !this.lastSessionIds.has(id))) {
                    this.store.env.services["mail.sound_effects"].play("member-leave");
                }
            },
        });
    },
    get videoCount() {
        return Object.values(this.store.RtcSession.records).filter((session) => session.hasVideo)
            .length;
    },
};
patch(Thread.prototype, ThreadPatch);
