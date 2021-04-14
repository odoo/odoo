/** @odoo-module **/

import { browser } from "@web/core/browser";
import { debugRegistry } from "@web/debug/debug_registry";
import ToursDialog from "@web_tour/debug/tour_dialog_component";
import utils from "web_tour.utils";

function debugDisableTourItem(env) {
  if (!env.services.user.isSystem) {
    return {};
  }
  const activeTours = env.services.tour.getActiveTours();
  if (activeTours.length === 0) {
    return {};
  }
  return {
    type: "item",
    description: env._t("Disable Tours"),
    callback: async () => {
      await env.services.orm.call("web_tour.tour", "consume", [activeTours]);
      for (const tourName of activeTours) {
        browser.localStorage.removeItem(utils.get_debugging_key(tourName));
      }
      browser.location.reload();
    },
    sequence: 33,
  };
}

function debugStartTourItem(env) {
  if (!env.services.user.isSystem) {
    return {};
  }
  return {
    type: "item",
    description: env._t("Start Tour"),
    callback: async () => {
      env.services.dialog.open(ToursDialog);
    },
    sequence: 32,
  };
}

debugRegistry.add("web_tour.start_tour", debugStartTourItem);
debugRegistry.add("web_tour.disable_tour", debugDisableTourItem);
