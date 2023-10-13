
declare module "@spreadsheet" {
  import { CorePlugin, UIPlugin } from "@odoo/o-spreadsheet";

  export interface OdooCorePlugin extends CorePlugin {
    getters: OdooCoreGetters;
  }

  export interface OdooCorePluginConstructor {
    new(config: unknown): OdooCorePlugin;
  }

  export interface OdooUIPlugin extends UIPlugin {
    getters: OdooGetters;
  }

  export interface OdooUIPluginConstructor {
    new(config: unknown): OdooUIPlugin;
  }
}
