import { registries } from "@odoo/o-spreadsheet";
import { onWillUnmount } from "@odoo/owl";

import { addToRegistryWithCleanup } from "@spreadsheet_edition/bundle/helpers/misc";
import { QualitySpreadsheetPlugin } from "./quality_spreadsheet_plugin";


const { corePluginRegistry } = registries;

/**
 * Adds the spreadsheet quality check plugins and menus
 * and removes them when the action is left
 */
export function useSpreadsheetQualityControlExtension() {
    addQualitySpreadsheetExtensionWithCleanUp(onWillUnmount);
}

function addQualitySpreadsheetExtensionWithCleanUp(cleanUpHook = () => {}) {
    addToRegistryWithCleanup(
        cleanUpHook,
        corePluginRegistry,
        "quality_check_spreadsheet_plugin",
        QualitySpreadsheetPlugin
    );
}
