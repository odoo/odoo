/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Timer',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            this.update({ timeoutId: this.messaging.browser.setTimeout(this._onTimeout, this.duration) });
        },
        _willDelete() {
            this.messaging.browser.clearTimeout(this.timeoutId);
        },
    },
    recordMethods: {
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeDuration() {
            if (this.callMainViewAsShowOverlay) {
                return 3 * 1000;
            }
            if (this.chatterOwnerAsAttachmentsLoader) {
                return this.messaging.loadingBaseDelayDuration;
            }
            if (this.messageViewOwnerAsHighlight) {
                return 2 * 1000;
            }
            if (this.messagingOwnerAsFetchImStatusTimer) {
                return this.messagingOwnerAsFetchImStatusTimer.fetchImStatusTimerDuration;
            }
            if (this.rtcSessionOwnerAsBroadcast) {
                return 3 * 1000;
            }
            if (this.threadAsCurrentPartnerInactiveTypingTimerOwner) {
                return 5 * 1000;
            }
            if (this.threadAsCurrentPartnerLongTypingTimerOwner) {
                return 50 * 1000;
            }
            if (this.otherMemberLongTypingInThreadTimerOwner) {
                return 60 * 1000;
            }
            if (this.throttleOwner) {
                return this.throttleOwner.duration;
            }
            return clear();
        },
        /**
         * @private
         */
        _onTimeout() {
            this.update({ timeoutId: clear() });
            if (this.callMainViewAsShowOverlay) {
                this.callMainViewAsShowOverlay.onShowOverlayTimeout();
                return;
            }
            if (this.chatterOwnerAsAttachmentsLoader) {
                this.chatterOwnerAsAttachmentsLoader.onAttachmentsLoadingTimeout();
                return;
            }
            if (this.messageViewOwnerAsHighlight) {
                this.messageViewOwnerAsHighlight.onHighlightTimerTimeout();
                return;
            }
            if (this.messagingOwnerAsFetchImStatusTimer) {
                this.messagingOwnerAsFetchImStatusTimer.onFetchImStatusTimerTimeout();
                return;
            }
            if (this.rtcSessionOwnerAsBroadcast) {
                this.rtcSessionOwnerAsBroadcast.onBroadcastTimeout();
                return;
            }
            if (this.threadAsCurrentPartnerInactiveTypingTimerOwner) {
                this.threadAsCurrentPartnerInactiveTypingTimerOwner.onCurrentPartnerInactiveTypingTimeout();
                return;
            }
            if (this.threadAsCurrentPartnerLongTypingTimerOwner) {
                this.threadAsCurrentPartnerLongTypingTimerOwner.onCurrentPartnerLongTypingTimeout();
                return;
            }
            if (this.otherMemberLongTypingInThreadTimerOwner) {
                this.otherMemberLongTypingInThreadTimerOwner.onOtherMemberLongTypingTimeout();
                return;
            }
            if (this.throttleOwner) {
                this.throttleOwner.onTimeout();
                return;
            }
        },
        _onChangeDoReset() {
            if (!this.doReset) {
                return;
            }
            this.messaging.browser.clearTimeout(this.timeoutId);
            this.update({
                doReset: clear(),
                timeoutId: this.messaging.browser.setTimeout(this._onTimeout, this.duration),
            });
        },
    },
    fields: {
        callMainViewAsShowOverlay: one('CallMainView', {
            identifying: true,
            inverse: 'showOverlayTimer',
        }),
        chatterOwnerAsAttachmentsLoader: one('Chatter', {
            identifying: true,
            inverse: 'attachmentsLoaderTimer',
        }),
        doReset: attr({
            default: false,
        }),
        /**
         * Duration, in milliseconds, until timer times out and calls the
         * timeout function.
         */
        duration: attr({
            compute: '_computeDuration',
            readonly: true,
            required: true,
        }),
        messagingOwnerAsFetchImStatusTimer: one('Messaging', {
            identifying: true,
            inverse: 'fetchImStatusTimer',
        }),
        messageViewOwnerAsHighlight: one('MessageView', {
            identifying: true,
            inverse: 'highlightTimer',
        }),
        otherMemberLongTypingInThreadTimerOwner: one('OtherMemberLongTypingInThreadTimer', {
            identifying: true,
            inverse: 'timer',
            isCausal: true,
        }),
        rtcSessionOwnerAsBroadcast: one('RtcSession', {
            identifying: true,
            inverse: 'broadcastTimer',
        }),
        threadAsCurrentPartnerInactiveTypingTimerOwner: one('Thread', {
            identifying: true,
            inverse: 'currentPartnerInactiveTypingTimer',
        }),
        threadAsCurrentPartnerLongTypingTimerOwner: one('Thread', {
            identifying: true,
            inverse: 'currentPartnerLongTypingTimer',
        }),
        throttleOwner: one('Throttle', {
            identifying: true,
            inverse: 'cooldownTimer',
        }),
        /**
         * Internal reference of `setTimeout()` that is used to invoke function
         * when timer times out. Useful to clear it when timer is cleared/reset.
         */
        timeoutId: attr(),
    },
    onChanges: [
        {
            dependencies: ["doReset"],
            methodName: '_onChangeDoReset',
        },
    ],
});
