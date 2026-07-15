import {
    after,
    afterEach,
    animationFrame,
    beforeEach,
    getCurrent,
    registerDebugInfo,
} from "@odoo/hoot";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { App, Scope } from "@odoo/owl";
import { startRouter } from "@web/core/browser/router";
import { appTranslateFn } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { getTemplate } from "@web/core/templates";
import { pick } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
import { customDirectives, globalValues, makeEnv } from "@web/env";
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

class TestScope extends Scope {}

class TestApp extends App {
    test = true;
    scope = new TestScope(this);

    destroy() {
        this.scope.finalize(() => {});
        super.destroy();
    }
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
/**
 * Current main test App instance.
 * @type {TestApp | null}
 */
let currentApp = null;
let testEnv = {};

// Registers all registries for cleanup in all tests
beforeEach(function registerMainRegistryForCleanup() {
    registerRegistryForCleanup(registry);
});
afterEach(function restoreMainRegistry() {
    restoreRegistry(registry);
    clearTestEnv();
});

beforeEach(() => {
    patchWithCleanup(App.apps, {
        add(app) {
            registerDebugInfo("app", app);
            if (!(app instanceof TestApp)) {
                after(() => destroyApp(app));
            }
            return super.add(app);
        },
    });
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @deprecated
 * @param {Record<PropertyKey, any>} [dialogData]
 */
export function assignDialogTestEnv(dialogData) {
    assignTestEnv({
        dialogData: {
            close: () => {},
            isActive: true,
            scrollToOrigin: () => {},
            ...dialogData,
        },
    });
}

/**
 * @deprecated
 * @param {Record<PropertyKey, any>} env
 */
export function assignTestEnv(env) {
    Object.assign(testEnv, env);
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
 * @deprecated
 */
export function clearTestEnv() {
    testEnv = {};
}

/**
 * @param {App | null} [app]
 */
export function destroyApp(app = currentApp) {
    if (app && !app.destroyed) {
        app.destroy();
    }
    if (app === currentApp) {
        currentApp = null;
        restoreRegistry(registry);
    }
}

export function getMockEnv() {
    return currentApp?.env;
}

/**
 * Retrieves a service by its registered name, or a plugin by its class.
 *
 * Passing a string returns the matching entry from the "services" registry
 * (this includes legacy compatibility services such as "offline"). Passing a
 * plugin class returns the running instance of that plugin from the plugin
 * manager, which is the preferred way to access converted plugins in tests
 * (e.g. `getService(OfflinePlugin)` instead of `getService("offline")`).
 *
 * @overload
 * @template {keyof Services} T
 * @param {T} name service name
 * @returns {Services[T]}
 */
/**
 * @template T
 * @overload
 * @param {new (...args: any[]) => T} PluginClass plugin class
 * @returns {T}
 */
/**
 * @param {string | Function} name
 * @returns {any}
 */
export function getService(name) {
    if (typeof name === "string") {
        return getMockEnv()?.services[name];
    } else {
        return currentApp.pluginManager.getPlugin(name);
    }
}

export function getTestApp() {
    return currentApp;
}

/**
 * @param {{ forceNew?: boolean }} [options]
 */
export async function makeTestApp(options) {
    if (currentApp) {
        if (!options?.forceNew) {
            throw new Error(`cannot create test app: a test app has already been declared`);
        }
        restoreRegistry(registry);
    }

    if (!MockServer.current) {
        await makeMockServer();
    }

    if (!currentApp) {
        startRouter();
    }

    const app = new TestApp({
        customDirectives,
        dev: false,
        env: Object.assign(makeEnv(), testEnv),
        getTemplate,
        globalValues,
        name: getCurrent().test?.fullName || "TEST",
        plugins: services,
        test: true,
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
    });
    await app.pluginManager.ready;

    currentApp = app;
    after(() => destroyApp(app));

    return app;
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
    const env = getMockEnv();
    if (env?.services?.[name]) {
        if (typeof serviceFactory === "function") {
            const dependencies = pick(env.services, ...(originalService.dependencies || []));
            env.services[name] = serviceFactory(env, dependencies);
        } else {
            patch(env.services[name], serviceFactory);
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
 * @template [T=void]
 * @param {() => T} fn
 * @returns {Promise<T>}
 */
export async function runTestScope(fn) {
    const app = getTestApp() || (await makeTestApp());
    return app.scope.run(fn);
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
        getService(OfflinePlugin).setOffline(_offline);
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
