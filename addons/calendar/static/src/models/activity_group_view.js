/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ActivityGroupView',
    recordMethods: {
        /**
         * @override
         */
        onClickFilterButton(ev) {
            const $el = $(ev.currentTarget);
            const data = _.extend({}, $el.data());
            if (data.res_model === "calendar.event" && data.filter === "my") {
                this.activityMenuViewOwner.update({ isOpen: false });
                this.env.services['action'].doAction('calendar.action_calendar_event', {
                    additionalContext: {
                        default_mode: 'day',
                        search_default_mymeetings: 1,
                    },
                    clearBreadcrumbs: true,
                });
            } else {
                this._super.apply(this, arguments);
            }
        },
    },
});
