odoo.define('crm.tour_crm_rainbowman', function (require) {
    "use strict";

    var tour = require('web_tour.tour');

    tour.register('crm_rainbowman', {
        test: true,
        url: "/web",
    }, [
        tour.stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_app[data-menu-xmlid='crm.crm_menu_root']",
            content: "open crm app",
        }, {
            trigger: ".o-kanban-button-new",
            content: "click create",
        }, {
            trigger: "input[name=name]",
            content: "complete name",
            run: "text Test Lead 1",
        }, {
            trigger: "div[name=planned_revenue] > input",
            content: "complete planned revenue",
            run: "text 999999997",
        }, {
            trigger: "button.o_kanban_add",
            content: "create lead",
        }, {
            trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Lead 1')",
            content: "move to won stage",
            run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(3) "
        }, {
            trigger: ".o-kanban-button-new",
            extra_trigger: ".o_reward_rainbow",
            content: "click create",
        }, {
            trigger: "input[name=name]",
            content: "complete name",
            run: "text Test Lead 2",
        }, {
            trigger: "div[name=planned_revenue] > input",
            content: "complete planned revenue",
            run: "text 999999998",
        }, {
            trigger: "button.o_kanban_add",
            content: "create lead",
        }, {
            trigger: ".o_kanban_record .o_kanban_record_title:contains('Test Lead 2')",
            content: "click on lead",
        }, {
            trigger: ".o_statusbar_status button[data-value='4']",
            content: "move lead to won stage",
        }, {
            trigger: ".o_statusbar_status button[data-value='1']",
            extra_trigger: ".o_reward_rainbow",
            content: "move lead to previous stage & rainbowman appears",
        }, {
            trigger: "button[name=action_set_won_rainbowman]",
            content: "click button mark won",
        }, {
            trigger: ".o_menu_brand",
            extra_trigger: ".o_reward_rainbow",
            content: "last rainbowman appears",
        }
    ]);
});
