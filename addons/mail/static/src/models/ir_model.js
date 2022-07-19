/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'ir.model',
    identifyingFields: ['id'],
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
            required: true,
            readonly: true,
        }),
        model: attr({
            required: true,
        }),
        name: attr(),
    },
});
