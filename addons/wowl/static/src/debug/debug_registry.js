/** @odoo-module **/

import { Registry } from "../core/registry";
import { backendDebugManagerItems, globalDebugManagerItems } from "./debug_menu_items";

export const debugManagerRegistry = odoo.debugManagerRegistry = new Registry();

backendDebugManagerItems.forEach((item) => {
  debugManagerRegistry.add(item.name, item);
});

globalDebugManagerItems.forEach((item) => {
  debugManagerRegistry.add(item.name, item);
});
