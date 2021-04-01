/** @odoo-module **/
import { makeEnv } from "../../src/env";
import { Registry } from "../../src/core/registry";
import { actionService } from "../../src/actions/action_service";
import { effectService } from "../../src/effects/effect_service";
import { notificationService } from "../../src/notifications/notification_service";
import { dialogService } from "../../src/services/dialog_service";
import { hotkeyService } from "../../src/hotkey/hotkey_service";
import { menuService } from "../../src/services/menu_service";
import { ormService } from "../../src/services/orm_service";
import { popoverService } from "../../src/services/popover_service";
import { uiService } from "../../src/services/ui_service";
import { viewService } from "../../src/views/view_service";
import { viewRegistry } from "../../src/views/view_registry";
import {
  fakeTitleService,
  makeFakeUIService,
  makeFakeLocalizationService,
  makeFakeRouterService,
  makeFakeUserService,
  makeTestOdoo,
  mocks,
} from "./mocks";
import { makeMockServer } from "./mock_server";
import { registerCleanup } from "./cleanup";

const { Settings } = luxon;

/**
 * Patch the native Date object
 *
 * Note that it will be automatically unpatched at the end of the test
 *
 * @param {number} [year]
 * @param {number} [month]
 * @param {number} [day]
 * @param {number} [hours]
 * @param {number} [minutes]
 * @param {number} [seconds]
 */
export function patchDate(year, month, day, hours, minutes, seconds) {
  const actualDate = new Date();
  const fakeDate = new Date(year, month, day, hours, minutes, seconds);
  const timeInterval = actualDate.getTime() - fakeDate.getTime();
  Settings.now = () => Date.now() - timeInterval;
  registerCleanup(() => Settings.resetCaches());
}

export function makeTestServiceRegistry() {
  // build the service registry

  // need activateMockServer or something like that for odoo.browser.fetch !!! something is bad
  const testServiceRegistry = new Registry();
  const fakeUserService = makeFakeUserService();
  const fakeRouterService = makeFakeRouterService();

  testServiceRegistry
    .add("user", fakeUserService)
    .add("notification", notificationService)
    .add("dialog", dialogService)
    .add("menu", menuService)
    .add("action", actionService)
    .add("router", fakeRouterService)
    .add("view", viewService)
    .add("orm", ormService)
    .add("title", fakeTitleService)
    .add("ui", uiService)
    .add("effect", effectService)
    .add("hotkey", hotkeyService)
    .add("popover", popoverService);
  return testServiceRegistry;
}

export function makeTestViewRegistry() {
  // build a copy of the view registry
  const testViewRegistry = new Registry();
  for (const [key, view] of viewRegistry.getEntries()) {
    testViewRegistry.add(key, view);
  }
  return testViewRegistry;
}

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
  env.qweb.addTemplates(templates);
  return env;
}

export function getFixture() {
  if (QUnit.config.debug) {
    return document.body;
  } else {
    return document.querySelector("#qunit-fixture");
  }
}

export async function nextTick() {
  await new Promise((resolve) => window.requestAnimationFrame(resolve));
  await new Promise((resolve) => setTimeout(resolve));
}

export function makeDeferred() {
  let resolve;
  let reject;
  let prom = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  prom.resolve = resolve;
  prom.reject = reject;
  return prom;
}

function findElement(el, selector) {
  let target = el;
  if (selector) {
    const els = el.querySelectorAll(selector);
    if (els.length === 0) {
      throw new Error(`No element found (selector: ${selector})`);
    }
    if (els.length > 1) {
      throw new Error(`Found ${els.length} elements, instead of 1 (selector: ${selector})`);
    }
    target = els[0];
  }
  return target;
}

export function triggerEvent(el, selector, eventType, eventAttrs) {
  const target = findElement(el, selector);
  target.dispatchEvent(new Event(eventType, eventAttrs));
  return nextTick();
}

export function click(el, selector) {
  return triggerEvent(el, selector, "click", { bubbles: true, cancelable: true });
}

// -----------------------------------------------------------------------------
// Private (should not be called from any test)
// -----------------------------------------------------------------------------

let templates;
export function setTemplates(xml) {
  templates = xml;
}

export async function legacyExtraNextTick() {
  return nextTick();
}
