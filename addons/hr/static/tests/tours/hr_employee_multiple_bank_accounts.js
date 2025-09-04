import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_employee_multiple_bank_accounts_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Open an Employee Profile",
            trigger: ".o_kanban_record:contains('Johnny H.')",
            run: "click",
        },
        {
            content: "Open personal tab",
            trigger: ".nav-link:contains('Personal')",
            run: "click",
        },
        {
            content: "add bank 1",
            trigger: "input#bank_account_ids_2",
            run: "edit 1",
        },
        {
            content: "add bank 1",
            trigger: ".dropdown-item:contains('Create and edit')",
            run: "click",
        },
        {
            content: "save bank 1",
            trigger: ".o_form_button_save:contains('Save')",
            run: "click",
        },
        {
            content: "add bank 2",
            trigger: "input#bank_account_ids_2",
            run: "edit 2",
        },
        {
            content: "add bank 2",
            trigger: ".dropdown-item:contains('Create and edit')",
            run: "click",
        },
        {
            content: "save",
            trigger: ".o_form_button_save:contains('Save')",
            run: "click",
        },
        {
            content: "add bank 3",
            trigger: "input#bank_account_ids_1",
            run: "edit 3",
        },
        {
            content: "add bank 3",
            trigger: ".dropdown-item:contains('Create and edit')",
            run: "click",
        },
        {
            content: "save bank 3",
            trigger: ".o_form_button_save:contains('Save')",
            run: "click",
        },
        {
            content: "save employee form",
            trigger: ".fa-cloud-upload",
            run: "click",
        },
        {
            content: "wait for save completion",
            trigger: ".o_form_readonly, .o_form_saved",
        },
    ],
});
