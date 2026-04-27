import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("ticket_create_sol_tour", {
    url: "/odoo",
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='helpdesk.menu_helpdesk_root']",
        content: 'Select helpdesk main menu.',
        run: "click",
    }, {
        trigger: ".o_kanban_record:has(span:contains('Test Team'))",
        content: "Open the team dropdown of team name 'Test Team'.",
        run: "click",
    }, {
        trigger: ".o_kanban_record:contains('Test Ticket')",
        content: "Open the ticket name 'Test Ticket' from kanban view.",
        run: "click",
    }, {
        trigger: "div[name='sale_line_id'] input",
        content: 'Add the Sales Order Item',
        run: "fill New Sale order line",
    }, {
        trigger: ".o_field_widget[name=sale_line_id] .o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a",
        content: "Create an Sales Order Item in the autocomplete dropdown.",
        run: "click",
    }, {
        trigger: "div[name='product_id'] input",
        content: "Create an product in the autocomplete dropdown.",
        run: "click",
    }, {
        trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
        content: "Select the product in the autocomplete dropdown",
        run: "click",
    }, {
        trigger: ".modal .o_form_button_save",
        content: "Save task",
        run: "click",
    },
    // Those steps are currently needed in order to prevent the following issue:
    // "Form views in edition mode are automatically saved when the page is closed, which leads to stray network requests and inconsistencies."
    ...stepUtils.toggleHomeMenu(),
    ...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
]});
