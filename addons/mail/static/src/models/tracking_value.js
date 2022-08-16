/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'TrackingValue',
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeFormattedChangedField() {
            return sprintf(this.env._t("%s"), this.changedField);
        },
    },
    fields: {
        /**
         * States the original field of changed tracking value, such as "Status", "Date".
         */
        changedField: attr({
            required: true,
        }),
        /**
         * The translated `changedFiled` according to the language setting.
         */
        formattedChangedField: attr({
            compute: '_computeFormattedChangedField',
        }),
        id: attr({
            identifying: true,
            readonly: true,
            required: true,
        }),
        messageOwner: one('Message', {
            inverse: 'trackingValues',
            readonly: true,
            required: true,
        }),
        newValue: one('TrackingValueItem', {
            inverse: 'trackingValueAsNewValue',
            isCausal: true,
        }),
        oldValue: one('TrackingValueItem', {
            inverse: 'trackingValueAsOldValue',
            isCausal: true,
        }),
    },
});
