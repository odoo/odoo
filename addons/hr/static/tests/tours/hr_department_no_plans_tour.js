import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_department_no_plans_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Open the employee's page",
            trigger: ".o_kanban_record:contains('Employee Without Plans')",
            run: "click",
        },
        {
            content: "Open the employee's department",
            trigger: ".o_field_widget[name='department_id'] .o_form_uri",
            run: "click",
        },
        {
            content: "Department form is displayed",
            trigger: ".o_form_view .o_field_widget[name='name']:contains('Department Without Plans')",
        },
        {
            content: "Plans smart button shows 0 plans",
            trigger: "button[name='action_plan_from_department'] .o_stat_value",
            run: function () {
                const count = this.anchor.innerText.trim();
                if (count !== "0") {
                    throw new Error(`Plans smart button should show 0 plans, got "${count}"`);
                }
            },
        },
        {
            content: "Click on the Plans smart button",
            trigger: "button[name='action_plan_from_department']",
            run: "click",
        },
        {
            content: "Plans view is displayed without any plan",
            trigger: ".o_breadcrumb .active:contains('Employee Plans')",
            run: () => {
                if (document.querySelector(".o_error_dialog")) {
                    throw new Error("An error occurred when opening the department plans");
                }
                if (document.querySelector(".o_data_row, .o_kanban_record:not(.o_kanban_ghost)")) {
                    throw new Error("The department plans view should not contain any plan");
                }
            },
        },
    ],
});
