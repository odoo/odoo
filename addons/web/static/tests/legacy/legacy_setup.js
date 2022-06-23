/** @odoo-module alias=web.legacySetup **/
import { registry } from "@web/core/registry";
import legacyViewRegistry from "web.view_registry";

// in tests, there's nothing to setup globally (we don't want to deploy services),
// but this module must exist has it is required by other modules
export const legacySetupProm = Promise.resolve();

export function useLegacyViews(views = ["list", "form"]) {
  for (const vname of views) {
    registry.category("views").remove(vname); // remove new view from registry
    legacyViewRegistry.add(vname, legacyViewRegistry.get(vname)); // add legacy view -> will be wrapped and added to new registry
  }
}
