/** @odoo-module **/

import { makeEnv, startServices } from "./env";
import { legacySetupProm } from "./legacy/legacy_setup";
import { mapLegacyEnvToWowlEnv } from "./legacy/utils";
import { processTemplates } from "./core/assets";

const { mount, utils } = owl;
const { whenReady } = utils;

/**
 * Function to start a webclient.
 * It is used both in community and enterprise in main.js.
 * It's meant to be webclient flexible so we can have a subclass of
 * webclient in enterprise with added features.
 *
 * @param {owl.Component} Webclient
 */
export async function startWebClient(Webclient) {
    // delete (odoo as any).session_info; // FIXME: some legacy code rely on this (e.g. ajax.js)
    const sessionInfo = odoo.session_info;
    odoo.info = {
        db: sessionInfo.db,
        server_version: sessionInfo.server_version,
        server_version_info: sessionInfo.server_version_info,
    };
    odoo.isReady = false;

    // setup environment
    const env = makeEnv();
    const [, templates] = await Promise.all([
        startServices(env),
        odoo.loadTemplatesPromise.then(processTemplates),
    ]);
    env.qweb.addTemplates(templates);

    // start web client
    await whenReady();
    const legacyEnv = await legacySetupProm;
    mapLegacyEnvToWowlEnv(legacyEnv, env);
    const root = await mount(Webclient, { env, target: document.body, position: "self" });
    // delete odoo.debug; // FIXME: some legacy code rely on this
    odoo.__WOWL_DEBUG__ = { root };
    odoo.isReady = true;
}
