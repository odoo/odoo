/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';

registerPatch({
    name: 'ActivityGroupView',
    recordMethods: {
        /**
         * @override
         */
        onClickFilterButton(ev) {
            // fetch the data from the button otherwise fetch the ones from the parent (.o_ActivityMenuView_activityGroup).
            var data = _.extend({}, $(ev.currentTarget).data(), $(ev.target).data());
            var context = {};
            if (data.res_model === "crm.lead") {
                this.activityMenuViewOwner.update({ isOpen: false });
                if (data.filter === 'my') {
                    context['search_default_activities_overdue'] = 1;
                    context['search_default_activities_today'] = 1;
                } else {
                    context['search_default_activities_' + data.filter] = 1;
                }
                // Necessary because activity_ids of mail.activity.mixin has auto_join
                // So, duplicates are faking the count and "Load more" doesn't show up
                context['force_search_count'] = 1;
                this.env.services['action'].doAction('crm.crm_lead_action_my_activities', {
                    additionalContext: context,
                    clearBreadcrumbs: true,
                });
            } else {
                this._super.apply(this, arguments);
            }
        },
    },
});
