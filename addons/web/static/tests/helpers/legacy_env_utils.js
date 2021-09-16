/** @odoo-module */

import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { patch, unpatch } from "@web/core/utils/patch";
import { makeLegacyDialogMappingService } from "@web/legacy/utils";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import core from "web.core";
import makeTestEnvironment from "web.test_env";
import { registerCleanup } from "./cleanup";
import { makeTestEnv } from "./mock_env";
import { patchWithCleanup } from "./utils";
import * as FavoriteMenu from "web.FavoriteMenu";
import * as CustomFavoriteItem from "web.CustomFavoriteItem";

const serviceRegistry = registry.category("services");

export async function makeLegacyDialogMappingTestEnv() {
    const coreBusListeners = [];
    patch(core.bus, "legacy.core.bus.listeners", {
        on(eventName, thisArg, callback) {
            this._super(...arguments);
            coreBusListeners.push({ eventName, callback });
        },
    });

    const legacyEnv = makeTestEnvironment({ bus: core.bus });
    serviceRegistry.add("ui", uiService);
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("legacy_dialog_mapping", makeLegacyDialogMappingService(legacyEnv));

    const env = await makeTestEnv();

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

function clearLegacyRegistryWithCleanup(r) {
    const patch = {
        // To improve? Initial data in registry is ignored.
        map: Object.create(null),
        // Preserve onAdd listeners
        listeners: [...r.listeners],
        _scoreMapping: Object.create(null),
        _sortedKeys: null,
    };
    patchWithCleanup(r, patch);
}

export function prepareLegacyRegistriesWithCleanup() {
    // Clear FavoriteMenu registry and add the "Save favorite" item.
    clearLegacyRegistryWithCleanup(FavoriteMenu.registry);
    FavoriteMenu.registry.add("favorite-generator-menu", CustomFavoriteItem, 0);
}
