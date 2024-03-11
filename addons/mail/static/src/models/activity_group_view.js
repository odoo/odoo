/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

import session from 'web.session';

registerModel({
    name: 'ActivityGroupView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            ev.stopPropagation();
            this.activityMenuViewOwner.update({ isOpen: false });
            const targetAction = $(ev.currentTarget);
            const actionXmlid = targetAction.data('action_xmlid');
            if (actionXmlid) {
                this.env.services.action.doAction(actionXmlid);
            } else {
                let domain = [['activity_ids.user_id', '=', session.uid]];
                if (targetAction.data('domain')) {
                    domain = domain.concat(targetAction.data('domain'));
                }
                this.env.services['action'].doAction(
                    {
                        domain,
                        name: targetAction.data('model_name'),
                        res_model: targetAction.data('res_model'),
                        type: 'ir.actions.act_window',
                        views: this.activityGroup.irModel.availableWebViews.map(viewName => [false, viewName]),
                    },
                    {
                        clearBreadcrumbs: true,
                        viewType: 'activity',
                    },
                );
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickFilterButton(ev) {
            this.activityMenuViewOwner.update({ isOpen: false });
            // fetch the data from the button otherwise fetch the ones from the parent (.o_ActivityMenuView_activityGroup).
            const data = _.extend({}, $(ev.currentTarget).data(), $(ev.target).data());
            const context = {};
            if (data.filter === 'my') {
                context['search_default_activities_overdue'] = 1;
                context['search_default_activities_today'] = 1;
            } else {
                context['search_default_activities_' + data.filter] = 1;
            }
            // Necessary because activity_ids of mail.activity.mixin has auto_join
            // So, duplicates are faking the count and "Load more" doesn't show up
            context['force_search_count'] = 1;
            let domain = [['activity_ids.user_id', '=', session.uid]];
            if (data.domain) {
                domain = domain.concat(data.domain);
            }
            this.env.services['action'].doAction(
                {
                    context,
                    domain,
                    name: data.model_name,
                    res_model: data.res_model,
                    search_view_id: [false],
                    type: 'ir.actions.act_window',
                    views: this.activityGroup.irModel.availableWebViews.map(viewName => [false, viewName]),
                },
                {
                    clearBreadcrumbs: true,
                },
            );
        },
    },
    fields: {
        activityGroup: one('ActivityGroup', {
            identifying: true,
            inverse: 'activityGroupViews',
        }),
        activityMenuViewOwner: one('ActivityMenuView', {
            identifying: true,
            inverse: 'activityGroupViews',
        }),
    },
});
