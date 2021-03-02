/** @odoo-module **/
import { makeEnv, makeRAMLocalStorage } from "./env";
import { mapLegacyEnvToWowlEnv } from "./legacy/utils";
import { legacySetupProm } from "./legacy/legacy_setup";
import { WebClient } from "./webclient/webclient";
import { loadTemplates } from "./webclient/setup";

const { mount, utils } = owl;
const { whenReady } = utils;

(async () => {
  // prepare browser object
  let sessionStorage = window.sessionStorage;
  let localStorage = owl.browser.localStorage;
  try {
    // Safari crashes in Private Browsing
    localStorage.setItem("__localStorage__", "true");
    localStorage.removeItem("__localStorage__");
  } catch (e) {
    localStorage = makeRAMLocalStorage();
    sessionStorage = makeRAMLocalStorage();
  }
  odoo.browser = odoo.browser || {};
  odoo.browser = Object.assign(odoo.browser, owl.browser, {
    console: window.console,
    location: window.location,
    navigator: navigator,
    open: window.open.bind(window),
    XMLHttpRequest: window.XMLHttpRequest,
    localStorage,
    sessionStorage,
  });

  // setup environment
  const [env, templates] = await Promise.all([makeEnv(odoo.debug), loadTemplates()]);
  env.qweb.addTemplates(templates);
  // start web client
  await whenReady();
  const legacyEnv = await legacySetupProm;
  mapLegacyEnvToWowlEnv(legacyEnv, env);
  const root = await mount(WebClient, { env, target: document.body, position: "self" });
  // prepare runtime Odoo object
  const sessionInfo = odoo.session_info;
  // delete (odoo as any).session_info; // FIXME: some legacy code rely on this (e.g. ajax.js)
  delete odoo.debug;
  odoo.__WOWL_DEBUG__ = { root };
  odoo.info = {
    db: sessionInfo.db,
    server_version: sessionInfo.server_version,
    server_version_info: sessionInfo.server_version_info,
  };
})();
