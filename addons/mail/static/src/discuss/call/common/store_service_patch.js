import { fields } from "@mail/model/export";
import { Store } from "@mail/core/common/store_service";
import { router } from "@web/core/browser/router";

import { patch } from "@web/core/utils/patch";

/**
 * Shareable meeting link currently mirrored in the address bar, or `undefined` when not in the
 * full-screen meeting view. Kept in sync from the `_shareUrl` field below (which gates on the
 * full-screen state) and read back by the router patch below.
 * @type {string|undefined}
 */
let callShareUrl;

// The web client's router owns the address bar and recomputes it from the action state on every
// (debounced) push, so directly writing the meeting link with `history.replaceState` is
// immediately overwritten. Instead, teach the router to emit the link itself: its own pushes then
// render it and there is nothing left to race. `actionStack` is only present on the navigation
// state, so message/record link generation (which passes a bare `{ model, resId }`) keeps its
// normal url.
patch(router, {
    stateToUrl(state) {
        if (callShareUrl && Array.isArray(state.actionStack)) {
            const { pathname, search } = new URL(callShareUrl);
            return `${pathname}${search}`;
        }
        return super.stateToUrl(state);
    },
});

/** @type {import("models").Store} */
const StorePatch = {
    setup() {
        super.setup(...arguments);
        this.rtc = fields.One("Rtc", {
            compute() {
                return {};
            },
        });
        this.ringingChannels = fields.Many("discuss.channel", {
            /** @this {import("models").Store} */
            onUpdate() {
                if (this.ringingChannels.length > 0) {
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
        this.fullscreenChannel = fields.One("discuss.channel");
        this._hasFullscreenUrl = fields.Attr(false, {
            compute() {
                return this.discuss?.thread?.channel?.eq(this.fullscreenChannel);
            },
            onUpdate() {
                if (!this.discuss?.hasRestoredThread) {
                    return;
                }
                this._hasFullscreenUrlOnUpdate();
            },
            eager: true,
        });
        /**
         * Shareable link of the full-screen call, mirrored in the address bar while its meeting
         * view is open (and `undefined` otherwise). Depending on both the call and the full-screen
         * state, this recomputes whenever either changes — including when the invitation link
         * resolves (channel uuid loads) — so the address bar stays in sync no matter the order in
         * which they settle as a meeting starts. The patched {@link router.stateToUrl} renders the
         * mirrored value; the push here recomputes the address bar.
         *
         * Only for logged-in users: on the public meeting page the address bar already holds the
         * invitation link, and rewriting it through the web-client router (which has no action
         * state there) would clobber that link and lock the guest out on reload.
         */
        this._shareUrl = fields.Attr(undefined, {
            compute() {
                if (!this.self_user) {
                    return undefined;
                }
                return this.rtc.isFullscreen ? this.rtc.localChannel?.invitationLink : undefined;
            },
            onUpdate() {
                callShareUrl = this._shareUrl;
                router.replaceState({ fullscreen: this._hasFullscreenUrl ? true : undefined });
            },
            eager: true,
        });
        this.meetingViewOpened = false;
    },
    _hasFullscreenUrlOnUpdate() {
        if (callShareUrl) {
            return;
        }
        router.pushState({ fullscreen: this._hasFullscreenUrl ? true : undefined });
    },
    initialize() {
        super.initialize(...arguments);
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
