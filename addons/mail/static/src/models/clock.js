/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';

/**
 * Models a record that provides the current date, updated at a given frequency.
 */
registerModel({
    name: 'Clock',
    identifyingFields: ['frequency'],
    lifecycleHooks: {
        _willDelete() {
            this.messaging.browser.clearInterval(this.tickInterval);
        },
    },
    recordMethods: {
        /**
         * The date is set by a compute rather than using a default value. Thus,
         * the date set at first is the time of the record creation, and not the
         * time of the model initialization.
         *
         * @private
         * @returns {Date}
         */
        _computeDate() {
            return new Date();
        },
        /**
         * @private
         * @returns {integer}
         */
        _computeTickInterval() {
            return this.messaging.browser.setInterval(this._onInterval, this.frequency);
        },
        /**
         * @private
         */
        _onChangeWatchers() {
            if (this.watchers.length === 0) {
                this.delete();
            }
        },
        /**
         * @private
         */
        _onInterval() {
            this.update({ date: new Date() });
        },
    },
    fields: {
        /**
         * A Date object set to the current date at the time the record is
         * created, then updated at every tick.
         */
        date: attr({
            compute: '_computeDate',
        }),
        /**
         * An integer representing the frequency in milliseconds at which `date`
         * must be recomputed.
         */
        frequency: attr({
            readonly: true,
            required: true,
        }),
        tickInterval: attr({
            compute: '_computeTickInterval',
        }),
        /**
         * The records that are making use of this clock.
         *
         * The clock self-destructs when there are no more watchers.
         */
        watchers: many('ClockWatcher', {
            inverse: 'clock',
            isCausal: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['watchers'],
            methodName: '_onChangeWatchers',
        }),
    ],
});
