import { fields } from "@mail/core/common/record";
import { Store } from "@mail/core/common/store_service";
import { router } from "@web/core/browser/router";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.rtc = fields.One("Rtc", {
            compute() {
                return {};
            },
        });
        this.ringingThreads = fields.Many("Thread", {
            /** @this {import("models").Store} */
            onUpdate() {
                if (this.ringingThreads.length > 0) {
                    this.env.services["mail.sound_effects"].play("call-invitation", {
                        loop: true,
                    });
                } else {
                    this.env.services["mail.sound_effects"].stop("call-invitation");
                }
            },
        });
        this.allActiveRtcSessions = fields.Many("discuss.channel.rtc.session");
        this.nextTalkingTime = 1;
        this.fullscreenChannel = fields.One("Thread");
        this._hasFullscreenUrl = fields.Attr(false, {
            compute() {
                return this.discuss?.thread?.eq(this.fullscreenChannel);
            },
            onUpdate() {
                if (!this.discuss?.hasRestoredThread) {
                    return;
                }
                this._hasFullscreenUrlOnUpdate();
            },
            eager: true,
        });
        this.meetingViewOpened = false;
    },
    _hasFullscreenUrlOnUpdate() {
        router.pushState({
            fullscreen: this._hasFullscreenUrl ? true : undefined,
        });
    },
    onStarted() {
        super.onStarted(...arguments);
        this.rtc.start();
    },
    sortMembers(m1, m2) {
        const m1HasRtc = Boolean(m1.rtcSession);
        const m2HasRtc = Boolean(m2.rtcSession);
        if (m1HasRtc === m2HasRtc) {
            /**
             * If raisingHand is falsy, it gets an Infinity value so that when
             * we sort by [oldest/lowest-value]-first, falsy values end up last.
             */
            const m1RaisingValue = m1.rtcSession?.raisingHand || Infinity;
            const m2RaisingValue = m2.rtcSession?.raisingHand || Infinity;
            if (m1HasRtc && m1RaisingValue !== m2RaisingValue) {
                return m1RaisingValue - m2RaisingValue;
            } else {
                return super.sortMembers(m1, m2);
            }
        } else {
            return m2HasRtc - m1HasRtc;
        }
    },
};
patch(Store.prototype, StorePatch);
