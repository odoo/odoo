import { Component, useState } from "@odoo/owl";

import { useDiscussSystray } from "@mail/utils/common/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { user } from "@web/core/user";

export class ActivityMenu extends Component {
    static components = { Dropdown };
    static props = [];
    static template = "mail.ActivityMenu";

    setup() {
        super.setup();
        this.discussSystray = useDiscussSystray();
        this.store = useState(useService("mail.store"));
        this.action = useService("action");
        this.userId = user.userId;
        this.ui = useState(useService("ui"));
        this.dropdown = useDropdownState();
    }

    onBeforeOpen() {
        this.store.fetchData({ systray_get_activities: true });
    }

    availableViews(group) {
        return [
            [false, "kanban"],
            [false, "list"],
            [false, "form"],
            [false, "activity"],
        ];
    }

    openActivityGroup(group, filter="all") {
        this.dropdown.close();
        const context = {
            // Necessary because activity_ids of mail.activity.mixin has auto_join
            // So, duplicates are faking the count and "Load more" doesn't show up
            force_search_count: 1,
        };
        if (group.model === "mail.activity") {
            this.action.doAction("mail.mail_activity_without_access_action", {
                additionalContext: {
                    active_ids: group.activity_ids,
                    active_model: "mail.activity",
                },
            });
            return;
        }

        if (filter === "all") {
            context["search_default_activities_overdue"] = 1;
            context["search_default_activities_today"] = 1;
        }
        else if (filter === "overdue") {
            context["search_default_activities_overdue"] = 1;
        }
        else if (filter === "today") {
            context["search_default_activities_today"] = 1;
        }
        else if (filter === "upcoming_all") {
            context["search_default_activities_upcoming_all"] = 1;
        }

        let domain = [["activity_user_id", "=", this.userId]];
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
            {
                clearBreadcrumbs: true,
                viewType: group.view_type,
            }
        );
    }

    openMyActivities() {
        this.dropdown.close();
        this.action.doAction("mail.mail_activity_action_my", { clearBreadcrumbs: true });
    }
}

registry
    .category("systray")
    .add("mail.activity_menu", { Component: ActivityMenu }, { sequence: 20 });
