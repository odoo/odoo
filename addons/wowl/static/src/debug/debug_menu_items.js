/** @odoo-module **/

import { browser } from "../core/browser";
import { routeToUrl } from "../services/router_service";
import { debugRegistry } from "./debug_registry";

// Backend Debug Manager Items
export function runJSTestsItem(env) {
  const runTestsURL = browser.location.origin + "/wowl/tests?mod=*";
  return {
    type: "item",
    description: env._t("Run JS Tests"),
    href: runTestsURL,
    callback: () => {
      browser.open(runTestsURL);
    },
    sequence: 10,
  };
}

export function runJSTestsMobileItem(env) {
  const runTestsMobileURL = browser.location.origin + "/wowl/tests/mobile?mod=*";
  return {
    type: "item",
    description: env._t("Run JS Mobile Tests"),
    href: runTestsMobileURL,
    callback: () => {
      browser.open(runTestsMobileURL);
    },
    sequence: 20,
  };
}

export function runClickTestItem(env) {
  return {
    type: "item",
    description: env._t("Run Click Everywhere Test"),
    callback: () => {
      console.log("Run Click Everywhere Test");
      // TODO need to imp ?
      // perform_click_everywhere_test
    },
    sequence: 30,
  };
}

export function openViewItem(env) {
  return {
    type: "item",
    description: env._t("Open View"),
    callback: () => {
      console.log("Open View");
      // select_view
      // disable_multiple_selection don't work
      // Need to add SelectCreateDialog and SelectCreateListController
    },
    sequence: 40,
  };
}

// Global Debug Manager Items
export function globalSeparator(env) {
  return {
    type: "separator",
    sequence: 400,
  };
}

export function activateAssetsDebugging(env) {
  return {
    type: "item",
    description: env._t("Activate Assets Debugging"),
    callback: () => {
      browser.location.search = "?debug=assets";
    },
    sequence: 410,
  };
}

export function activateTestsAssetsDebugging(env) {
  return {
    type: "item",
    description: env._t("Activate Tests Assets Debugging"),
    callback: () => {
      browser.location.search = "?debug=assets,tests";
    },
    sequence: 420,
  };
}

export function regenerateAssets(env) {
  return {
    type: "item",
    description: env._t("Regenerate Assets Bundles"),
    callback: async () => {
      const domain = [
        "&",
        ["res_model", "=", "ir.ui.view"],
        "|",
        ["name", "=like", "%.assets_%.css"],
        ["name", "=like", "%.assets_%.js"],
      ];
      const ids = await env.services.model("ir.attachment").search(domain);
      await env.services.model("ir.attachment").unlink(ids);
      browser.location.reload();
    },
    sequence: 430,
  };
}

export function becomeSuperuser(env) {
  const becomeSuperuserULR = browser.location.origin + "/wowl/become";
  return {
    type: "item",
    description: env._t("Become Superuser"),
    hide: !env.services.user.isAdmin,
    href: becomeSuperuserULR,
    callback: () => {
      //TODO  add /wowl/become
      browser.open(becomeSuperuserULR, "_self");
    },
    sequence: 440,
  };
}

export function leaveDebugMode(env) {
  return {
    type: "item",
    description: env._t("Leave the Developer Tools"),
    callback: () => {
      const route = env.services.router.current;
      route.search.debug = "";
      browser.location.href = browser.location.origin + routeToUrl(route);
    },
    sequence: 450,
  };
}

const backendDebugManagerItems = [
  runJSTestsItem,
  runJSTestsMobileItem,
  runClickTestItem,
  openViewItem,
];

for (let item of backendDebugManagerItems) {
  debugRegistry.add(item.name, item);
}

const globalDebugManagerItems = [
  globalSeparator,
  activateAssetsDebugging,
  regenerateAssets,
  becomeSuperuser,
  leaveDebugMode,
  activateTestsAssetsDebugging,
];

for (let item of globalDebugManagerItems) {
  debugRegistry.add(item.name, item);
}
