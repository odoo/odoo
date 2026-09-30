import { registry } from "@web/core/registry";
import * as spreadsheet from "@odoo/o-spreadsheet";

import { IrMenuPlugin } from "./ir_ui_menu_plugin";

import {
    isMarkdownIrMenuIdUrl,
    isIrMenuXmlUrl,
    isMarkdownViewUrl,
    parseIrMenuXmlUrl,
    parseViewLink,
    parseIrMenuIdLink,
} from "./odoo_menu_link_cell";
import { _t } from "@web/core/l10n/translation";
import { navigateTo } from "../actions/helpers";

const { urlRegistry, corePluginRegistry, errorTypes } = spreadsheet.registries;
const { EvaluationError } = spreadsheet;

corePluginRegistry.add("ir_ui_menu_plugin", IrMenuPlugin);

const LINK_ERROR = "#LINK";
errorTypes.add(LINK_ERROR);

class BadOdooLinkError extends EvaluationError {
    constructor(menuId) {
        super(
            _t("Menu %s not found. You may not have the required access rights.", menuId),
            LINK_ERROR
        );
    }
}

export const spreadsheetLinkMenuCellService = {
    dependencies: ["menu"],
    start(env) {
        function _getIrMenuByXmlId(xmlId) {
            const menu = env.services.menu.getAll().find((menu) => menu.xmlid === xmlId);
            if (!menu) {
                throw new BadOdooLinkError(xmlId);
            }
            return menu;
        }

        urlRegistry
            .replace("OdooMenuIdLink", {
                sequence: 65,
                match: isMarkdownIrMenuIdUrl,
                createLink(url, label) {
                    const menuId = parseIrMenuIdLink(url);
                    const menu = env.services.menu.getMenu(menuId);
                    if (!menu) {
                        throw new BadOdooLinkError(menuId);
                    }
                    return {
                        url,
                        label,
                        isExternal: false,
                        isUrlEditable: false,
                    };
                },
                urlRepresentation(url) {
                    const menuId = parseIrMenuIdLink(url);
                    return env.services.menu.getMenu(menuId).name;
                },
                open(url, env, newWindow) {
                    const menuId = parseIrMenuIdLink(url);
                    const menu = env.services.menu.getMenu(menuId);
                    env.services.action.doAction(menu.actionID, { newWindow });
                },
            })
            .replace("OdooMenuXmlLink", {
                sequence: 66,
                match: isIrMenuXmlUrl,
                createLink(url, label) {
                    const xmlId = parseIrMenuXmlUrl(url);
                    _getIrMenuByXmlId(xmlId); // Validate the XML ID exists
                    return {
                        url,
                        label,
                        isExternal: false,
                        isUrlEditable: false,
                    };
                },
                urlRepresentation(url) {
                    const xmlId = parseIrMenuXmlUrl(url);
                    const menuId = _getIrMenuByXmlId(xmlId).id;
                    return env.services.menu.getMenu(menuId).name;
                },
                open(url, env, newWindow) {
                    const xmlId = parseIrMenuXmlUrl(url);
                    const menuId = _getIrMenuByXmlId(xmlId).id;
                    const menu = env.services.menu.getMenu(menuId);
                    env.services.action.doAction(menu.actionID, { newWindow });
                },
            })
            .replace("OdooViewLink", {
                sequence: 67,
                match: isMarkdownViewUrl,
                createLink(url, label) {
                    return {
                        url,
                        label,
                        isExternal: false,
                        isUrlEditable: false,
                    };
                },
                urlRepresentation(url) {
                    const actionDescription = parseViewLink(url);
                    return actionDescription.name;
                },
                async open(url, env, newWindow) {
                    const { viewType, action, name } = parseViewLink(url);
                    await navigateTo(
                        env,
                        action.xmlId,
                        {
                            type: "ir.actions.act_window",
                            name: name,
                            res_model: action.modelName,
                            views: action.views,
                            target: "current",
                            domain: action.domain,
                            context: action.context,
                        },
                        { viewType, newWindow }
                    );
                },
            });

        return true;
    },
};

registry.category("services").add("spreadsheetLinkMenuCell", spreadsheetLinkMenuCellService);
