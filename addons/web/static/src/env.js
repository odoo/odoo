import { registry } from "./core/registry";
import { getTemplate } from "@web/core/templates";
import { App, EventBus } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

/**
 * @typedef {Object} OdooEnv
 * @property {import("services").Services} services
 * @property {EventBus} bus
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
        bus: new EventBus(),
        services: {},
        debug: odoo.debug,
        get isSmall() {
            throw new Error("UI service not initialized!");
        },
    };
}

// -----------------------------------------------------------------------------
// Service Launcher
// -----------------------------------------------------------------------------

const serviceRegistry = registry.category("services");

serviceRegistry.addValidation({
    start: Function,
    dependencies: { type: Array, element: String, optional: true },
    async: { type: [{ type: Array, element: String }, { value: true }], optional: true },
    "*": true,
});

export const SERVICES_METADATA = {};
let startServicesPromise = null;

/**
 * Start all services registered in the service registry, while making sure
 * each service dependencies are properly fulfilled.
 *
 * @param {OdooEnv} env
 * @returns {Promise<void>}
 */
export async function startServices(env) {
    // Wait for all synchronous code so that if new services that depend on
    // one another are added to the registry, they're all present before we
    // start them regardless of the order they're added to the registry.
    await Promise.resolve();

    const toStart = new Set();
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
            toStart.add(namedService);
        } else {
            await _startServices(env, toStart);
        }
    });
    await _startServices(env, toStart);
}

async function _startServices(env, toStart) {
    if (startServicesPromise) {
        return startServicesPromise.then(() => _startServices(env, toStart));
    }
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
            const name = service.name;
            toStart.delete(service);
            const entries = (service.dependencies || []).map((dep) => [dep, services[dep]]);
            const dependencies = Object.fromEntries(entries);
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
        for (const s of toStart) {
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

/**
 * Create an application with a given component as root and mount it. If no env
 * is provided, the application will be treated as a "root": an env will be
 * created and the services will be started, it will also be set as the root
 * in `__WOWL_DEBUG__`
 *
 * @param {import("@odoo/owl").Component} component the component to mount
 * @param {HTMLElement} target the HTML element in which to mount the app
 * @param {Partial<ConstructorParameters<typeof App>[1]>} [appConfig] object
 *  containing a (partial) config for the app.
 */
export async function mountComponent(component, target, appConfig = {}) {
    let { env } = appConfig;
    const isRoot = !env;
    if (isRoot) {
        env = await makeEnv();
        await startServices(env);
    }
    const app = new App(component, {
        env,
        getTemplate,
        dev: env.debug || session.test_mode,
        warnIfNoStaticProps: !session.test_mode,
        name: component.constructor.name,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
        ...appConfig,
    });
    const root = await app.mount(target);
    if (isRoot) {
        odoo.__WOWL_DEBUG__ = { root };
    }
    return app;
}
