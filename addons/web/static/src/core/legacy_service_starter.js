/**
 * @todo owl3 migration
 * temporary - to remove when all service are converted
 */

import { onWillDestroy, onWillStart, Plugin, t, useScope } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { SERVICES_METADATA } from "@web/core/utils/hooks";
import { useChildEnv } from "@web/owl2/utils";

const serviceRegistry = registry.category("services");

serviceRegistry.addValidation(
    t.object({
        start: t.function(),
        dependencies: t.array(t.string()).optional(),
        async: t.or([t.literal(true), t.array(t.string())]).optional(),
    })
);

let startServicesPromise = null;

/**
 * Start all services registered in the service registry, while making sure
 * each service dependencies are properly fulfilled.
 *
 * @param {OdooEnv} env
 * @returns {Promise<void>}
 */
export async function startServices(env, runScope) {
    // Wait for all synchronous code so that if new services that depend on
    // one another are added to the registry, they're all present before we
    // start them regardless of the order they're added to the registry.
    await Promise.resolve();

    // we start all plugins first (in particular the localization plugin)
    const toStart = new Map();
    serviceRegistry.addEventListener("UPDATE", async (ev) => {
        // Wait for all synchronous code so that if new services that depend on
        // one another are added to the registry, they're all present before we
        // start them regardless of the order they're added to the registry.
        await Promise.resolve();
        const { operation, key: name, value: service } = ev.detail;
        if (operation === "delete") {
            // We hardly see why it would be usefull to remove a service.
            // Furthermore we could encounter problems with dependencies.
            // Keep it simple!
            return;
        }
        if (toStart.size) {
            const namedService = Object.assign(Object.create(service), { name });
            toStart.set(name, namedService);
        } else {
            await _startServices(env, toStart, runScope);
        }
    });
    await _startServices(env, toStart, runScope);
}

async function _startServices(env, toStart, runScope) {
    if (startServicesPromise) {
        return startServicesPromise.then(() => _startServices(env, toStart, runScope));
    }
    const services = env.services;
    for (const [name, service] of serviceRegistry.getEntries()) {
        if (!(name in services)) {
            const namedService = Object.assign(Object.create(service), { name });
            toStart.set(name, namedService);
        }
    }

    // start as many services in parallel as possible
    async function start() {
        let service = null;
        const proms = [];
        runScope(() => {
            while ((service = findNext())) {
                const name = service.name;
                toStart.delete(name);
                const entries = (service.dependencies || []).map((dep) => [dep, services[dep]]);
                const dependencies = Object.fromEntries(entries);
                if (name in services) {
                    continue;
                }
                const value = service.start(env, dependencies);
                if ("async" in service) {
                    SERVICES_METADATA[name] = service.async;
                }
                proms.push(
                    Promise.resolve(value).then((val) => {
                        services[name] = val || null;
                    })
                );
            }
        });
        await Promise.all(proms);
        if (proms.length) {
            return start();
        }
    }
    startServicesPromise = start().finally(() => {
        startServicesPromise = null;
    });
    await startServicesPromise;
    if (toStart.size) {
        const missingDeps = new Set();
        for (const service of toStart.values()) {
            for (const dependency of service.dependencies) {
                if (!(dependency in services) && !toStart.has(dependency)) {
                    missingDeps.add(dependency);
                }
            }
        }
        const depNames = [...missingDeps].join(", ");
        throw new Error(
            `Some services could not be started: ${[
                ...toStart.keys(),
            ]}. Missing dependencies: ${depNames}`
        );
    }

    function findNext() {
        for (const s of toStart.values()) {
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

export class LegacyServiceStarterPlugin extends Plugin {
    static sequence = 100; // start legacy services after all the other plugins.

    scope = useScope();
    env = useChildEnv();

    setup() {
        const runScope = this.scope.run.bind(this.scope);
        onWillStart(() => startServices(this.env, runScope));
        onWillDestroy(() => registry.category("services").trigger("CLEANUP"));
    }
}
services.add(LegacyServiceStarterPlugin);
