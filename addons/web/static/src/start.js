/** @odoo-module **/

import { makeEnv, startServices } from "./env";
import { localization } from "@web/core/l10n/localization";
import { session } from "@web/session";
import { templates } from "@web/core/assets";
import { hasTouch } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { App, Component, whenReady } from "@odoo/owl";

/**
 * Function to start a webclient.
 * It is used both in community and enterprise in main.js.
 * It's meant to be webclient flexible so we can have a subclass of
 * webclient in enterprise with added features.
 *
 * @param {Component} Webclient
 */
export async function startWebClient(Webclient) {
    odoo.info = {
        db: session.db,
        server_version: session.server_version,
        server_version_info: session.server_version_info,
        isEnterprise: session.server_version_info.slice(-1)[0] === "e",
    };
    odoo.isReady = false;

    // setup environment
    await whenReady();
    const env = makeEnv();
    await startServices(env);

    Component.env = env;

    // start web client
    const app = new App(Webclient, {
        name: "Odoo Web Client",
        env,
        templates,
        dev: env.debug,
        warnIfNoStaticProps: true,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });
    const root = await app.mount(document.body);
    const classList = document.body.classList;
    if (localization.direction === "rtl") {
        classList.add("o_rtl");
    }
    if (env.services.user.userId === 1) {
        classList.add("o_is_superuser");
    }
    if (env.debug) {
        classList.add("o_debug");
    }
    if (hasTouch()) {
        classList.add("o_touch_device");
    }
    // delete odoo.debug; // FIXME: some legacy code rely on this
    odoo.__WOWL_DEBUG__ = { root };
    odoo.isReady = true;
}
