/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";

export class ActivityMenu extends Component {
    static components = { Dropdown };
    static props = [];
    static template = "mail.ActivityMenu";

    setup() {
        this.store = useState(useService("mail.store"));
        this.action = useService("action");
        this.userId = useService("user").userId;
        this.ui = useState(useService("ui"));
        this.fetchSystrayActivities();
    }

    async fetchSystrayActivities() {
        const groups = await this.env.services.orm.call("res.users", "systray_get_activities");
        let total = 0;
        for (const group of groups) {
            total += group.total_count || 0;
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
                domain = Domain.and([domain, group.domain]).toList();
            }
            this.action.doAction(
                {
                    domain,
                    name: group.name,
                    res_model: group.model,
                    type: "ir.actions.act_window",
                    views: this.availableViews(group),
                },
                { clearBreadcrumbs: true, viewType: "activity" }
            );
        }
    }

    openActivityGroup(group, filter = "all") {
        document.body.click(); // hack to close dropdown
        const context = {
            // Necessary because activity_ids of mail.activity.mixin has auto_join
            // So, duplicates are faking the count and "Load more" doesn't show up
            force_search_count: 1,
        };
        if (filter === "all") {
            context.search_default_activities_overdue = 1;
            context.search_default_activities_today = 1;
        } else {
            context["search_default_activities_" + filter] = 1;
        }
        let domain = [["activity_ids.user_id", "=", this.userId]];
        if (group.domain) {
            domain = Domain.and([domain, group.domain]).toList();
        }
        const views = this.availableViews(group);

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
            { clearBreadcrumbs: true }
        );
    }
}

registry
    .category("systray")
    .add("mail.activity_menu", { Component: ActivityMenu }, { sequence: 20 });
