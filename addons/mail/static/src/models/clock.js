/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many } from '@mail/model/model_field';

/**
 * Models a record that provides the current date, updated at a given frequency.
 */
registerModel({
    name: 'Clock',
    lifecycleHooks: {
        _created() {
            // The date is set here rather than via a default value so that the
            // date set at first is the time of the record creation, and not the
            // time of the model initialization.
            this.update({ date: new Date() });
        },
        _willDelete() {
            this.messaging.browser.clearInterval(this.tickInterval);
        },
    },
    recordMethods: {
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
        date: attr(),
        /**
         * An integer representing the frequency in milliseconds at which `date`
         * must be recomputed.
         */
        frequency: attr({
            identifying: true,
        }),
        tickInterval: attr({
            compute() {
                return this.messaging.browser.setInterval(this._onInterval, this.frequency);
            },
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
        {
            dependencies: ['watchers'],
            methodName: '_onChangeWatchers',
        },
    ],
});
