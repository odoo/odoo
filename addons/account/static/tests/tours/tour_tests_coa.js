/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('chart_of_accounts_branch_access_tour', {
    steps: () => [
        {
            trigger: '.o_app:contains("Accounting")',
            content: "Open Accounting App",
            run: 'click',
        },
        {
            content: "Go to Configuration",
            trigger: 'span:contains("Configuration")',
            run: "click",
        },
        {
            content: "Go to Chart of Accounts",
            trigger: 'a:contains("Chart of Accounts")',
            run: "click",
        },
        {
            trigger: '.o_breadcrumb .text-truncate:contains("Chart of Accounts")',
        },
    ]
});
