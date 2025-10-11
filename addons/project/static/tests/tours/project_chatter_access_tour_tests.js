/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("project_chatter_log_disabled", {
    test: true,
    url: "/web",/*  */
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Project app",
            trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
        },
        {
            content: "Toggle a Project's dropdown",
            trigger: ".o_kanban_record .dropdown-toggle.o-no-caret",
        },
        {
            content: "Wait for kanban actions to load",
            trigger: ".dropdown-item.mx-0",
        },
        {
            content: "Check that Log Note button is disabled",
            trigger: ".o-mail-Chatter-logNote:disabled",
            isCheck: true,
        },
        {
            content: "Check that Log Note button is disabled",
            trigger: ".o-mail-Chatter-sendMessage:disabled",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("project_chatter_log_enabled", {
    test: true,
    url: "/web",/*  */
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Project app",
            trigger: '.o_app[data-menu-xmlid="project.menu_main_pm"]',
        },
        {
            content: "Toggle a Project's dropdown",
            trigger: ".o_kanban_record .dropdown-toggle.o-no-caret",
        },
        {
            content: "Wait for kanban actions to load",
            trigger: ".oe_kanban_action:contains('Settings')",
        },    
        {
            content: "Check that Log Note button is disabled",
            trigger: ".o-mail-Chatter-logNote:not(:disabled)",
            isCheck: true,
        },
        {
            content: "Check that Log Note button is disabled",
            trigger: ".o-mail-Chatter-sendMessage:not(:disabled)",
            isCheck: true,
        },
    ],
});
