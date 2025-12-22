/** @odoo-module */

import { CorePlugin, UIPlugin } from "@odoo/o-spreadsheet";

/**
 * An o-spreadsheet core plugin with access to all custom Odoo plugins
 * @type {import("@spreadsheet").OdooCorePluginConstructor}
 **/
export const OdooCorePlugin = CorePlugin;

/**
 * An o-spreadsheet UI plugin with access to all custom Odoo plugins
 * @type {import("@spreadsheet").OdooUIPluginConstructor}
 **/
export const OdooUIPlugin = UIPlugin;
