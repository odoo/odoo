/** @odoo-module **/
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('industry_fsm_report_worksheet_test_tour', {
    url: "/odoo",
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        content: 'Open FSM app.',
        trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
        run: "click",
    },
    {
        content: 'Open setting dropdown',
        trigger: 'button[data-menu-xmlid="industry_fsm.fsm_menu_settings"]',
        run: "click",
    },
    {
        content: 'Open worksheet template view',
        trigger: 'a[data-menu-xmlid="industry_fsm_report.fsm_settings_worksheets"]',
        run: "click",
    },
    {
        content: 'Create a new worksheet',
        trigger: 'button.o_list_button_add',
        run: "click",
    },
    {
        content: 'Set name for the new worksheet',
        trigger: 'div[name="name"] input[type="text"]',
        run: "edit A very original worksheet",
    },
    {
        content: 'Save changes',
        trigger: 'button.o_list_button_save',
        run: "click",
    },
    {
        content: 'Open worksheet template form',
        trigger: "button:contains(Design Template):last:enabled",
        run: "click",
    },
    {
        content: 'Close studio',
        trigger: 'div.o_web_studio_leave a:contains("Close")',
        run: "click",
    },
    {
        trigger: 'button:contains("Design Template")',
    },
    {
        content: 'Check view',
        trigger: 'span:contains("A very original worksheet")',
    },
]});
