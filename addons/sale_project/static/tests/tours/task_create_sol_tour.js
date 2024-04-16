import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("task_create_sol_tour", {
    test: true,
    url: "/web",
    steps: () => [
    stepUtils.showAppsMenuItem(), {
        trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
        content: 'Select Project main menu.',
    }, {
        trigger: ".o_kanban_record:contains('Test History Project'):first",
        content: "Open the project dropdown of project name 'Test History Project'.",
    }, {
        trigger: "div strong.o_kanban_record_title:contains('Test History Task')",
        content: "Open the task name 'Test History Project' from kanban view.",
    },  {
        trigger: ".o_field_widget[name='partner_id'] input",
        content: "Add the customer for this task to select an SO and SOL."
    }, {
        trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
        content: "Select the customer in the autocomplete dropdown",
        auto: true,
    }, {
        trigger: "div[name='sale_line_id'] input",
        content: 'Add the Sales Order Item',
        run: "fill New Sale order line",
    }, {
        trigger: ".o_field_widget[name=sale_line_id] .o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a",
        content: "Create an Sales Order Item in the autocomplete dropdown.",
    }, {
        trigger: "div[name='product_id'] input",
        content: "Create an product in the autocomplete dropdown.",
    }, {
        trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
        content: "Select the product in the autocomplete dropdown",
    }, {
        trigger: ".o_form_button_save",
        content: "Save Sales Order Item",
        in_modal: true,
    }, {
        trigger: ".o_form_button_save",
        content: "Save task",
    }, {
        trigger: ".o_field_widget[name='sale_line_id'] input",
        content: "Check if the Sales Order Item is saved correctly.",
        run: function ({ anchor }) {
            if (!anchor.value) {
                console.error("Sales Order Item is not saved correctly.");
            }
        },
    },
    // Those steps are currently needed in order to prevent the following issue:
    // "Form views in edition mode are automatically saved when the page is closed, which leads to stray network requests and inconsistencies."
    stepUtils.toggleHomeMenu(),
    ...stepUtils.goToAppSteps("project.menu_main_pm", 'Go to the Project app.'),
]});
