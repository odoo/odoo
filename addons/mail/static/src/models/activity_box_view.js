/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'ActivityBoxView',
    identifyingFields: ['chatter'],
    recordMethods: {
        /**
         * Handles click on activity box title.
         */
        onClickActivityBoxTitle(ev) {
            ev.preventDefault();
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
        activityViews: many('ActivityView', {
            compute: '_computeActivityViews',
            inverse: 'activityBoxView',
            isCausal: true,
        }),
        chatter: one('Chatter', {
            inverse: 'activityBoxView',
            readonly: true,
            required: true,
        }),
        isActivityListVisible: attr({
            default: true,
        }),
    },
});
