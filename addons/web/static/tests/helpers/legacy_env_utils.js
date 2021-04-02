/** @odoo-module */

import makeTestEnvironment from "web.test_env";
import core from "web.core";
import { Registry } from "@web/core/registry";
import { hotkeyService } from "@web/hotkey/hotkey_service";
import { uiService } from "@web/services/ui_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeLegacyDialogMappingService } from "@web/legacy/utils";
import { registerCleanup } from "./cleanup";
import { patch, unpatch } from "../../src/utils/patch";

export async function makeLegacyDialogMappingTestEnv() {
  const coreBusListeners = [];
  patch(core.bus, "legacy.core.bus.listeners", {
    on(eventName, thisArg, callback) {
      this._super(...arguments);
      coreBusListeners.push({ eventName, callback });
    },
  });

  const legacyEnv = makeTestEnvironment({ bus: core.bus });
  const serviceRegistry = new Registry();
  serviceRegistry.add("ui", uiService);
  serviceRegistry.add("hotkey", hotkeyService);
  serviceRegistry.add("legacy_dialog_mapping", makeLegacyDialogMappingService(legacyEnv));

  const env = await makeTestEnv({ serviceRegistry });

  registerCleanup(() => {
    for (const listener of coreBusListeners) {
      core.bus.off(listener.eventName, listener.callback);
    }
    unpatch(core.bus, "legacy.core.bus.listeners");
  });

  return {
    legacyEnv,
    env,
  };
}
