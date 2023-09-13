/** @odoo-module alias=web.legacySetup **/

import { registry } from "../core/registry";
import {
    makeLegacyNotificationService,
    makeLegacyRPCService,
} from "./utils";
import { makeLegacyActionManagerService } from "./backend_utils";
import legacyEnv from "@web/legacy/js/env";
import { templates } from "@web/core/assets";

import { Component, whenReady } from "@odoo/owl";

let legacySetupResolver;
export const legacySetupProm = new Promise((resolve) => {
    legacySetupResolver = resolve;
});

// build the legacy env and set it on Component (this was done in main.js,
// with the starting of the webclient)
(async () => {
    Component.env = legacyEnv;
    const legacyActionManagerService = makeLegacyActionManagerService(legacyEnv);
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("legacy_action_manager", legacyActionManagerService);
    // add a service to redirect rpc events triggered on the bus in the
    // legacy env on the bus in the wowl env
    serviceRegistry.add("legacy_rpc", makeLegacyRPCService(legacyEnv));
    serviceRegistry.add("legacy_notification", makeLegacyNotificationService(legacyEnv));
    const wowlToLegacyServiceMappers = registry.category("wowlToLegacyServiceMappers").getEntries();
    for (const [legacyServiceName, wowlToLegacyServiceMapper] of wowlToLegacyServiceMappers) {
        serviceRegistry.add(legacyServiceName, wowlToLegacyServiceMapper(legacyEnv));
    }
    await whenReady();
    legacyEnv.templates = templates;
    legacySetupResolver(legacyEnv);
})();
