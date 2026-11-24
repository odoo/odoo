import { registry } from "@web/core/registry";

function selectCompany(companyName) {
    return [
        {
            content: "Open the work information tab",
            trigger: "button[name='work_information']",
            run: "click",
        },
        {
            content: `Select ${companyName}`,
            trigger: ".o_field_widget[name='company_id'] input",
            run: `edit ${companyName}`,
        },
        {
            trigger: `.o-autocomplete--dropdown-menu .dropdown-item:contains(${companyName})`,
            run: "click",
        },
    ];
}

registry.category("web_tour.tours").add("hr_employee_company_change_tour", {
    steps: () => [
        ...selectCompany("Company B"),
        {
            content: "The company is changed in the form, without dialog",
            trigger:
                "body:not(:has(.modal)) .o_field_widget[name='company_id'] input:value(Company B)",
        },
        {
            content: "Save the employee",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
    ],
});

registry.category("web_tour.tours").add("hr_employee_company_move_tour", {
    steps: () => [
        ...selectCompany("Company B"),
        {
            content: "The version is covered by payslips: the move dialog opens",
            trigger: ".modal .modal-title:contains(Move employee to a new company)",
        },
        {
            content: "Discard the move",
            trigger: ".modal-footer button:contains(Discard)",
            run: "click",
        },
        {
            content: "The company is unchanged",
            trigger:
                "body:not(:has(.modal)) .o_field_widget[name='company_id'] input:value(Company A)",
        },
        ...selectCompany("Company B").slice(1),
        {
            content: "The effective date defaults to the day after the payslips",
            trigger: ".modal .o_field_widget[name='date_version'] input:value(11/01/2026)",
        },
        {
            content: "Confirm the move",
            trigger: ".modal-footer button:contains(Confirm)",
            run: "click",
        },
        {
            content: "The employee is moved to Company B from the effective date",
            trigger:
                "body:not(:has(.modal)) .o_field_widget[name='company_id'] input:value(Company B)",
        },
    ],
});
