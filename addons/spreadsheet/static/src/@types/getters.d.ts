import { CorePlugin, Model, UID } from "@odoo/o-spreadsheet";
import { ChartOdooMenuPlugin, OdooChartCorePlugin, OdooChartUIPlugin } from "@spreadsheet/chart";
import { CurrencyPlugin } from "@spreadsheet/currency/plugins/currency";
import { AccountingPlugin } from "addons/spreadsheet_account/static/src/plugins/accounting_plugin";
import { GlobalFiltersCorePlugin, GlobalFiltersUIPlugin } from "@spreadsheet/global_filters";
import { ListCorePlugin, ListUIPlugin } from "@spreadsheet/list";
import { IrMenuPlugin } from "@spreadsheet/ir_ui_menu/ir_ui_menu_plugin";
import { PivotOdooCorePlugin } from "@spreadsheet/pivot";
import { PivotCoreGlobalFilterPlugin } from "@spreadsheet/pivot/plugins/pivot_core_global_filter_plugin";

type Getters = Model["getters"];
type CoreGetters = CorePlugin["getters"];

/**
 * Union of all getter names of a plugin.
 *
 * e.g. With the following plugin
 * @example
 * class MyPlugin {
 *   static getters = [
 *     "getCell",
 *     "getCellValue",
 *   ] as const;
 *   getCell() { ... }
 *   getCellValue() { ... }
 * }
 * type Names = GetterNames<typeof MyPlugin>
 * // is equivalent to "getCell" | "getCellValue"
 */
type GetterNames<Plugin extends { getters: readonly string[] }> = Plugin["getters"][number];

/**
 * Extract getter methods from a plugin, based on its `getters` static array.
 * @example
 * class MyPlugin {
 *   static getters = [
 *     "getCell",
 *     "getCellValue",
 *   ] as const;
 *   getCell() { ... }
 *   getCellValue() { ... }
 * }
 * type MyPluginGetters = PluginGetters<typeof MyPlugin>;
 * // MyPluginGetters is equivalent to:
 * // {
 * //   getCell: () => ...,
 * //   getCellValue: () => ...,
 * // }
 */
type PluginGetters<Plugin extends { new (...args: unknown[]): any; getters: readonly string[] }> =
    Pick<InstanceType<Plugin>, GetterNames<Plugin>>;

declare module "@spreadsheet" {
    /**
     * Add getters from custom plugins defined in odoo
     */

    interface OdooCoreGetters extends CoreGetters {}
    interface OdooCoreGetters extends PluginGetters<typeof GlobalFiltersCorePlugin> {}
    interface OdooCoreGetters extends PluginGetters<typeof ListCorePlugin> {}
    interface OdooCoreGetters extends PluginGetters<typeof OdooChartCorePlugin> {}
    interface OdooCoreGetters extends PluginGetters<typeof ChartOdooMenuPlugin> {}
    interface OdooCoreGetters extends PluginGetters<typeof IrMenuPlugin> {}
    interface OdooCoreGetters extends PluginGetters<typeof PivotOdooCorePlugin> {}
    interface OdooCoreGetters extends PluginGetters<typeof PivotCoreGlobalFilterPlugin> {}

    interface OdooGetters extends Getters {}
    interface OdooGetters extends OdooCoreGetters {}
    interface OdooGetters extends PluginGetters<typeof GlobalFiltersUIPlugin> {}
    interface OdooGetters extends PluginGetters<typeof ListUIPlugin> {}
    interface OdooGetters extends PluginGetters<typeof OdooChartUIPlugin> {}
    interface OdooGetters extends PluginGetters<typeof CurrencyPlugin> {}
    interface OdooGetters extends PluginGetters<typeof AccountingPlugin> {}
}
