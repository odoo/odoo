/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("crm_rainbowman", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_app[data-menu-xmlid='crm.crm_menu_root']",
            content: "open crm app",
            run: "click",
        },
        {
            trigger: ".o-kanban-button-new",
            content: "click create",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=name] input",
            content: "complete name",
            run: "edit Test Lead 1",
        },
        {
            trigger: ".o_field_widget[name=expected_revenue] input",
            content: "complete expected revenue",
            run: "edit 999999997",
        },
        {
            trigger: "button.o_kanban_add",
            content: "create lead",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains('Test Lead 1')",
            content: "move to won stage",
            run: "drag_and_drop (.o_opportunity_kanban .o_kanban_group:eq(3))",
        },
        {
            trigger: ".o_reward_rainbow",
        },
        {
            // This step and the following simulates the fact that after drag and drop,
            // from the previous steps, a click event is triggered on the window element,
            // which closes the currently shown .o_kanban_quick_create.
            trigger: ".o_kanban_renderer",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_quick_create))",
        },
        {
            trigger: ".o-kanban-button-new",
            content: "create second lead",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=name] input",
            content: "complete name",
            run: "edit Test Lead 2",
        },
        {
            trigger: ".o_field_widget[name=expected_revenue] input",
            content: "complete expected revenue",
            run: "edit 999999998",
        },
        {
            trigger: "button.o_kanban_add",
            content: "create lead",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:contains('Test Lead 2')",
        },
        {
            // move first test back to new stage to be able to test rainbowman a second time
            trigger: ".o_kanban_record:contains('Test Lead 1')",
            content: "move back to new stage",
            run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(0) ",
        },
        {
            trigger: ".o_kanban_record:contains('Test Lead 2')",
            content: "click on second lead",
            run: "click",
        },
        {
            trigger: ".o_statusbar_status button[data-value='4']",
            content: "move lead to won stage",
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".o_reward_rainbow",
        },
        {
            trigger: ".o_statusbar_status button[data-value='1']",
            content: "move lead to previous stage & rainbowman appears",
            run: "click",
        },
        {
            trigger: "button[name=action_set_won_rainbowman]",
            content: "click button mark won",
            run: "click",
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".o_reward_rainbow",
        },
        {
            trigger: ".o_menu_brand",
            content: "last rainbowman appears",
        },
    ],
});
