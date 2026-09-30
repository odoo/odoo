import { registry } from "@web/core/registry";

function selectCompany(companyName) {
    return [
        {
            content: `Select ${companyName}`,
            trigger: ".o_field_widget[name='company_id'] input",
            run: `edit ${companyName}`,
        },
        {
            trigger: `.o-autocomplete--dropdown-menu .dropdown-item:contains(${companyName})`,
            run: "click",
        },
        {
            content: "The company modification dialog opens",
            trigger: ".modal .modal-title:contains(Company Modification)",
        },
    ];
}

registry.category("web_tour.tours").add("hr_employee_company_transfer_tour", {
    steps: () => [
        {
            content: "Open the work information tab",
            trigger: "button[name='work_information']",
            run: "click",
        },
        ...selectCompany("Transfer Company B"),
        {
            content: "Cancel the transfer",
            trigger: ".modal-footer button:contains(Cancel)",
            run: "click",
        },
        {
            content: "The company is unchanged",
            trigger:
                "body:not(:has(.modal)) .o_field_widget[name='company_id'] input:value(Transfer Company A)",
        },
        ...selectCompany("Transfer Company B"),
        {
            content: "Duplicate and archive the employee",
            trigger: ".modal-footer button:contains(Duplicate & Archive)",
            run: "click",
        },
        {
            content: "The new employee is opened in the new company",
            trigger:
                "body:not(:has(.modal)) .o_field_widget[name='company_id'] input:value(Transfer Company B)",
        },
    ],
});
