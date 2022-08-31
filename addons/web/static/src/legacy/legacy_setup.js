/** @odoo-module alias=web.legacySetup **/

import { registry } from "../core/registry";
import {
    makeLegacyNotificationService,
    makeLegacyRpcService,
    makeLegacySessionService,
    makeLegacyDialogMappingService,
    makeLegacyCrashManagerService,
    makeLegacyCommandService,
    makeLegacyDropdownService,
} from "./utils";
import { makeLegacyActionManagerService } from "./backend_utils";
import * as AbstractService from "web.AbstractService";
import legacyEnv from "web.env";
import * as session from "web.session";
import * as makeLegacyWebClientService from "web.pseudo_web_client";

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
    // add a service to redirect rpc events triggered on the bus in the
    // legacy env on the bus in the wowl env
    const legacyRpcService = makeLegacyRpcService(legacyEnv);
    serviceRegistry.add("legacy_rpc", legacyRpcService);
    const legacySessionService = makeLegacySessionService(legacyEnv, session);
    serviceRegistry.add("legacy_session", legacySessionService);
    const legacyWebClientService = makeLegacyWebClientService(legacyEnv);
    serviceRegistry.add("legacy_web_client", legacyWebClientService);
    serviceRegistry.add("legacy_notification", makeLegacyNotificationService(legacyEnv));
    serviceRegistry.add("legacy_crash_manager", makeLegacyCrashManagerService(legacyEnv));
    const legacyDialogMappingService = makeLegacyDialogMappingService(legacyEnv);
    serviceRegistry.add("legacy_dialog_mapping", legacyDialogMappingService);
    const legacyCommandService = makeLegacyCommandService(legacyEnv);
    serviceRegistry.add("legacy_command", legacyCommandService);
    serviceRegistry.add("legacy_dropdown", makeLegacyDropdownService(legacyEnv));
    const wowlToLegacyServiceMappers = registry.category("wowlToLegacyServiceMappers").getEntries();
    for (const [legacyServiceName, wowlToLegacyServiceMapper] of wowlToLegacyServiceMappers) {
        serviceRegistry.add(legacyServiceName, wowlToLegacyServiceMapper(legacyEnv));
    }
    await Promise.all([whenReady(), session.is_bound]);
    legacyEnv.templates = session.owlTemplates;
    legacySetupResolver(legacyEnv);
})();
