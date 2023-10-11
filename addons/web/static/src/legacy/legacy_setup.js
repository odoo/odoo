/** @odoo-module alias=web.legacySetup **/

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
    await whenReady();
    legacyEnv.templates = templates;
    legacySetupResolver(legacyEnv);
})();
