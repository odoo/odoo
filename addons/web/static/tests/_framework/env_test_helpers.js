// @ts-check

import { after, afterEach, beforeEach, registerDebugInfo } from "@odoo/hoot";
import { startRouter } from "@web/core/browser/router";
import {
    translatedTerms,
    translatedTermsGlobal,
    translationLoaded,
} from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/collections/objects";
import { patch } from "@web/core/utils/patch";
import { makeEnv, startServices } from "@web/env";
import { createDebugContext } from "@web/services/debug/debug_context";

import { makeMockServer, MockServer } from "./mock_server/mock_server";

/**
 * @typedef {Record<keyof Services, any>} Dependencies
 *
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 *
 * @typedef {import("@web/core/registry").Registry} Registry
 *
 * @typedef {import("services").ServiceFactories} Services
 */

//-----------------------------------------------------------------------------
// Internals
//-----------------------------------------------------------------------------

/**
 * TODO: remove when services do not have side effects anymore
 * This forsaken block of code ensures that all are properly cleaned up after each
 * test because they were populated during the starting process of some services.
 *
 * @param {Registry} registry
 */
const registerRegistryForCleanup = (registry) => {
    const content = Object.entries(registry.content).map(([key, value]) => [
        key,
        value.slice(),
    ]);
    registriesContent.set(registry, content);

    for (const subRegistry of Object.values(registry.subRegistries)) {
        registerRegistryForCleanup(subRegistry);
    }
};

const registriesContent = new WeakMap();
/** @type {OdooEnv | null} */
let currentEnv = null;

// Registers all registries for cleanup in all tests
beforeEach(() => registerRegistryForCleanup(registry));
afterEach(() => restoreRegistry(registry));

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Empties the given registry.
 *
 * @param {Registry} registry
 */
export function clearRegistry(registry) {
    registry.content = {};
    registry.elements = null;
    registry.entries = null;
}

export function getMockEnv() {
    return currentEnv;
}

/**
 * @template {keyof Services} T
 * @param {T} name
 * @returns {Services[T]}
 */
export function getService(name) {
    return currentEnv.services[name];
}

/**
 * Makes a mock environment along with a mock server
 *
 * @param {Partial<OdooEnv>} [partialEnv]
 * @param {{
 *  makeNew?: boolean;
 * }} [options]
 */
export async function makeMockEnv(partialEnv, options) {
    if (currentEnv && !options?.makeNew) {
        throw new Error(
            `cannot create mock environment: a mock environment has already been declared`,
        );
    }

    if (!MockServer.current) {
        await makeMockServer();
    }

    const env = makeEnv();
    Object.assign(env, partialEnv, createDebugContext(/** @type {any} */ (env))); // This is needed if the views are in debug mode

    registerDebugInfo("env", env);

    if (!currentEnv) {
        currentEnv = env;
        startRouter();
        after(() => {
            currentEnv = null;

            // Ideally: should be done in a patch of the localization service, but this
            // is less intrusive for now.
            if (translatedTerms[translationLoaded]) {
                for (const key in translatedTerms) {
                    delete translatedTerms[key];
                }
                for (const key in translatedTermsGlobal) {
                    delete translatedTermsGlobal[key];
                }
                translatedTerms[translationLoaded] = false;
            }
        });
    }

    await startServices(env);

    return env;
}

/**
 * Makes a mock environment for dialog tests
 *
 * @param {Partial<OdooEnv>} [partialEnv]
 * @returns {Promise<OdooEnv>}
 */
export async function makeDialogMockEnv(partialEnv) {
    return makeMockEnv({
        ...partialEnv,
        dialogData: {
            close: () => {},
            isActive: true,
            scrollToOrigin: () => {},
            ...partialEnv?.dialogData,
        },
    });
}

/**
 * @template {keyof Services} T
 * @param {T} name
 * @param {Partial<Services[T]> |
 *  ((env: OdooEnv, dependencies: Dependencies) => Services[T])
 * } serviceFactory
 */
export function mockService(name, serviceFactory) {
    const serviceRegistry = registry.category("services");
    const originalService = serviceRegistry.get(name, null);
    serviceRegistry.add(
        name,
        {
            ...originalService,
            start(env, dependencies) {
                if (typeof serviceFactory === "function") {
                    return serviceFactory(env, dependencies);
                } else {
                    const service = originalService.start(env, dependencies);
                    if (service instanceof Promise) {
                        service.then((value) => patch(value, serviceFactory));
                    } else {
                        patch(service, serviceFactory);
                    }
                    return service;
                }
            },
        },
        { force: true },
    );

    // Patch already initialized service
    if (currentEnv?.services?.[name]) {
        if (typeof serviceFactory === "function") {
            const dependencies = pick(
                currentEnv.services,
                .../** @type {any[]} */ (originalService.dependencies || []),
            );
            /** @type {any} */ (currentEnv.services)[name] = serviceFactory(
                currentEnv,
                /** @type {any} */ (dependencies),
            );
        } else {
            patch(currentEnv.services[name], serviceFactory);
        }
    }
}

/**
 * @param {Registry} registry
 */
export function restoreRegistry(registry) {
    if (registriesContent.has(registry)) {
        clearRegistry(registry);

        registry.content = Object.fromEntries(registriesContent.get(registry));
    }

    for (const subRegistry of Object.values(registry.subRegistries)) {
        restoreRegistry(subRegistry);
    }
}
