/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2many, one2one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ActivityBoxView',
    identifyingFields: ['chatter'],
    lifecycleHooks: {
        _created() {
            // Bind necessary until OWL supports arrow function in handlers: https://github.com/odoo/owl/issues/876
            this.onClickActivityBoxTitle = this.onClickActivityBoxTitle.bind(this);
        },
    },
    recordMethods: {
        /**
         * Handles click on activity box title.
         */
        onClickActivityBoxTitle() {
            this.update({ isActivityListVisible: !this.isActivityListVisible });
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActivityViews() {
            return insertAndReplace(this.chatter.thread.activities.map(activity => {
                return { activity: replace(activity) };
            }));
        },
    },
    fields: {
        activityViews: one2many('ActivityView', {
            compute: '_computeActivityViews',
            inverse: 'activityBoxView',
            isCausal: true,
        }),
        chatter: one2one('Chatter', {
            inverse: 'activityBoxView',
            readonly: true,
            required: true,
        }),
        isActivityListVisible: attr({
            default: true,
        }),
    },

});
