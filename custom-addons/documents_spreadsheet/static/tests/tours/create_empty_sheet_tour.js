/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("spreadsheet_create_empty_sheet", {
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
            content: "Open document app",
            run: "click",
        },
        {
            trigger: ".o_cp_buttons:contains('Upload') .dropdown-toggle.dropdown-toggle-split",
            content: "Open dropdown",
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
            trigger: '[data-menu-xmlid="documents.dashboard"]',
            content: "Go back to Document App",
        },
        {
            trigger: ".o_document_spreadsheet:first",
            content: "Reopen the sheet",
            run: "click",
        },
        {
            trigger: '[data-menu-xmlid="documents.dashboard"]',
            content: "Wait for the spreadsheet to be properly unloaded",
        },
    ],
});
registry.category("web_tour.tours").add("spreadsheet_create_list_view", {
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
            content: "Open document app",
            run: "click",
        },
        {
            trigger: "button.o_switch_view.o_list",
            content: "Switch to list view",
            run: "click",
        },
        {
            trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle",
            extra_trigger: ".o_list_view",
            content: "Open the cog menu",
            run: "click",
        },
        {
            trigger: ".o_control_panel .o_cp_action_menus .dropdown-toggle:contains(Spreadsheet)",
            run: function () {
                this.$anchor[0].dispatchEvent(new MouseEvent("mouseenter"));
            },
        },
        {
            trigger: ".o_insert_list_spreadsheet_menu",
            content: "Insert in spreadsheet",
            run: "click",
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
            trigger: ".o_pivot_cancel",
            content: "Go back to the list of lists",
            run: "click",
        },
        {
            trigger: '[data-menu-xmlid="documents.dashboard"]',
            content: "Wait for the spreadsheet to be properly unloaded",
        },
    ],
});
