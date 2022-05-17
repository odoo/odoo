/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Timer',
    identifyingFields: [[
        'otherMemberLongTypingInThreadTimerOwner',
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
        /**
         * Duration, in milliseconds, until timer times out and calls the
         * timeout function.
         */
        duration: attr({
            compute: '_computeDuration',
            readonly: true,
            required: true,
        }),
        otherMemberLongTypingInThreadTimerOwner: one('OtherMemberLongTypingInThreadTimer', {
            inverse: 'timer',
            isCausal: true,
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
