/* @odoo-module */

import { useMessaging, useStore } from "@mail/core/common/messaging_hook";

import { Component, useState } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ActivityMenu extends Component {
    static components = { Dropdown };
    static props = [];
    static template = "mail.ActivityMenu";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.action = useService("action");
        this.userId = useService("user").userId;
        this.ui = useState(useService("ui"));
        this.fetchSystrayActivities();
    }

    async fetchSystrayActivities() {
        const groups = await this.env.services.orm.call("res.users", "systray_get_activities");
        let total = 0;
        for (const group of groups) {
            total += group.total_count;
        }
        this.store.activityCounter = total;
        this.store.activityGroups = groups;
        this.sortActivityGroups();
    }

    sortActivityGroups() {
        this.store.activityGroups.sort((g1, g2) => g1.id - g2.id);
    }

    onBeforeOpen() {
        this.fetchSystrayActivities();
    }

    availableViews(group) {
        return [
            [false, "kanban"],
            [false, "list"],
            [false, "form"],
            [false, "activity"],
        ];
    }

    onClickAction(action, group) {
        document.body.click(); // hack to close dropdown
        if (action.action_xmlid) {
            this.env.services.action.doAction(action.action_xmlid);
        } else {
            let domain = [["activity_ids.user_id", "=", this.userId]];
            if (group.domain) {
                domain = domain.concat(group.domain);
            }
            this.action.doAction(
                {
                    domain,
                    name: group.name,
                    res_model: group.model,
                    type: "ir.actions.act_window",
                    views: this.availableViews(group),
                },
                { clearBreadcrumbs: true , viewType: "activity" }
            );
        }
    }

    /**
     * Allow to define the view type used for opening an activity group.
     *
     * Meant to be overridden by other modules to define custom view type per model.
     *
     * @param {string} model The model for which the view type needs to be determined.
     * @returns {string} view type for the given model.
     */
    getActivityGroupViewType(model) {
        return "list";
    }

    openActivityGroup(group) {
        document.body.click(); // hack to close dropdown
        const context = {
            // Necessary because activity_ids of mail.activity.mixin has auto_join
            // So, duplicates are faking the count and "Load more" doesn't show up
            force_search_count: 1,
        };
        const domain = [["activity_ids.user_id", "=", this.userId]];
        const views = this.availableViews(group);

        const viewType = this.getActivityGroupViewType(group.model);
        this.action.doAction(
            {
                context,
                domain,
                name: group.name,
                res_model: group.model,
                search_view_id: [false],
                type: "ir.actions.act_window",
                views,
            },
            { clearBreadcrumbs: true, viewType: viewType }
        );
    }
}

registry
    .category("systray")
    .add("mail.activity_menu", { Component: ActivityMenu }, { sequence: 20 });
