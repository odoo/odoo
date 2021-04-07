/** @odoo-module **/
import FormController from "web.FormController";
import { Registry } from "../../src/core/registry";
import { makeEnv } from "../../src/env";
import { registerCleanup } from "./cleanup";
import { makeMockServer } from "./mock_server";
import { makeFakeLocalizationService, makeFakeUIService, mocks } from "./mock_services";

function makeTestConfig(config = {}) {
  const serviceRegistry = config.serviceRegistry || new Registry();
  if (!serviceRegistry.contains("ui")) {
    serviceRegistry.add("ui", makeFakeUIService());
  }
  if (!serviceRegistry.contains("localization")) {
    serviceRegistry.add("localization", makeFakeLocalizationService());
  }
  return Object.assign(config, {
    debug: config.debug || "",
    serviceRegistry,
    mainComponentRegistry: config.mainComponentRegistry || new Registry(),
    actionRegistry: config.actionRegistry || new Registry(),
    systrayRegistry: config.systrayRegistry || new Registry(),
    errorDialogRegistry: config.errorDialogRegistry || new Registry(),
    userMenuRegistry: config.userMenuRegistry || new Registry(),
    debugRegistry: config.debugRegistry || new Registry(),
    viewRegistry: config.viewRegistry || new Registry(),
  });
}

/**
 * @typedef {import("../../src/env").OdooEnv} OdooEnv
 */

/**
 * Create a test environment
 *
 * @param {*} config
 * @returns {Promise<OdooEnv>}
 */
export async function makeTestEnv(config = {}) {
  const testConfig = makeTestConfig(config);
  if (config.serverData || config.mockRPC || config.activateMockServer) {
    testConfig.serviceRegistry.remove("rpc");
    makeMockServer(testConfig, config.serverData, config.mockRPC);
  }

  // remove the multi-click delay for the quick edit in form views
  // todo: move this elsewhere (setup?)
  const initialQuickEditDelay = FormController.prototype.multiClickTime;
  FormController.prototype.multiClickTime = 0;
  registerCleanup(() => {
    FormController.prototype.multiClickTime = initialQuickEditDelay;
  });

  // add all missing dependencies if necessary
  for (let service of testConfig.serviceRegistry.getAll()) {
    if (service.dependencies) {
      for (let dep of service.dependencies) {
        if (dep in mocks && !testConfig.serviceRegistry.contains(dep)) {
          testConfig.serviceRegistry.add(dep, mocks[dep]());
        }
      }
    }
  }
  odoo = makeTestOdoo(testConfig);
  const env = await makeEnv(odoo.debug);
  env.qweb.addTemplates(window.__ODOO_TEMPLATES__);
  return env;
}

export function makeTestOdoo(config = {}) {
  return Object.assign({}, odoo, {
    browser: {},
    debug: config.debug,
    session_info: {
      cache_hashes: {
        load_menus: "161803",
        translations: "314159",
      },
      currencies: {
        1: { name: "USD", digits: [69, 2], position: "before", symbol: "$" },
        2: { name: "EUR", digits: [69, 2], position: "after", symbol: "€" },
      },
      user_context: {
        lang: "en",
        uid: 7,
        tz: "taht",
      },
      qweb: "owl",
      uid: 7,
      name: "Mitchell",
      username: "The wise",
      is_admin: true,
      partner_id: 7,
      // Commit: 3e847fc8f499c96b8f2d072ab19f35e105fd7749
      // to see what user_companies is
      user_companies: {
        allowed_companies: { 1: { id: 1, name: "Hermit" } },
        current_company: 1,
      },
      db: "test",
      server_version: "1.0",
      server_version_info: ["1.0"],
    },
    serviceRegistry: config.serviceRegistry,
    mainComponentRegistry: config.mainComponentRegistry,
    actionRegistry: config.actionRegistry,
    systrayRegistry: config.systrayRegistry,
    errorDialogRegistry: config.errorDialogRegistry,
    userMenuRegistry: config.userMenuRegistry,
    debugRegistry: config.debugRegistry,
    viewRegistry: config.viewRegistry,
    commandCategoryRegistry: config.commandCategoryRegistry,
  });
}
