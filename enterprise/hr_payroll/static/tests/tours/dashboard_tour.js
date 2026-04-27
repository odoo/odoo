/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("payroll_dashboard_ui_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open payroll app",
            trigger:
                ".o_app[data-menu-xmlid='hr_work_entry_contract_enterprise.menu_hr_payroll_root']",
            run: "click",
        },
        {
            content: "Create a new note",
            trigger: "button.o_hr_payroll_todo_create",
            run: "click",
        },
        {
            content: "Set a name",
            trigger: "li.o_hr_payroll_todo_tab input",
            run: "edit Dashboard Todo List && click body",
        },
        {
            trigger: "li.o_hr_payroll_todo_tab a.active:contains(Dashboard Todo List)",
        },
        {
            content: "Edit the note in dashboard view",
            trigger: "div.o_hr_payroll_todo_value",
            run: "click",
        },
        {
            content: "Write in the note",
            trigger: ".note-editable.odoo-editor-editable",
            run: "editor Todo List",
        },
    ],
});
