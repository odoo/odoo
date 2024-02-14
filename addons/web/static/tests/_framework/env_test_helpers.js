import { after, registerDebugInfo } from "@odoo/hoot";
import { startRouter } from "@web/core/browser/router";
import { createDebugContext } from "@web/core/debug/debug_context";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { MockServer, makeMockServer } from "./mock_server/mock_server";

/**
 * @typedef {import("@web/env").OdooEnv} OdooEnv
 *
 * @typedef {import("services").Services} Services
 */

//-----------------------------------------------------------------------------
// Internals
//-----------------------------------------------------------------------------

const toRestoreRegistry = new WeakMap();

export function restoreRegistryFromBeforeTest(registry, { withSubRegistries = false } = {}) {
    const content = toRestoreRegistry.get(registry);
    toRestoreRegistry.delete(registry);
    if (content) {
        registry.content = Object.fromEntries(content);
        registry.elements = null;
        registry.entries = null;
    }
    if (withSubRegistries) {
        for (const subRegistry of Object.values(registry.subRegistries)) {
            restoreRegistryFromBeforeTest(subRegistry);
        }
    }
}

/**
 * TODO: remove when services do not have side effects anymore
 * This forsaken block of code ensures that all are properly cleaned up after each
 * test because they were populated during the starting process of some services.
 *
 * @param {typeof registry} registry
 */
const restoreRegistryAfterTest = (registry) => {
    const content = Object.entries(registry.content).map(([key, value]) => [key, value.slice()]);
    toRestoreRegistry.set(registry, content);
    after(() => {
        restoreRegistryFromBeforeTest(registry);
    });
    for (const subRegistry of Object.values(registry.subRegistries)) {
        restoreRegistryAfterTest(subRegistry);
    }
};

/** @type {OdooEnv | null} */
let currentEnv = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Empties the given registry.
 *
 * @param {import("@web/core/registry").Registry} registry
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
    restoreRegistryAfterTest(registry);

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
