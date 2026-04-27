/** @odoo-module */

import { registry } from "@web/core/registry";

let startingNumberOfSheetsInGroup = 0;

function assertNSheetsInGroup(number) {
    const actualNumber = document.querySelectorAll(".o_list_table tr.o_data_row").length;
    if (actualNumber !== number) {
        console.error(`Expected ${number} sheets in the dashbord group, got ${actualNumber}`);
    }
}

function focusFirstSheetInModal() {
    const sheetImg = document.querySelector(".o-spreadsheet-grid-image");
    sheetImg.dispatchEvent(new MouseEvent("focus"));
}

registry
    .category("web_tour.tours")
    .add("spreadsheet_dashboard_document_add_document_to_dashboard_group", {
        url: "/odoo",
        steps: () => [
            {
                trigger:
                    '.o_app[data-menu-xmlid="spreadsheet_dashboard.spreadsheet_dashboard_menu_root"]',
                content: "Open dashboard app",
                run: "click",
            },
            {
                trigger:
                    'button[data-menu-xmlid="spreadsheet_dashboard.spreadsheet_dashboard_menu_configuration"]',
                content: "Open configuration menu",
                run: "click",
            },
            {
                trigger:
                    'a[data-menu-xmlid="spreadsheet_dashboard.spreadsheet_dashboard_menu_configuration_dashboards"]',
                content: "Open dashboard configuration menu",
                run: "click",
            },
            {
                trigger: 'tbody tr td[name="name"]',
                content: "Open a dashboard group from list view",
                run: "click",
            },
            {
                trigger: 'button[name="action_add_document_spreadsheet_to_dashboard"]',
                run: () => {
                    startingNumberOfSheetsInGroup = document.querySelectorAll(
                        ".o_list_table tr.o_data_row"
                    ).length;
                },
            },
            {
                trigger: 'button[name="action_add_document_spreadsheet_to_dashboard"]',
                content: "Open add document to dashboard modal",
                run: "click",
            },
            {
                trigger: ".o-spreadsheet-grid-image",
                content: "Focus a spreadsheet",
                run: focusFirstSheetInModal,
            },
            {
                trigger: "button.btn-primary",
                content: "Click confirm button",
                run: "click",
            },
            {
                trigger: '.o-sp-breadcrumb',
                content: 'Go back to the dashboard group config',
                run: "click",
            },
            {
                trigger: `.o_data_row`,
                content: "A spreadsheet was added as dashboard",
                run: () => assertNSheetsInGroup(startingNumberOfSheetsInGroup + 1),
            },
            {
                trigger: 'button[name="action_add_document_spreadsheet_to_dashboard"]',
                content: "Open add document to dashboard modal",
                run: "click",
            },
            {
                trigger: ".o-spreadsheet-grid-image",
                content: "Focus a spreadsheet",
                run: focusFirstSheetInModal,
            },
            {
                trigger: ".o-spreadsheet-grid-image",
                content: "Double click a spreadsheet",
                run: "dblclick",
            },
            {
                trigger: '.o-sp-breadcrumb',
                content: 'Go back to the dashboard group config',
                run: "click",
            },
            {
                trigger: `.o_data_row`,
                content: "A spreadsheet was added as dashboard",
                run: () => assertNSheetsInGroup(startingNumberOfSheetsInGroup + 2),
            },
        ],
    });
