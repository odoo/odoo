/** @odoo-module **/

import { Registry } from "../core/registry";
import { backendDebugManagerItems, globalDebugManagerItems } from "./debug_manager_elements";

export const debugManagerRegistry = new Registry();

backendDebugManagerItems.forEach((item) => {
  debugManagerRegistry.add(item.name, item);
});

globalDebugManagerItems.forEach((item) => {
  debugManagerRegistry.add(item.name, item);
});
