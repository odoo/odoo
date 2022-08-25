/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ir.model',
    recordMethods: {
        /**
         * @private
         * @returns {string[]}
         */
        _computeAvailableWebViews() {
            return ['kanban', 'list', 'form', 'activity'];
        },
    },
    fields: {
        /**
         * Determines the name of the views that are available for this model.
         */
        availableWebViews: attr({
            compute: '_computeAvailableWebViews',
        }),
        activityGroup: one('ActivityGroup', {
            inverse: 'irModel',
            isCausal: true,
        }),
        iconUrl: attr(),
        id: attr({
            identifying: true,
        }),
        model: attr({
            required: true,
        }),
        name: attr(),
    },
});
