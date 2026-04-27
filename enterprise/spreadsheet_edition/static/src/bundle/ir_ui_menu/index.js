/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { initCallbackRegistry } from "@spreadsheet/o_spreadsheet/init_callbacks";
import {
    buildIrMenuIdLink,
    buildViewLink,
    buildIrMenuXmlLink,
} from "@spreadsheet/ir_ui_menu/odoo_menu_link_cell";
import { IrMenuSelectorDialog } from "@spreadsheet_edition/bundle/ir_menu_selector/ir_menu_selector";

const { markdownLink } = spreadsheet.links;
const { linkMenuRegistry } = spreadsheet.registries;

/**
 * Helper to get the function to be called when the spreadsheet is opened
 * in order to insert the link.
 * @param {import("@spreadsheet/ir_ui_menu/odoo_menu_link_cell").ViewLinkDescription} actionToLink
 * @returns Function to call
 */
function insertLink(actionToLink) {
    return (model) => {
        if (!this.isEmptySpreadsheet) {
            const sheetId = model.uuidGenerator.uuidv4();
            const sheetIdFrom = model.getters.getActiveSheetId();
            model.dispatch("CREATE_SHEET", {
                sheetId,
                position: model.getters.getSheetIds().length,
            });
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        }
        const viewLink = buildViewLink(actionToLink);
        model.dispatch("UPDATE_CELL", {
            sheetId: model.getters.getActiveSheetId(),
            content: markdownLink(actionToLink.name, viewLink),
            col: 0,
            row: 0,
        });
    };
}

initCallbackRegistry.add("insertLink", insertLink);

linkMenuRegistry.add("odooMenu", {
    name: _t("Link an Odoo menu"),
    sequence: 20,
    execute: async (env) => {
        return new Promise((resolve) => {
            const closeDialog = env.services.dialog.add(IrMenuSelectorDialog, {
                onMenuSelected: (menuId) => {
                    closeDialog();
                    const menu = env.services.menu.getMenu(menuId);
                    const xmlId = menu && menu.xmlid;
                    const url = xmlId ? buildIrMenuXmlLink(xmlId) : buildIrMenuIdLink(menuId);
                    const label = menu.name;
                    resolve(markdownLink(label, url));
                },
            });
        });
    },
});
