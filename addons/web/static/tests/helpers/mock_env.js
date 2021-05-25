/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import FormController from "web.FormController";
import { registerCleanup } from "./cleanup";
import { makeMockServer } from "./mock_server";
import { mocks } from "./mock_services";
import { patchWithCleanup } from "./utils";

export function clearRegistryWithCleanup(registry) {
    const patch = {
        content: {},
        elements: null,
        entries: null,
        subRegistries: {},
        // Preserve OnUpdate handlers
        subscriptions: { UPDATE: [...registry.subscriptions.UPDATE] },
    };
    patchWithCleanup(registry, patch);
}

function cloneRegistryWithCleanup(registry) {
    const patch = {
        content: { ...registry.content },
        elements: null,
        entries: null,
        subRegistries: {},
        // Preserve OnUpdate handlers
        subscriptions: { UPDATE: [...registry.subscriptions.UPDATE] },
    };
    patchWithCleanup(registry, patch);
}

export function prepareRegistriesWithCleanup() {
    // Clone registries
    cloneRegistryWithCleanup(registry.category("actions"));
    cloneRegistryWithCleanup(registry.category("views"));
    cloneRegistryWithCleanup(registry.category("error_handlers"));

    cloneRegistryWithCleanup(registry.category("main_components"));

    // Clear registries
    clearRegistryWithCleanup(registry.category("command_categories"));
    clearRegistryWithCleanup(registry.category("debug"));
    clearRegistryWithCleanup(registry.category("error_dialogs"));

    clearRegistryWithCleanup(registry.category("services"));
    clearRegistryWithCleanup(registry.category("systray"));
    clearRegistryWithCleanup(registry.category("user_menuitems"));
    // fun fact: at least one registry is missing... this shows that we need a
    // better design for the way we clear these registries...
}

/**
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 */

/**
 * Create a test environment
 *
 * @param {*} config
 * @returns {Promise<OdooEnv>}
 */
export async function makeTestEnv(config = {}) {
    // add all missing dependencies if necessary
    const serviceRegistry = registry.category("services");
    for (let service of serviceRegistry.getAll()) {
        if (service.dependencies) {
            for (let dep of service.dependencies) {
                if (dep in mocks && !serviceRegistry.contains(dep)) {
                    serviceRegistry.add(dep, mocks[dep]());
                }
            }
        }
    }

    if (config.serverData || config.mockRPC || config.activateMockServer) {
        makeMockServer(config.serverData, config.mockRPC);
    }

    // remove the multi-click delay for the quick edit in form views
    // todo: move this elsewhere (setup?)
    const initialQuickEditDelay = FormController.prototype.multiClickTime;
    FormController.prototype.multiClickTime = 0;
    registerCleanup(() => {
        FormController.prototype.multiClickTime = initialQuickEditDelay;
    });

    setTestOdooWithCleanup(config);
    const env = makeEnv(odoo.debug);
    await startServices(env);
    env.qweb.addTemplates(window.__ODOO_TEMPLATES__);
    return env;
}

export function setTestOdooWithCleanup(config = {}) {
    const originalOdoo = odoo;
    registerCleanup(() => {
        odoo = originalOdoo;
    });
    odoo = Object.assign({}, originalOdoo, {
        debug: config.debug || "",
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
    });
}
