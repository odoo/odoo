/** @odoo-module **/

import { registry } from "./core/registry";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef {Object} OdooEnv
 * @property {Object} services
 * @property {owl.core.EventBus} bus
 * @property {owl.QWeb} qweb
 * @property {string} debug
 * @property {(str: string) => string} _t
 * @property {boolean} [isSmall]
 */

// -----------------------------------------------------------------------------
// makeEnv
// -----------------------------------------------------------------------------

/**
 * Return a value Odoo Env object
 *
 * @returns {OdooEnv}
 */
export function makeEnv() {
    return {
        qweb: new owl.QWeb(),
        bus: new owl.core.EventBus(),
        services: {},
        debug: odoo.debug,
        _t: () => {
            throw new Error("Translations are not ready yet. Maybe use _lt instead?");
        },
        get isSmall() {
            throw new Error("UI service not initialized!");
        },
    };
}

// -----------------------------------------------------------------------------
// Service Launcher
// -----------------------------------------------------------------------------

const serviceRegistry = registry.category("services");

export const SERVICES_METADATA = {};

/**
 * Start all services registered in the service registry, while making sure
 * each service dependencies are properly fulfilled.
 *
 * @param {OdooEnv} env
 * @returns {Promise<void>}
 */
export async function startServices(env) {
    const toStart = new Set();
    serviceRegistry.on("UPDATE", null, async (payload) => {
        // Wait for all synchronous code so that if new services that depend on
        // one another are added to the registry, they're all present before we
        // start them regardless of the order they're added to the registry.
        await Promise.resolve();
        const { operation, key: name, value: service } = payload;
        if (operation === "delete") {
            // We hardly see why it would be usefull to remove a service.
            // Furthermore we could encounter problems with dependencies.
            // Keep it simple!
            return;
        }
        if (toStart.size) {
            const namedService = Object.assign(Object.create(service), { name });
            toStart.add(namedService);
        } else {
            await _startServices(env, toStart);
        }
    });
    // Wait for all synchronous code so that if new services that depend on
    // one another are added to the registry, they're all present before we
    // start them regardless of the order they're added to the registry.
    await Promise.resolve();
    await _startServices(env, toStart);
}

async function _startServices(env, toStart) {
    const services = env.services;
    for (const [name, service] of serviceRegistry.getEntries()) {
        if (!(name in services)) {
            const namedService = Object.assign(Object.create(service), { name });
            toStart.add(namedService);
        }
    }

    // start as many services in parallel as possible
    async function start() {
        let service = null;
        const proms = [];
        while ((service = findNext())) {
            let name = service.name;
            toStart.delete(service);
            const entries = (service.dependencies || []).map((dep) => [dep, services[dep]]);
            const dependencies = Object.fromEntries(entries);
            let value;
            try {
                value = service.start(env, dependencies);
            } catch (e) {
                value = e;
                console.error(e);
            }
            if ("async" in service) {
                SERVICES_METADATA[name] = service.async;
            }
            if (value instanceof Promise) {
                proms.push(
                    new Promise(async (resolve) => {
                        value
                            .then((val) => {
                                services[name] = val || null;
                            })
                            .catch((error) => {
                                services[name] = error;
                                console.error(error);
                            })
                            .finally(resolve);
                    })
                );
            } else {
                services[service.name] = value || null;
            }
        }
        await Promise.all(proms);
        if (proms.length) {
            return start();
        }
    }
    await start();
    if (toStart.size) {
        const names = [...toStart].map((s) => s.name);
        const missingDeps = new Set();
        [...toStart].forEach((s) =>
            s.dependencies.forEach((dep) => {
                if (!(dep in services) && !names.includes(dep)) {
                    missingDeps.add(dep);
                }
            })
        );
        const depNames = [...missingDeps].join(", ");
        throw new Error(
            `Some services could not be started: ${names}. Missing dependencies: ${depNames}`
        );
    }

    function findNext() {
        for (let s of toStart) {
            if (s.dependencies) {
                if (s.dependencies.every((d) => d in services)) {
                    return s;
                }
            } else {
                return s;
            }
        }
        return null;
    }
}
