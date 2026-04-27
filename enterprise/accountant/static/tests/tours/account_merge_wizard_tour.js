/** @odoo-module */

import { accountTourSteps } from "@account/js/tours/account";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("account_merge_wizard_tour", {
    url: "/odoo",
    steps: () => [
        ...accountTourSteps.goToAccountMenu("Go to Accounting"),
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
        {
            content: "Select accounts",
            trigger: "thead .o_list_record_selector",
            run: "click",
        },
        {
            content: "Check that exactly 4 accounts are present and selected",
            trigger: ".o_list_selection_box:contains(4):contains(selected)",
        },
        {
            content: "Open Actions menu",
            trigger: ".o_cp_action_menus .dropdown-toggle",
            run: "click",
        },
        {
            content: "Open Merge accounts wizard",
            trigger: 'span:contains("Merge accounts")',
            run: "click",
        },
        {
            content: "Group by name",
            trigger: 'div[name="is_group_by_name"] input',
            run: "click",
        },
        {
            content: "Wait for content to be updated",
            trigger: 'td:contains("Current Assets (Current Assets)")',
        },
        {
            content: "Merge accounts",
            trigger: 'button:not([disabled]) span:contains("Merge")',
            run: "click",
        },
        {
            content: "Check that there are now exactly 2 accounts",
            trigger: ".o_pager_limit:contains(2)",
        },
    ],
});
