/** @odoo-module**/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("spreadsheet_clone_xlsx", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
            content: "Open document app",
            run: "click",
        },
        {
            trigger: '.o_documents_title:contains("Folders")',
            content: "check if the folders are loaded",
        },
        {
            trigger: ".o_searchview_input",
            content: "click on search",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            content: "fill in searchbar",
            run: `edit Test folder`,
        },
        {
            content: "find the right folder",
            trigger: ".o_searchview_autocomplete li:contains(Test folder)",
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("Test folder")',
            content: "Open Test folder workspace",
            run: "dblclick",
        },
        {
            trigger: ".o_searchview_facet .o_facet_remove",
            content: "remove filter",
            run: "click",
        },
        {
            trigger: 'li[title="Company"] header button',
            content: "Unfold Company folder",
            run: "click",
        },
        {
            trigger: '.list-group-item.active:contains("Test folder")',
            content: "Make sure we start with one card",
            run: "click",
        },
        {
            trigger: ".o_document_xlsx",
            content: "Open xlsx card",
            run: "click",
        },
        {
            trigger: "input#willArchive",
            content: "Uncheck sending to trash",
            run: "click",
        },
        {
            trigger: ".modal-dialog footer button.btn-primary",
            content: "Open with Odoo Spreadsheet",
            run: "click",
        },
        {
            trigger: ".o-spreadsheet-topbar",
            content: "Check that we are now in Spreadsheet",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer .o_kanban_record .o_document_spreadsheet",
            content: "Check a spreadsheet document was created",
        },
        {
            trigger: ".o_document_xlsx",
            content: "Re-open the xlsx card",
            run: "click",
        },
        {
            trigger: ".modal-dialog footer button.btn-primary",
            content: "Open with Odoo Spreadsheet without unchecking the box",
            run: "click",
        },
        {
            trigger: ".o-spreadsheet-topbar",
            content: "Check that we are now in Spreadsheet",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer:not(:has(.o_kanban_record .o_document_xlsx))",
            content: "Check that XLSX is no longer visible",
            run: function () {
                const elements = document.querySelectorAll(".o_document_xlsx").length;
                if (elements) {
                    console.error(`${elements} elements found.`);
                }
            },
        },
    ],
});
