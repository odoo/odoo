/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { stepUtils } from '@web_tour/tour_service/tour_utils';

    registry.category("web_tour.tours").add('crm_rainbowman', {
        test: true,
        url: "/web",
        steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_app[data-menu-xmlid='crm.crm_menu_root']",
            content: "open crm app",
        }, {
            trigger: ".o-kanban-button-new",
            content: "click create",
        }, {
            trigger: ".o_field_widget[name=name] input",
            content: "complete name",
            run: "text Test Lead 1",
        }, {
            trigger: ".o_field_widget[name=expected_revenue] input",
            content: "complete expected revenue",
            run: "text 999999997",
        }, {
            trigger: "button.o_kanban_add",
            content: "create lead",
        }, {
            trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Lead 1')",
            content: "move to won stage",
            run: "drag_and_drop_native .o_opportunity_kanban .o_kanban_group:eq(3) "
        }, {
            trigger: ".o_reward_rainbow",
            extra_trigger: ".o_reward_rainbow",
            run: function () {} // check rainbowman is properly displayed
        }, {
            // This step and the following simulates the fact that after drag and drop,
            // from the previous steps, a click event is triggered on the window element,
            // which closes the currently shown .o_kanban_quick_create.
            trigger: ".o_kanban_renderer",
        }, {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_quick_create))",
            run() {},
        }, {
            trigger: ".o-kanban-button-new",
            content: "create second lead",
        }, {
            trigger: ".o_field_widget[name=name] input",
            content: "complete name",
            run: "text Test Lead 2",
        }, {
            trigger: ".o_field_widget[name=expected_revenue] input",
            content: "complete expected revenue",
            run: "text 999999998",
        }, {
            trigger: "button.o_kanban_add",
            content: "create lead",
        }, {
            trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Lead 2')",
            run: function () {} // wait for the record to be properly created
        }, {
            // move first test back to new stage to be able to test rainbowman a second time
            trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Lead 1')",
            content: "move back to new stage",
            run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(0) "
        }, {
            trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Lead 2')",
            content: "click on second lead",
        }, {
            trigger: ".o_statusbar_status button[data-value='4']",
            content: "move lead to won stage",
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".o_statusbar_status button[data-value='1']",
            extra_trigger: ".o_reward_rainbow",
            content: "move lead to previous stage & rainbowman appears",
        }, {
            trigger: "button[name=action_set_won_rainbowman]",
            content: "click button mark won",
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".o_menu_brand",
            extra_trigger: ".o_reward_rainbow",
            content: "last rainbowman appears",
            isCheck: true,
        }
    ]});
