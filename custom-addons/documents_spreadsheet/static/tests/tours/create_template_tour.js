/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const SHEET_NAME = "Res Partner Test Spreadsheet";
const TEMPLATE_NAME = `${SHEET_NAME} - Template`;

registry.category("web_tour.tours").add(
    "documents_spreadsheet_create_template_tour",
    {
        test: true,
        url: "/web",
        steps: () => [
        ...stepUtils.goToAppSteps("documents.menu_root", "Open Document app"),
        {
            trigger: 'li[title="Test folder"] header',
            content: "Open the test folder",
            run: "click",
        },
        {
            trigger: `div[title="${SHEET_NAME}"]`,
            content: "Select Test Sheet",
            run: "click",
        },
        {
            trigger: `button.o_switch_view.o_list`,
            content: "Switch to list view",
            run: "click",
        },
        {
            trigger: `img[title="${SHEET_NAME}"]`,
            content: "Open the sheet",
            run: "click",
        },
        {
            trigger: `.o-topbar-menu[data-id="file"]`,
            content: "Open the file menu",
            run: "click",
        },
        {
            trigger: `.o-menu-item[data-name="save_as_template"]`,
            content: "Save as template",
            run: "click",
        },
        {
            trigger: `button[name="save_template"]`,
            content: "Save as template",
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
            trigger: ".o_searchview .o_facet_remove",
            content: 'Remove "My templates" filter',
            run: "click",
        },
        {
            trigger: "input.o_searchview_input",
            content: "Search the template",
            run: `text ${TEMPLATE_NAME}`,
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
            trigger: ".o-spreadsheet",
            content: "Redirected to spreadsheet",
        },
    ]
});
