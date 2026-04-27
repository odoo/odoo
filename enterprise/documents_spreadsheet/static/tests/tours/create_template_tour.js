/** @odoo-module */

import { waitFor } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const SHEET_NAME = "Res Partner Test Spreadsheet";
const TEMPLATE_NAME = `${SHEET_NAME} - Template`;

registry.category("web_tour.tours").add("documents_spreadsheet_create_template_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("documents.menu_root", "Open Document app"),
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
            trigger: `div[title="${SHEET_NAME}"]`,
            content: "Select Test Sheet",
            run: "click",
        },
        {
            trigger: 'img[alt="Spreadsheet Preview"]',
            content: "Open the sheet",
            run: "click",
        },
        {
            trigger: '.o-topbar-menu[data-id="file"]',
            content: "Open the file menu",
            run: "click",
        },
        {
            trigger: '.o-menu-item[data-name="save_as_template"]',
            content: "Save as template",
            run: "click",
        },
        {
            trigger: '.modal button[name="save_template"]',
            content: "Save as template",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".btn.btn-primary.dropdown-toggle[data-hotkey='c']",
            content: "new dropdown",
            run: "click",
        },
        {
            trigger: ".btn.btn-link.o_documents_kanban_spreadsheet",
            content: "Spreadsheet",
            run: "click",
        },
        {
            trigger: `.o-spreadsheet-grid-item-name:contains(${TEMPLATE_NAME})`,
            content: "verify that the template name is displayed",
        },
        {
            trigger: "button.btn-close",
            content: "close the popup",
            run: "click",
        },
        {
            trigger: 'button[data-menu-xmlid="documents.Config"]',
            content: "Open Configuration menu",
            run: "click",
        },
        {
            trigger:
                '.dropdown-item[data-menu-xmlid="documents_spreadsheet.menu_technical_spreadsheet_template"]',
            content: "Open Templates menu",
            run: "click",
        },
        {
            trigger: ".o_menu_brand",
            content: "Wait search filter to be displayed",
            run: async () => {
                await waitFor(".o_searchview .o_facet_remove", { timeout: 1500 });
            },
        },
        {
            trigger: ".o_searchview .o_facet_remove",
            content: 'Remove "My templates" filter',
            run: "click",
        },
        {
            trigger: "input.o_searchview_input",
            content: "Search the template",
            run: `edit ${TEMPLATE_NAME}`,
        },
        {
            trigger: ".o_menu_item.focus",
            content: "Validate search",
            run: "click",
        },
        {
            trigger: `tr.o_data_row:first-child td[data-tooltip="${TEMPLATE_NAME}"]`,
            content: "Wait search to complete",
        },
        {
            trigger: "button.o-new-spreadsheet",
            content: "Create spreadsheet from template",
            run: "click",
        },
        {
            trigger: ".o_menu_brand",
            content: "Wait",
            run: async () => {
                await waitFor(".o-spreadsheet", { timeout: 1500 });
            },
        },
        {
            trigger: ".o-spreadsheet",
            content: "Redirected to spreadsheet",
            run: "click",
        },
    ],
});
