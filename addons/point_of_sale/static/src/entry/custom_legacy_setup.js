/** @odoo-module alias=web.legacySetup default=false **/

/**
 * We are replacing the `web.legacySetup` defined in web addon
 * with this module in order to skip the other legacy modules,
 * and only load what the PoS UI needed -- the legacy_action_manager.
 */

import { registry } from "@web/core/registry";
import { makeLegacyActionManagerService } from "@web/legacy/backend_utils";
import * as AbstractService from "web.AbstractService";
import * as legacyEnv from "web.env";
import * as session from "web.session";

const { Component, whenReady } = owl;

let legacySetupResolver;
export const legacySetupProm = new Promise((resolve) => {
    legacySetupResolver = resolve;
});

// build the legacy env and set it on Component (this was done in main.js,
// with the starting of the webclient)
(async () => {
    AbstractService.prototype.deployServices(legacyEnv);
    Component.env = legacyEnv;
    const legacyActionManagerService = makeLegacyActionManagerService(legacyEnv);
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("legacy_action_manager", legacyActionManagerService);
    await Promise.all([whenReady(), session.is_bound]);
    legacyEnv.templates = session.owlTemplates;
    legacySetupResolver(legacyEnv);
})();
