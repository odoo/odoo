import { after, afterEach, beforeEach, registerDebugInfo } from "@odoo/hoot";
import { startRouter } from "@web/core/browser/router";
import { createDebugContext } from "@web/core/debug/debug_context";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { MockServer, makeMockServer } from "./mock_server/mock_server";

/**
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 *
 * @typedef {import("@web/core/registry").Registry} Registry
 *
 * @typedef {import("services").Services} Services
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
    const content = Object.entries(registry.content).map(([key, value]) => [key, value.slice()]);
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
 */
export async function makeMockEnv(partialEnv, { makeNew = false } = {}) {
    if (currentEnv && !makeNew) {
        throw new Error(
            `cannot create mock environment: a mock environment has already been declared`
        );
    }

    if (!MockServer.current) {
        await makeMockServer();
    }

    currentEnv = makeEnv();
    Object.assign(currentEnv, partialEnv, createDebugContext(currentEnv)); // This is needed if the views are in debug mode

    registerDebugInfo(currentEnv);

    startRouter();
    await startServices(currentEnv);

    after(() => (currentEnv = null));

    return currentEnv;
}

/**
 * Makes a mock environment for dialog tests
 *
 * @param {Partial<OdooEnv>} [partialEnv]
 * @returns {Promise<OdooEnv>}
 */
export async function makeDialogMockEnv(partialEnv) {
    return makeMockEnv({
        dialogData: {
            close: () => {},
            isActive: true,
            scrollToOrigin: () => {},
        },
        ...partialEnv,
    });
}

/**
 * @template {keyof Services} T
 * @param {T} name
 * @param {(env: OdooEnv, dependencies: Record<keyof Services, any>) => Services[T]} serviceFactory
 */
export function mockService(name, serviceFactory) {
    const serviceRegistry = registry.category("services");
    const originalService = serviceRegistry.get(name, null);
    serviceRegistry.add(name, { start: serviceFactory }, { force: true });
    if (originalService) {
        after(() => serviceRegistry.add(name, originalService, { force: true }));
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
