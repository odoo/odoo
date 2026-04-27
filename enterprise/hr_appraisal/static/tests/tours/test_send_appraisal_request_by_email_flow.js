/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_send_appraisal_request_by_email_flow", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_app[data-menu-xmlid='hr_appraisal.menu_hr_appraisal_root']",
            content: "Open appraisal app",
            run: "click",
        },
        {
            trigger: ".o_kanban_record",
            content: "Go to the one employee appraisal",
            run: "click",
        },
        {
            trigger: "button[name='action_send_appraisal_request']",
            content: "Send the appraisal request by email",
            run: "click",
        },
        {
            trigger: ".modal-dialog .o_form_view",
            content: "Check that the Appraisal request form modal is open",
        },
    ],
});
