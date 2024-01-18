import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('project_create_sol_tour', {
    test: true,
    url: "/web",
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
        content: 'Select Project main menu.',
    }, {
        trigger: ".o_kanban_record:contains('Test History Project'):first .o_dropdown_kanban .dropdown-toggle",
        content: "Open the project dropdown of project name 'Test History Project'.",
    }, {
        trigger: ".o_kanban_card_manage_settings a:contains('Settings')",
        content: 'Start editing the project.',
    }, {
        trigger: ".o_field_widget[name='partner_id'] input",
        content: "Add the customer for this project"
    }, {
        trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
        content: "Select the customer in the autocomplete dropdown",
        auto: true,
    }, {
        trigger: 'a.nav-link[name="settings"]',
        extra_trigger: 'div.o_notebook_headers',
        content: 'Click on Settings tab to configure this project.',
    }, {
        id: "project_sale_timesheet_start",
        trigger: "div[name='sale_line_id'] input",
        content: 'Add the Sales Order Item',
        run: "fill New Sale order line",
    }, {
        trigger: ".o_field_widget[name=sale_line_id] .o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create a",
        content: "Create an Sales Order Item in the autocomplete dropdown.",
    }, {
        trigger: ".o_form_button_save",
        content: "Save project",
    },
    // Those steps are currently needed in order to prevent the following issue:
    // "Form views in edition mode are automatically saved when the page is closed, which leads to stray network requests and inconsistencies."
    stepUtils.toggleHomeMenu(),
    ...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
]});
