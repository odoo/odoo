/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Timer',
    identifyingFields: [[
        'callViewAsShowOverlay',
        'chatterOwnerAsAttachmentsLoader',
        'messagingOwnerAsFetchImStatusTimer',
        'messageViewOwnerAsHighlight',
        'otherMemberLongTypingInThreadTimerOwner',
        'rtcSessionOwnerAsBroadcast',
        'threadAsCurrentPartnerInactiveTypingTimerOwner',
        'threadAsCurrentPartnerLongTypingTimerOwner',
        'throttleOwner',
    ]],
    lifecycleHooks: {
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
            if (this.callViewAsShowOverlay) {
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
         * @returns {number}
         */
        _computeTimeoutId() {
            if (this.duration === undefined) {
                return; // ensure duration is computed first
            }
            if (this.timeoutId) {
                return;
            }
            return this.messaging.browser.setTimeout(this._onTimeout, this.duration);
        },
        /**
         * @private
         */
        _onTimeout() {
            this._onTimeoutOwner();
            if (this.exists()) { // owner might have deleted the timer itself
                this.delete();
            }
        },
        /**
         * @private
         */
        _onTimeoutOwner() {
            if (this.callViewAsShowOverlay) {
                this.callViewAsShowOverlay.onShowOverlayTimeout();
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
    },
    fields: {
        callViewAsShowOverlay: one('CallView', {
            inverse: 'showOverlayTimer',
            readonly: true,
        }),
        chatterOwnerAsAttachmentsLoader: one('Chatter', {
            inverse: 'attachmentsLoaderTimer',
            readonly: true,
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
            inverse: 'fetchImStatusTimer',
            readonly: true,
        }),
        messageViewOwnerAsHighlight: one('MessageView', {
            inverse: 'highlightTimer',
            readonly: true,
        }),
        otherMemberLongTypingInThreadTimerOwner: one('OtherMemberLongTypingInThreadTimer', {
            inverse: 'timer',
            isCausal: true,
            readonly: true,
        }),
        rtcSessionOwnerAsBroadcast: one('RtcSession', {
            inverse: 'broadcastTimer',
            readonly: true,
        }),
        threadAsCurrentPartnerInactiveTypingTimerOwner: one('Thread', {
            inverse: 'currentPartnerInactiveTypingTimer',
            readonly: true,
        }),
        threadAsCurrentPartnerLongTypingTimerOwner: one('Thread', {
            inverse: 'currentPartnerLongTypingTimer',
            readonly: true,
        }),
        throttleOwner: one('Throttle', {
            inverse: 'cooldownTimer',
            readonly: true,
        }),
        /**
         * Internal reference of `setTimeout()` that is used to invoke function
         * when timer times out. Useful to clear it when timer is cleared/reset.
         */
        timeoutId: attr({
            compute: '_computeTimeoutId',
            readonly: true,
            required: true,
        }),
    },
});
