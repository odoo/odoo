import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('project_create_sol_tour', {
    url: "/odoo",
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
        content: 'Select Project main menu.',
        run: "click",
    }, {
        trigger: ".o_kanban_record:contains(Test History Project):first",
        content: "Open the project dropdown of project name 'Test History Project'.",
        run: "hover && click .o_kanban_record:contains(Test History Project):first .o_dropdown_kanban .dropdown-toggle",
    }, {
        trigger: ".o_kanban_card_manage_settings a:contains('Settings')",
        content: 'Start editing the project.',
        run: "click",
    }, {
        trigger: ".o_field_widget[name='partner_id'] input",
        content: "Add the customer for this project",
        run: "click",
    }, {
        isActive: ["auto"],
        trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
        content: "Select the customer in the autocomplete dropdown",
        run: "click",
    },
    {
        trigger: 'div.o_notebook_headers',
    },
    {
        trigger: 'a.nav-link[name="settings"]',
        content: 'Click on Settings tab to configure this project.',
        run: "click",
    }, {
        id: "project_sale_timesheet_start",
        trigger: "div[name='sale_line_id'] input",
        content: 'Add the Sales Order Item',
        run: "fill New Sale order line",
    }, {
        trigger: ".o_field_widget[name=sale_line_id] .o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create a",
        content: "Create an Sales Order Item in the autocomplete dropdown.",
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        trigger: ".o_form_button_save:enabled",
        content: "Save project",
        run: "click",
    },
    // Those steps are currently needed in order to prevent the following issue:
    // "Form views in edition mode are automatically saved when the page is closed, which leads to stray network requests and inconsistencies."
    ...stepUtils.toggleHomeMenu(),
    ...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
]});

