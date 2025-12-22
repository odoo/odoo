import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("check_public_employee_link_redirect", {
    // starts at /odoo/employee/<employee_id>
    steps: () => {
        /* ignoring inactive modals since the modal may appear multiple times
          thus hiding the inactive ones and playwright doesn't like doing
          actions on hidden elements */
        const msgSelector = '.o_dialog:not(.o_inactive_modal) .modal-content .modal-body div[role="alert"] p';
        const msg = `You are not allowed to access "Employee" (hr.employee) records.
We can redirect you to the public employee list.`;
        return [
            {
                trigger: msgSelector,
                content: "See if redirect warning popup appears for current user",
                timeout: 3000,
                run: () => {
                    const errorTxt = document.querySelector(msgSelector).innerText;
                    if (errorTxt !== msg) {
                        throw new Error("Could not find correct warning message when visiting private employee without required permissions")
                    }
                }
            },
        ]
    },
});

