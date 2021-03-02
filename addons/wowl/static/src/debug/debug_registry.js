/** @odoo-module **/

import { Registry } from "../core/registry";
import { backendDebugManagerItems, globalDebugManagerItems } from "./debug_menu_items";

export const debugRegistry = (odoo.debugRegistry = new Registry());

backendDebugManagerItems.forEach((item) => {
  debugRegistry.add(item.name, item);
});

globalDebugManagerItems.forEach((item) => {
  debugRegistry.add(item.name, item);
});
