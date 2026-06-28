import { registries } from "@odoo/o-spreadsheet";

import { IrMenuPlugin } from "./ir_ui_menu_plugin";

const { corePluginRegistry } = registries;

corePluginRegistry.add("ir_ui_menu_plugin", IrMenuPlugin);
