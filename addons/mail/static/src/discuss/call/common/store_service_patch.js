import { Store } from "@mail/core/common/store_service";
import { fields } from "@mail/model/export";

import { computed } from "@odoo/owl";
import { router } from "@web/core/browser/router";

import { patch } from "@web/core/utils/patch";

/**
 * Shareable meeting link currently mirrored in the address bar, or `undefined` when not in the
 * @type {string|undefined}
 */
let callShareUrl;

function routerOwnsAddressBar() {
    return Array.isArray(router.current.actionStack);
}

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
        this.rtc = fields.One("Rtc");
        this.ringingChannels = fields.Many("discuss.channel");
        const hasRingingChannels = computed(() => this.ringingChannels.length > 0);
        this.onChange(
            () => [hasRingingChannels()],
            function onChangeRingingChannels(shouldPlay) {
                if (shouldPlay) {
                    this.env.services["mail.sound_effects"].play("call-invitation", { loop: true });
                    return () => this.env.services["mail.sound_effects"].stop("call-invitation");
                }
            }
        );
        this.nextTalkingTime = 1;
        this.fullscreenChannel = fields.One("discuss.channel");
        this.meetingViewOpened = false;
        this.onChange(
            () => [this.hasFullscreenUrl],
            function onChangeHasFullscreenUrl(hasFullscreenUrl) {
                if (this.discuss?.hasRestoredThread) {
                    this.hasFullscreenUrlOnUpdate(hasFullscreenUrl);
                }
            }
        );
        /**
         *
         */
        this.onChange(
            () => [
                this.self_user && this.rtc?.isFullscreen
                    ? this.rtc.localChannel?.invitationLink
                    : undefined,
            ],
            function onChangeShareUrl(shareUrl) {
                if (!routerOwnsAddressBar() || shareUrl === callShareUrl) {
                    return;
                }
                callShareUrl = shareUrl;
                router.replaceState({ fullscreen: this.hasFullscreenUrl ? true : undefined });
            }
        );
    },
    get hasFullscreenUrl() {
        return this.discuss?.thread?.channel?.eq(this.fullscreenChannel);
    },
    /** @param {boolean} hasFullscreenUrl */
    hasFullscreenUrlOnUpdate(hasFullscreenUrl) {
        // the public page writes the address bar itself, so the router push is
        // for the web client only
        if (callShareUrl || !routerOwnsAddressBar()) {
            return;
        }
        router.pushState({ fullscreen: hasFullscreenUrl ? true : undefined });
    },
    initialize() {
        super.initialize(...arguments);
        this.rtc = {};
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
