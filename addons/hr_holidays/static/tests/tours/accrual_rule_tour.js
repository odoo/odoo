import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_holidays_accrual_rule_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_app[data-menu-xmlid='hr_holidays.menu_hr_holidays_root']",
            run: "click",
        },
        {
            trigger: ".o-dropdown[data-menu-xmlid='hr_holidays.menu_hr_holidays_configuration']",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_holidays.hr_leave_accrual_rule_menu']",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            run: "edit UI Monthly Accrual",
        },
        {
            trigger: ".o_field_widget[name='work_entry_type_id'] input",
            run: "edit Accrual Tour Time Off",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Accrual Tour Time Off')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='employee_domain'] button:contains('New Rule')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='employee_domain'] .o_model_field_selector",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover input",
            run: "edit First Contract Date",
        },
        {
            trigger:
                ".o_model_field_selector_popover [data-name='first_contract_date'] .o_model_field_selector_popover_item_name",
            run: "click",
        },
        {
            trigger:
                ".o_field_widget[name='employee_domain'] select:has(option:contains('Relative range'))",
            run: "selectByLabel Relative range",
        },
        {
            trigger: ".o_field_widget[name='employee_domain'] input[type='number']",
            run: "edit -2",
        },
        {
            trigger: ".o_field_widget[name='employee_domain'] select:has(option:contains('year'))",
            run: "selectByLabel year",
        },
        {
            trigger:
                ".o_field_widget[name='employee_domain'] .o_domain_show_selection_button:contains('1 record(s)')",
            run() {
                if (odoo.debug || document.querySelector(".o_domain_selector_debug_container")) {
                    throw new Error("Relative ranges must be available without debug mode");
                }
            },
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".o_form_status_indicator:not(.o_form_status_indicator_dirty)",
        },
        {
            trigger: "button[name='action_run']",
            run: "click",
        },
        {
            trigger: ".o_list_view .o_data_row:contains('Recently Hired Accrual Employee')",
        },
    ],
});
