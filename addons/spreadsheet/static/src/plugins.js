import { CorePlugin, CoreViewPlugin, UIPlugin } from "@odoo/o-spreadsheet";

/**
 * An o-spreadsheet core plugin with access to all custom Odoo plugins
 * @type {import("@spreadsheet").OdooCorePluginConstructor}
 **/
export const OdooCorePlugin = CorePlugin;

/**
 * An o-spreadsheet CoreView plugin with access to all custom Odoo plugins
 * @type {import("@spreadsheet").OdooUIPluginConstructor}
 **/
export const OdooCoreViewPlugin = CoreViewPlugin;

/**
 * An o-spreadsheet UI plugin with access to all custom Odoo plugins
 * @type {import("@spreadsheet").OdooUIPluginConstructor}
 **/
export const OdooUIPlugin = UIPlugin;
