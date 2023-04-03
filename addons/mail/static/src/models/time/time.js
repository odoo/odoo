/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'Time',
    identifyingFields: ['messaging'],
    lifecycleHooks: {
        _willDelete() {
            clearInterval(this.everyMinuteIntervalId);
        },
    },
    recordMethods: {
        _computeCurrentDateEveryMinute() {
            return new Date();
        },
        /**
         * @private
         * @returns {number}
         */
        _computeEveryMinuteIntervalId() {
            return setInterval(this._onEveryMinuteTimeout, 60 * 1000);
        },
        /**
         * @private
         */
        _onEveryMinuteTimeout() {
            this.update({ currentDateEveryMinute: new Date() });
        },
    },
    fields: {
        /**
         * Contains a Date object that is set to the current time, and is
         * (re-)computed every minute.
         */
        currentDateEveryMinute: attr({
            compute: '_computeCurrentDateEveryMinute',
        }),
        everyMinuteIntervalId: attr({
            compute: '_computeEveryMinuteIntervalId',
        }),
    },
});
