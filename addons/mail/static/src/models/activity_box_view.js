/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

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
    },
    fields: {
        activityViews: many('ActivityView', {
            compute() {
                return this.chatter.thread.activities.map(activity => {
                    return { activity };
                });
            },
            inverse: 'activityBoxView',
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
