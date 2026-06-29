import { after, afterEach, animationFrame, beforeEach, registerDebugInfo } from "@odoo/hoot";
import { App } from "@odoo/owl";
import { startRouter } from "@web/core/browser/router";
import { createDebugContext } from "@web/core/debug/debug_context";
import { appTranslateFn } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { getTemplate } from "@web/core/templates";
import { pick } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
import { customDirectives, globalValues, makeEnv, startServices } from "@web/env";
import { MockServer, makeMockServer, onRpc } from "./mock_server/mock_server";
import { patchWithCleanup } from "./patch_test_helpers";

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

function cleanupMockEnvs() {
    registry.category("services").trigger("CLEANUP");
    currentEnvs.length = 0;
}

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
/** @type {OdooEnv[]} */
const currentEnvs = [];
/**
 * Current main test App instance. It is assigned via a patch of `App.apps.set`
 * becaue the app can be instantiated either from the test helpers, or by the production
 * code itself. As the latter cannot be tracked by a direct 'App.constructor' patch,
 * the 'apps' set is used to track the active app.
 * @type {App | null}
 */
let currentApp = null;

// Registers all registries for cleanup in all tests
beforeEach(function registerMainRegistryForCleanup() {
    registerRegistryForCleanup(registry);
});
afterEach(function restoreMainRegistry() {
    restoreRegistry(registry);
});

patchWithCleanup(App.apps, {
    add(app) {
        if (!currentApp) {
            currentApp = app;
            registerDebugInfo("app", app);
        }
        after(() => destroyApp(app));
        return super.add(app);
    },
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @deprecated
 * @param {OdooEnv} env
 * @param {App} app
 */
export function assignEnvToApp(env, app) {
    if (!app.env === env) {
        return;
    }
    app.env = env;
    app.pluginManager.config.env = env;
    const envPluginInstance = app.pluginManager.getPluginById("__ENV__");
    if (envPluginInstance) {
        envPluginInstance.env = env;
    }
}

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

/**
 * @param {App} [app]
 */
export function destroyApp(app = currentApp) {
    if (app && !app.destroyed) {
        app.destroy();
    }
    if (app === currentApp) {
        currentApp = null;
    }
}

export function getMockEnv() {
    return currentEnvs[0];
}

/**
 * @template {keyof Services} T
 * @param {T} name
 * @returns {Services[T]}
 */
export function getService(name) {
    return currentEnvs[0]?.services[name];
}

/**
 * @param {{
 *  makeNew?: boolean;
 *  name?: string;
 * }} [options]
 */
export function getTestApp(options) {
    if (currentApp && !options?.makeNew) {
        if (options?.name) {
            currentApp.name = options.name;
        }
        return currentApp;
    }
    return new App({
        customDirectives,
        dev: false,
        getTemplate,
        globalValues,
        name: options?.name || "TEST",
        plugins: services,
        test: true,
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
    });
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
    const isFirstEnv = !currentEnvs.length;
    if (!isFirstEnv && !options?.makeNew) {
        throw new Error(
            `cannot create mock environment: a mock environment has already been declared`
        );
    }

    if (!MockServer.current) {
        await makeMockServer();
    }

    const app = getTestApp(options);
    const env = makeEnv();
    Object.assign(env, partialEnv, createDebugContext(env)); // This is needed if the views are in debug mode

    assignEnvToApp(env, app);

    if (isFirstEnv) {
        startRouter();
    }
    currentEnvs.push(env);

    await startServices(env, app);

    if (isFirstEnv) {
        // Cleanup needs to be added *after* the services have been started: this
        // is because it will trigger a "CLEANUP" event that needs to be applied
        // *before* removing the event listeners that have been setup and will be
        // torn down in plugins/services.
        after(cleanupMockEnvs);
    }

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
 *  (env: OdooEnv, dependencies: Dependencies) => Services[T]
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
        { force: true }
    );

    // Patch already initialized service
    for (const env of currentEnvs) {
        if (env.services?.[name]) {
            if (typeof serviceFactory === "function") {
                const dependencies = pick(env.services, ...(originalService.dependencies || []));
                env.services[name] = serviceFactory(env, dependencies);
            } else {
                patch(env.services[name], serviceFactory);
            }
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

/**
 * Makes a function to set Offline all RPCs and set Offline the service.
 */
export function mockOffline() {
    /**
     * @param {boolean} offline
     */
    function setOffline(offline) {
        _offline = offline;
        getService("offline").offline = _offline;
        return animationFrame();
    }

    let _offline = false;
    onRpc("/*", () => {
        if (_offline) {
            return new Response("", { status: 502 });
        }
    });

    return setOffline;
}
