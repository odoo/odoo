/** @odoo-module **/
import { deployServices } from "./services/deploy_services";
export async function makeEnv(debug) {
  const env = {
    browser: owl.browser,
    qweb: new owl.QWeb(),
    bus: new owl.core.EventBus(),
    services: {},
    debug,
  };
  // define shortcut properties coming from some services
  Object.defineProperty(env, "isSmall", {
    get() {
      if (!env.services.device) {
        throw new Error("Device service not initialized!");
      }
      return env.services.device.isSmall;
    },
  });
  Object.defineProperty(env, "_t", {
    get() {
      if (!env.services.localization) {
        throw new Error("Localization service not initialized!");
      }
      return env.services.localization._t;
    },
  });
  Object.defineProperty(env.qweb, "translateFn", {
    get() {
      if (!env.services.localization) {
        throw new Error("Localization service not initialized!");
      }
      return env.services.localization._t;
    },
  });
  await deployServices(env);
  return env;
}
export function makeRAMLocalStorage() {
  let store = {};
  return {
    setItem(key, value) {
      store[key] = value;
    },
    getItem(key) {
      return store[key];
    },
    clear() {
      store = {};
    },
    removeItem(key) {
      delete store[key];
    },
    get length() {
      return Object.keys(store).length;
    },
    key() {
      return "";
    },
  };
}
