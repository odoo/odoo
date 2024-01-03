/** @odoo-module */

import { after, registerDebugInfo } from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
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

/**
 * TODO: remove when services do not have side effects anymore
 * This forsaken block of code ensures that all are properly cleaned up after each
 * test because they were populated during the starting process of some services.
 *
 * @param {typeof registry} registry
 */
const __monitorRegistry = (registry) => {
    const added = new Set();
    const removed = new Map();

    const off = on(registry, "UPDATE", ({ detail: { operation, key, value } }) => {
        if (operation === "add") {
            added.add(key);
        } else if (operation === "remove" && !removed.has(key)) {
            removed.set(key, value);
        }
    });

    after(() => {
        off();
        for (const key of added) {
            registry.remove(key);
        }
        for (const [key, value] of removed) {
            registry.add(key, value);
        }
    });
    for (const subRegistry of Object.values(registry.subRegistries)) {
        __monitorRegistry(subRegistry);
    }
};

/** @type {OdooEnv | null} */
let currentEnv = null;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

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
export async function makeMockEnv(partialEnv) {
    if (currentEnv) {
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

    __monitorRegistry(registry);
    await startServices(currentEnv);

    after(() => (currentEnv = null));

    return currentEnv;
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
