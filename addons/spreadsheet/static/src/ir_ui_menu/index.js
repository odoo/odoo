/** @odoo-module */

import { registry } from "@web/core/registry";
import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";

import IrMenuPlugin from "./ir_ui_menu_plugin";

import {
    isMarkdownIrMenuIdLink,
    isMarkdownIrMenuXmlLink,
    isMarkdownViewLink,
    parseIrMenuXmlLink,
    OdooViewLinkCell,
    OdooMenuLinkCell,
    parseViewLink,
    parseIrMenuIdLink,
} from "./odoo_menu_link_cell";

const { cellRegistry, corePluginRegistry } = spreadsheet.registries;
const { parseMarkdownLink } = spreadsheet.helpers;

corePluginRegistry.add("ir_ui_menu_plugin", IrMenuPlugin);

export const spreadsheetLinkMenuCellService = {
    dependencies: ["menu"],
    start(env) {
        function _getIrMenuByXmlId(xmlId) {
            const menu = env.services.menu.getAll().find((menu) => menu.xmlid === xmlId);
            if (!menu) {
                throw new Error(
                    `Menu ${xmlId} not found. You may not have the required access rights.`
                );
            }
            return menu;
        }

        cellRegistry
            .add("OdooMenuIdLink", {
                sequence: 65,
                match: isMarkdownIrMenuIdLink,
                createCell: (id, content, properties, sheetId, getters) => {
                    const { url } = parseMarkdownLink(content);
                    const menuId = parseIrMenuIdLink(url);
                    const menuName = env.services.menu.getMenu(menuId).name;
                    return new OdooMenuLinkCell(id, content, menuId, menuName, properties);
                },
            })
            .add("OdooMenuXmlLink", {
                sequence: 66,
                match: isMarkdownIrMenuXmlLink,
                createCell: (id, content, properties, sheetId, getters) => {
                    const { url } = parseMarkdownLink(content);
                    const xmlId = parseIrMenuXmlLink(url);
                    const menuId = _getIrMenuByXmlId(xmlId).id;
                    const menuName = _getIrMenuByXmlId(xmlId).name;
                    return new OdooMenuLinkCell(id, content, menuId, menuName, properties);
                },
            })
            .add("OdooIrFilterLink", {
                sequence: 67,
                match: isMarkdownViewLink,
                createCell: (id, content, properties, sheetId, getters) => {
                    const { url } = parseMarkdownLink(content);
                    const actionDescription = parseViewLink(url);
                    return new OdooViewLinkCell(id, content, actionDescription, properties);
                },
            });

        return true;
    },
};

registry.category("services").add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
