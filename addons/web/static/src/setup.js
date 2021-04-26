/** @odoo-module **/

import { makeEnv } from "./env";
import { mapLegacyEnvToWowlEnv } from "./legacy/utils";
import { legacySetupProm } from "./legacy/legacy_setup";
import { loadTemplates } from "./webclient/setup";

const { mount, utils } = owl;
const { whenReady } = utils;

export async function startWebClient(webclient) {
  // delete (odoo as any).session_info; // FIXME: some legacy code rely on this (e.g. ajax.js)
  const sessionInfo = odoo.session_info;
  odoo.info = {
    db: sessionInfo.db,
    server_version: sessionInfo.server_version,
    server_version_info: sessionInfo.server_version_info,
  };

  // setup environment
  const [env, templates] = await Promise.all([makeEnv(odoo.debug), loadTemplates()]);
  env.qweb.addTemplates(templates);

  // start web client
  await whenReady();
  const legacyEnv = await legacySetupProm;
  mapLegacyEnvToWowlEnv(legacyEnv, env);
  const root = await mount(webclient, { env, target: document.body, position: "self" });
  delete odoo.debug;
  odoo.__WOWL_DEBUG__ = { root };
}
