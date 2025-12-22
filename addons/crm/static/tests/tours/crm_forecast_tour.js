/** @odoo-module */
import { queryAll } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
const today = luxon.DateTime.now();

registry.category("web_tour.tours").add('crm_forecast', {
    url: "/odoo",
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        trigger: ".o_app[data-menu-xmlid='crm.crm_menu_root']",
        content: "open crm app",
        run: "click",
    }, {
        trigger: '.dropdown-toggle[data-menu-xmlid="crm.crm_menu_report"]',
        content: 'Open Reporting menu',
        run: 'click',
    }, {
        trigger: '.dropdown-item[data-menu-xmlid="crm.crm_menu_forecast"]',
        content: 'Open Forecast menu',
        run: 'click',
    }, {
        trigger: '.o_column_quick_create:contains(Add next month)',
        content: 'Wait page loading',
    }, {
        trigger: ".o-kanban-button-new",
        content: "click create",
        run: 'click',
    }, {
        trigger: ".o_field_widget[name=name] input",
        content: "complete name",
        run: "edit Test Opportunity 1",
    }, {
        trigger: ".o_field_widget[name=expected_revenue] input",
        content: "complete expected revenue",
        run: "edit 999999",
    }, {
        trigger: "button.o_kanban_edit",
        content: "edit lead",
        run: "click",
    }, {
        trigger: "div[name=date_deadline] input",
        content: "complete expected closing",
        run: `edit ${today.toFormat("MM/dd/yyyy")}`,
    }, {
        trigger: "div[name=date_deadline] input",
        content: "click to make the datepicker disappear",
        run: "click"
    }, {
        trigger: '.o_back_button',
        content: 'navigate back to the kanban view',
        tooltipPosition: "bottom",
        run: "click"
    }, {
        trigger: ".o_kanban_record:contains('Test Opportunity 1')",
        content: "move to the next month",
        async run(helpers) {
            const undefined_groups = queryAll('.o_column_title:contains("None")').length;
            await helpers.drag_and_drop(`.o_opportunity_kanban .o_kanban_group:eq(${1 + undefined_groups})`);
        },
    }, {
        trigger: ".o_kanban_record:contains('Test Opportunity 1')",
        content: "edit lead",
        run: "click"
    }, {
        trigger: ".o_field_widget[name=date_deadline] input",
        content: "complete expected closing",
        run: `edit ${today.plus({ months: 5 }).startOf("month").minus({ days: 1 }).toFormat("MM/dd/yyyy")} && press Escape`,
    }, {
        trigger: ".o_field_widget[name=probability] input",
        content: "max out probability",
        run: "edit 100",
    }, {
        trigger: '.o_back_button',
        content: 'navigate back to the kanban view',
        tooltipPosition: "bottom",
        run: "click"
    }, {
        trigger: '.o_kanban_add_column',
        content: "add next month",
        run: "click"
    }, {
        trigger: ".o_kanban_record:contains('Test Opportunity 1'):contains('Won')",
        content: "assert that the opportunity has the Won banner",
    }
]});
