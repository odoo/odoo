/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * @param {string} tourName
 * @param {string} templateName
 */
export function registerTemplateTour(tourName, templateName) {
    registry.category("web_tour.tours").add(
        tourName,
        {
            test: true,
            url: "/web",
            steps: () => [
            {
                trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
                content: "Open document app",
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
                content: "Open Configuration menu",
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
                run: `text ${templateName}`,
            },
            {
                trigger: ".o_menu_item.focus",
                content: "Validate search",
                run: "click",
            },
            {
                trigger: `tr.o_data_row:first-child td[data-tooltip="${templateName}"]`,
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
                isCheck: true,
            },
        ]
    });
}
