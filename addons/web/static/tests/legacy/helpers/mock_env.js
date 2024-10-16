/** @odoo-module alias=@web/../tests/helpers/mock_env default=false */

import { SERVICES_METADATA } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { registerCleanup } from "./cleanup";
import { makeMockServer } from "./mock_server";
import { mocks } from "./mock_services";
import { patchWithCleanup } from "./utils";
import { Component } from "@odoo/owl";
import { startRouter } from "@web/core/browser/router";

function prepareRegistry(registry, keepContent = false) {
    const _addEventListener = registry.addEventListener.bind(registry);
    const _removeEventListener = registry.removeEventListener.bind(registry);
    const patch = {
        content: keepContent ? { ...registry.content } : {},
        elements: null,
        entries: null,
        subRegistries: {},
        addEventListener(type, callback) {
            _addEventListener(type, callback);
            registerCleanup(() => {
                _removeEventListener(type, callback);
            });
        },
    };
    patchWithCleanup(registry, patch);
}

export function clearRegistryWithCleanup(registry) {
    prepareRegistry(registry);
}

function cloneRegistryWithCleanup(registry) {
    prepareRegistry(registry, true);
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

export const registryNamesToCloneWithCleanup = [
    "actions",
    "command_provider",
    "command_setup",
    "error_handlers",
    "fields",
    "fields",
    "main_components",
    "view_widgets",
    "views",
];

export const utils = {
    prepareRegistriesWithCleanup() {
        // Clone registries
        registryNamesToCloneWithCleanup.forEach((registryName) =>
            cloneRegistryWithCleanup(registry.category(registryName))
        );

        // Clear registries
        clearRegistryWithCleanup(registry.category("command_categories"));
        clearRegistryWithCleanup(registry.category("debug"));
        clearRegistryWithCleanup(registry.category("error_dialogs"));
        clearRegistryWithCleanup(registry.category("favoriteMenu"));
        clearRegistryWithCleanup(registry.category("ir.actions.report handlers"));
        clearRegistryWithCleanup(registry.category("main_components"));

        clearRegistryWithCleanup(registry.category("services"));
        clearServicesMetadataWithCleanup();

        clearRegistryWithCleanup(registry.category("systray"));
        clearRegistryWithCleanup(registry.category("user_menuitems"));
        clearRegistryWithCleanup(registry.category("kanban_examples"));
        // fun fact: at least one registry is missing... this shows that we need a
        // better design for the way we clear these registries...
    },
};

// This is exported in a utils object to allow for patching
export function prepareRegistriesWithCleanup() {
    return utils.prepareRegistriesWithCleanup();
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
    startRouter();
    // add all missing dependencies if necessary
    const serviceRegistry = registry.category("services");
    const servicesToProcess = serviceRegistry.getAll();
    while (servicesToProcess.length) {
        const service = servicesToProcess.pop();
        if (service.dependencies) {
            for (const depName of service.dependencies) {
                if (depName in mocks && !serviceRegistry.contains(depName)) {
                    const dep = mocks[depName]();
                    serviceRegistry.add(depName, dep);
                    servicesToProcess.push(dep);
                }
            }
        }
    }

    if (config.serverData || config.mockRPC || config.activateMockServer) {
        await makeMockServer(config.serverData, config.mockRPC);
    }

    let env = makeEnv();
    await startServices(env);
    Component.env = env;
    if ("config" in config) {
        env = Object.assign(Object.create(env), { config: config.config });
    }
    return env;
}

/**
 * Create a test environment for dialog tests
 *
 * @param {*} config
 * @returns {Promise<OdooEnv>}
 */
export async function makeDialogTestEnv(config = {}) {
    const env = await makeTestEnv(config);
    env.dialogData = {
        isActive: true,
        close() {},
    };
    return env;
}
