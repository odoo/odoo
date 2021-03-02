/** @odoo-module **/
import { actionRegistry } from "./actions/action_registry";
import { errorDialogRegistry } from "./errors/error_dialog_registry";
import { debugManagerRegistry } from "./debug/debug_manager_registry";
import { makeEnv, makeRAMLocalStorage } from "./env";
import { mapLegacyEnvToWowlEnv } from "./legacy/utils";
import { legacySetupProm } from "./legacy/legacy_setup";
import { serviceRegistry } from "./services/service_registry";
import { viewRegistry } from "./views/view_registry";
import { mainComponentRegistry } from "./webclient/main_component_registry";
import { systrayRegistry } from "./webclient/systray_registry";
import { userMenuRegistry } from "./webclient/user_menu_registry";
import { WebClient } from "./webclient/webclient";

const { mount, utils } = owl;
const { whenReady, loadFile } = utils;

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
  odoo.userMenuRegistry = userMenuRegistry;
  odoo.mainComponentRegistry = mainComponentRegistry;
  odoo.actionRegistry = actionRegistry;
  odoo.viewRegistry = viewRegistry;
  odoo.systrayRegistry = systrayRegistry;
  odoo.errorDialogRegistry = errorDialogRegistry;
  odoo.serviceRegistry = serviceRegistry;
  odoo.debugManagerRegistry = debugManagerRegistry;
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

async function loadTemplates() {
  const templatesUrl = `/wowl/templates/${odoo.session_info.qweb}`;
  const templates = await loadFile(templatesUrl);
  // as we currently have two qweb engines (owl and legacy), owl templates are
  // flagged with attribute `owl="1"`. The following lines removes the 'owl'
  // attribute from the templates, so that it doesn't appear in the DOM. For now,
  // we make the assumption that 'templates' only contains owl templates. We
  // might need at some point to handle the case where we have both owl and
  // legacy templates. At the end, we'll get rid of all this.
  const doc = new DOMParser().parseFromString(templates, "text/xml");
  for (let child of doc.querySelectorAll("templates > [owl]")) {
    child.removeAttribute("owl");
  }
  return new XMLSerializer().serializeToString(doc);
}
