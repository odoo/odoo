/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";

export class ActivityMenu extends Component {
    setup() {
        this.activity = useState(useService("mail.activity").state);
        this.action = useService("action");
        this.userId = useService("user").userId;
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
        const domain = [["activity_ids.user_id", "=", this.userId]];
        const views = [
            [false, "kanban"],
            [false, "list"],
            [false, "form"],
            [false, "activity"],
        ];

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

Object.assign(ActivityMenu, {
    components: { Dropdown },
    props: [],
    template: "mail.activity_menu",
});
