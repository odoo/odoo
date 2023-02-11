/** @odoo-module **/

import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import FormController from "web.FormController";
import { SERVICES_METADATA } from "../../src/env";
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

export function clearServicesMetadataWithCleanup() {
    const servicesMetadata = Object.assign({}, SERVICES_METADATA);
    for (const key of Object.keys(SERVICES_METADATA)) {
        delete SERVICES_METADATA[key];
    }
    registerCleanup(() => {
        for (const key of Object.keys(SERVICES_METADATA)) {
            delete SERVICES_METADATA[key];
        }
        Object.assign(SERVICES_METADATA, servicesMetadata);
    });
}

export function prepareRegistriesWithCleanup() {
    // Clone registries
    cloneRegistryWithCleanup(registry.category("actions"));
    cloneRegistryWithCleanup(registry.category("views"));
    cloneRegistryWithCleanup(registry.category("error_handlers"));
    cloneRegistryWithCleanup(registry.category("command_provider"));
    cloneRegistryWithCleanup(registry.category("view_widgets"));
    cloneRegistryWithCleanup(registry.category("fields"));

    cloneRegistryWithCleanup(registry.category("main_components"));

    // Clear registries
    clearRegistryWithCleanup(registry.category("command_categories"));
    clearRegistryWithCleanup(registry.category("debug"));
    clearRegistryWithCleanup(registry.category("error_dialogs"));
    clearRegistryWithCleanup(registry.category("favoriteMenu"));
    clearRegistryWithCleanup(registry.category("ir.actions.report handlers"));

    clearRegistryWithCleanup(registry.category("services"));
    clearServicesMetadataWithCleanup();

    clearRegistryWithCleanup(registry.category("systray"));
    clearRegistryWithCleanup(registry.category("user_menuitems"));
    clearRegistryWithCleanup(registry.category("__processed_archs__"));
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
    const servicesToProcess = serviceRegistry.getAll();
    while (servicesToProcess.length) {
        const service = servicesToProcess.pop();
        if (service.dependencies) {
            for (let depName of service.dependencies) {
                if (depName in mocks && !serviceRegistry.contains(depName)) {
                    const dep = mocks[depName]();
                    serviceRegistry.add(depName, dep);
                    servicesToProcess.push(dep);
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

    const env = makeEnv();
    env.config = config.config || {};
    await startServices(env);
    env.qweb.addTemplates(window.__ODOO_TEMPLATES__);
    return env;
}
