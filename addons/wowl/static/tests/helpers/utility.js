/** @odoo-module **/
import { Registry } from "../../src/core/registry";
import { makeEnv } from "../../src/env";
import { makeFakeDeviceService, makeFakeLocalizationService, makeTestOdoo, mocks } from "./mocks";
import { makeMockServer } from "./mock_server";
export async function mount(C, params) {
  C.env = params.env;
  const component = new C(null);
  const target = params.target || getFixture();
  await component.mount(target, { position: "first-child" });
  return component;
}
function makeTestConfig(config = {}) {
  const serviceRegistry = config.serviceRegistry || new Registry();
  if (!serviceRegistry.contains("device")) {
    serviceRegistry.add("device", makeFakeDeviceService());
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
    debugManagerRegistry: config.debugManagerRegistry || new Registry(),
    viewRegistry: config.viewRegistry || new Registry(),
  });
}
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
  let prom = new Promise((_r) => {
    resolve = _r;
  });
  prom.resolve = resolve;
  return prom;
}
export function click(el, selector) {
  let target = el;
  if (selector) {
    const els = el.querySelectorAll(selector);
    if (els.length === 0) {
      throw new Error(`Found no element to click on (selector: ${selector})`);
    }
    if (els.length > 1) {
      throw new Error(
        `Found ${els.length} elements to click on, instead of 1 (selector: ${selector})`
      );
    }
    target = els[0];
  }
  const ev = new MouseEvent("click", { bubbles: true });
  target.dispatchEvent(ev);
  return nextTick();
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
