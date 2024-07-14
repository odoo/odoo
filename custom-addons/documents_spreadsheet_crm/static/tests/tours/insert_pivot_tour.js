/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add(
    "insert_crm_pivot_in_spreadsheet",
    {
        test: true,
        url: "/web",
        steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
            content: "Open CRM app",
            run: "click",
        },
        {
            trigger: 'button[data-tooltip="Pivot"]',
            content: "Open Pivot view",
            run: "click",
        },
        {
            trigger: ".o_pivot_add_spreadsheet",
            content: "Insert pivot in the spreadsheet",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn-primary",
            content: "Insert in a new spreadsheet",
            run: "click",
        },
        {
            trigger: ".o-spreadsheet",
            content: "Redirected to spreadsheet",
            isCheck: true,
        },
    ]
});
