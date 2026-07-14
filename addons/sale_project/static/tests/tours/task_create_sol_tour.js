import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("task_create_sol_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Select Project main menu.",
            trigger: ".o_app[data-menu-xmlid='project.menu_main_pm']",
            run: "click",
        },
        {
            content: "Open the project dropdown of project name 'Test History Project'.",
            trigger: ".o_kanban_record:contains(Test History Project):first",
            run: "click",
        },
        {
            content: "Open the task name 'Test History Project' from kanban view.",
            trigger: ".o_kanban_record:contains(Test History Task)",
            run: "click",
        },
        {
            content: "Add the customer for this task to select an SO and SOL.",
            trigger: ".o_field_widget[name='partner_id'] input",
            run: "click",
        },
        {
            content: "Select the customer in the autocomplete dropdown",
            trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
            run: "click",
        },
        {
            content: "Add the Sales Order Item",
            trigger: "div[name='sale_line_id'] input",
            run: "fill New Sale order line",
        },
        {
            content: "Create an Sales Order Item in the autocomplete dropdown.",
            trigger:
                ".o_field_widget[name=sale_line_id] .o-autocomplete--dropdown-menu .o_m2o_dropdown_option_create_edit a",
            run: "click",
        },
        {
            content: "Create an product in the autocomplete dropdown.",
            trigger: "div[name='product_id'] input",
            run: "click",
        },
        {
            content: "Select the product in the autocomplete dropdown",
            trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
            run: "click",
        },
        {
            content: "Save Sales Order Item",
            trigger: ".modal .o_form_button_save",
            run: "click",
        },
        {
            content: "wait the modal is closed before save the form",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Save task",
            trigger: ".o_form_button_save:enabled",
            run: "click",
        },
        {
            content: "Check if the Sales Order Item is saved correctly.",
            trigger: ".o_field_widget[name='sale_line_id'] input",
            run() {
                if (!this.anchor.value) {
                    console.error("Sales Order Item is not saved correctly.");
                }
            },
        },
        // Those steps are currently needed in order to prevent the following issue:
        // "Form views in edition mode are automatically saved when the page is closed, which leads to stray network requests and inconsistencies."
        ...stepUtils.toggleHomeMenu(),
        ...stepUtils.goToAppSteps("project.menu_main_pm", "Go to the Project app."),
    ],
});
