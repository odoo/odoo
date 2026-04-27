/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("spreadsheet_save_multipage", {
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
            content: "Open the test folder",
            run: "dblclick",
        },
        {
            trigger: ".o_searchview_facet .o_facet_remove",
            content: "remove filter",
            run: "click",
        },
        {
            trigger: ".o_cp_buttons:contains('New') .dropdown-toggle",
            content: "Open dropdown",
            run: "click",
        },
        {
            trigger: ".o_documents_kanban_spreadsheet",
            content: "Open template dialog",
            run: "click",
        },
        {
            trigger: ".o-spreadsheet-create",
            content: "Create new spreadsheet",
            run: "click",
        },
        {
            trigger: ".o-add-sheet",
            content: "Add a sheet",
            run: "click",
        },
        {
            trigger: ".o-sheet-list .o-ripple-container:nth-child(2)",
            content: "Check that there are now two sheets",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer .o_kanban_record .o_kanban_stack",
            content: "Check is rendered as multipage",
        },
        {
            trigger: ".o_kanban_stack .o_documents_image",
            content: "Reopen the sheet",
            run: "click",
        },
        {
            trigger: ".o-sheet .o-sheet-icon",
            content: "Open sheet dropdown",
            run() {
                const sheets = document.querySelectorAll("div.o-sheet").length;
                if (sheets !== 2) {
                    console.error(`There should be 2 sheets, and ${sheets} has been found`);
                }
                document.querySelector("div.o-sheet[title=Sheet1] span.o-sheet-icon").click();
            },
        },
        {
            trigger: '.o-popover .o-menu-item[title="Delete"]',
            content: "Delete sheet",
            run: "click",
        },
        {
            trigger: ".modal-dialog footer button.btn-primary",
            content: "Confirm delete sheet",
            run: "click",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".o_kanban_renderer .o_kanban_record:first",
            content: "Check is rendered as single page",
            run: () => {
                const card = document.querySelectorAll(
                    ".o_kanban_renderer .o_kanban_record:first-child > div.o_kanban_stack"
                );
                if (card.length > 1) {
                    console.error("The card should not be rendered as multipage.");
                }
            },
        },
    ],
});
