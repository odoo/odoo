/** @odoo-module */

import { busService } from "@bus/services/bus_service";
import { busParametersService } from "@bus/bus_parameters_service";
import { multiTabService } from "@bus/multi_tab_service";

import { InsertListSpreadsheetMenu } from "@spreadsheet_edition/assets/list_view/insert_list_spreadsheet_menu_owl";
import { makeFakeUserService } from "@web/../tests/helpers/mock_services";
import { loadJS } from "@web/core/assets";
import { dialogService } from "@web/core/dialog/dialog_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ormService } from "@web/core/orm_service";
import { nameService } from "@web/core/name_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeFakeSpreadsheetService } from "@spreadsheet_edition/../tests/utils/collaborative_helpers";
import { Spreadsheet } from "@odoo/o-spreadsheet";
import { SpreadsheetComponent } from "@spreadsheet_edition/bundle/actions/spreadsheet_component";

const serviceRegistry = registry.category("services");

export async function prepareWebClientForSpreadsheet() {
    await loadJS("/web/static/lib/Chart/Chart.js");
    serviceRegistry.add("spreadsheet_collaborative", makeFakeSpreadsheetService(), { force: true });
    serviceRegistry.add(
        "user",
        makeFakeUserService(() => true),
        { force: true }
    );
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("dialog", dialogService);
    serviceRegistry.add("ui", uiService);
    serviceRegistry.add("name", nameService);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("bus_service", busService);
    serviceRegistry.add("bus.parameters", busParametersService);
    serviceRegistry.add("multi_tab", multiTabService);
    registry.category("favoriteMenu").add(
        "insert-list-spreadsheet-menu",
        {
            Component: InsertListSpreadsheetMenu,
            groupNumber: 4,
            isDisplayed: ({ config, isSmall }) =>
                !isSmall &&
                config.actionType === "ir.actions.act_window" &&
                config.viewType === "list",
        },
        { sequence: 5 }
    );
}

function getChildFromComponent(component, cls) {
    return Object.values(component.__owl__.children).find((child) => child.component instanceof cls)
        .component;
}

/**
 * Return the odoo spreadsheet component
 * @param {*} actionManager
 * @returns {SpreadsheetComponent}
 */
export function getSpreadsheetComponent(actionManager) {
    return getChildFromComponent(actionManager, SpreadsheetComponent);
}

/**
 * Return the o-spreadsheet component
 * @param {*} actionManager
 * @returns {Component}
 */
export function getOSpreadsheetComponent(actionManager) {
    return getChildFromComponent(getSpreadsheetComponent(actionManager), Spreadsheet);
}

/**
 * Return the o-spreadsheet Model
 */
export function getSpreadsheetActionModel(actionManager) {
    return getOSpreadsheetComponent(actionManager).model;
}

export function getSpreadsheetActionTransportService(actionManager) {
    return actionManager.transportService;
}

export function getSpreadsheetActionEnv(actionManager) {
    const model = getSpreadsheetActionModel(actionManager);
    const component = getSpreadsheetComponent(actionManager);
    const oComponent = getOSpreadsheetComponent(actionManager);
    return Object.assign(Object.create(component.env), {
        model,
        openSidePanel: oComponent.openSidePanel.bind(oComponent),
    });
}
