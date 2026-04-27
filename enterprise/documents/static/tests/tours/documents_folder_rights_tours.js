/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("test_document_folder_rights_for_multi_company", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
            run: "click",
        },
        {
            trigger: 'li[title="All"]',
            content: "Verify that the All folder is opened by default",
        },
        {
            trigger: 'li[title="Company"] header button',
            run: "click",
        },
        {
            trigger: "span.o_search_panel_label_title:contains('Folder1')",
            run: "click",
        },
        {
            trigger: ".o_switch_company_menu > .dropdown-toggle",
            run: "click",
        },
        {
            trigger: "div.btn.btn-link[aria-label='Switch to Company_A']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_switch_company_menu:contains('Company_A')",
        },
        {
            content: "Check that the workspace is not visible",
            trigger: ".o_search_panel_label_title:not(:contains('Folder1'))",
        },
    ],
});
