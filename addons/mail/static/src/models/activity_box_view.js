/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'ActivityBoxView',
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
                return { activity };
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
            identifying: true,
            inverse: 'activityBoxView',
        }),
        isActivityListVisible: attr({
            default: true,
        }),
    },
});
