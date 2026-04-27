/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
const SHEET_NAME = "Res Partner Test Spreadsheet";

registry.category("web_tour.tours").add("spreadsheet_create_empty_sheet", {
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
            trigger: 'span[title="Fill Color"]',
            content: "Choose a color",
            run: "click",
        },
        {
            trigger: '.o-color-picker-line-item[data-color="#990000"]',
            content: "Choose a color",
            run: "click",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".o_document_spreadsheet:first",
            content: "Reopen the sheet",
            run: "click",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".o_action_manager:not(:has(.o_spreadsheet_action))",
            content: "Wait for the spreadsheet to be properly unloaded",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("spreadsheet_create_list_view", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            content: "Open apps menu",
            run: "click",
        },
        {
            trigger: "button.o_switch_view.o_list",
            content: "Switch to list view",
            run: "click",
        },
        {
            trigger: ".o_list_view",
        },
        {
            trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle",
            content: "Open the cog menu",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-toggle:contains(Spreadsheet)",
            run: "hover",
        },
        {
            trigger: ".o_insert_list_spreadsheet_menu",
            content: "Insert in spreadsheet",
            run: "click",
        },
        {
            trigger: `.o-spreadsheet-grid-item-name:contains(${SHEET_NAME})`,
            content: "verify that the existing spreadsheet names are displayed",
        },
        {
            trigger: ".modal-footer .btn-primary",
            content: "Confirm",
            run: "click",
        },
        {
            trigger: ".o-topbar-topleft .o-topbar-menu[data-id='data']",
            content: "Open Data menu",
            run: "click",
        },
        {
            trigger: ".o-menu-item[data-name='item_list_1']",
            content: "Open List Side Panel",
            run: "click",
        },
        {
            trigger: ".o-sp-breadcrumb",
            content: "Go back to Document App",
            run: "click",
        },
        {
            trigger: ".o_action_manager:not(:has(.o_spreadsheet_action))",
            content: "Wait for the spreadsheet to be properly unloaded",
            run() {},
        },
    ],
});
