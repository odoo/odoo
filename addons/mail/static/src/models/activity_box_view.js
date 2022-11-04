/** @odoo-module **/

import { attr, many, one, registerModel } from '@mail/model';

registerModel({
    name: 'ActivityBoxView',
    template: 'mail.ActivityBoxView',
    templateGetter: 'activityBoxView',
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
        activityViews: many('ActivityView', { inverse: 'activityBoxView',
            compute() {
                return this.chatter.thread.activities.map(activity => {
                    return { activity };
                });
            },
        }),
        chatter: one('Chatter', { identifying: true, inverse: 'activityBoxView' }),
        isActivityListVisible: attr({ default: true }),
    },
});
