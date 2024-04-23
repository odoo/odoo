// ! WARNING: this module cannot depend on modules defined in "@web" !

import { after, before, describe, dryRun, globals, start } from "@odoo/hoot";
import { watchKeys } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";

import { mockBrowserFactory } from "./mock_browser.hoot";
import { CONFIG_SUFFIX, TEST_SUFFIX } from "./mock_module_loader";
import { mockSessionFactory } from "./mock_session.hoot";
import { makeTemplateFactory } from "./mock_templates.hoot";
import { mockUserFactory } from "./mock_user.hoot";

/**
 * @typedef {{
 *  addons?: Iterable<string>;
 *  mocks?: Record<string, any>;
 * }} ModuleSetParams
 */

const { fetch: realFetch } = globals;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {string[]} moduleNames
 */
const fetchDependencies = async (moduleNames) => {
    const addons = new Set(moduleNames.map(getAddonName));
    addons.delete("odoo");
    addons.delete("web");

    // Fetch missing dependencies
    const addonsToFetch = [...addons].filter((addon) => !dependencyCache[addon]);
    if (addonsToFetch.length) {
        const allDependencies = await orm("ir.module.module.dependency", "all_dependencies", [], {
            module_names: addonsToFetch,
        });
        for (const [moduleName, dependencyNames] of Object.entries(allDependencies)) {
            if (!dependencyCache[moduleName]) {
                dependencyCache[moduleName] = [];
            }
            for (const dependencyName of dependencyNames) {
                dependencyCache[moduleName].push(dependencyName);
            }
        }
    }

    // Add default and cached dependencies
    addons.add("odoo");
    addons.add("web");
    for (const addon of addons) {
        for (const dependency of dependencyCache[addon] || []) {
            addons.add(dependency);
        }
    }

    return addons;
};

/**
 * @param {string} name
 */
const getAddonName = (name) =>
    name.startsWith("@") ? name.split("/", 1)[0].slice(1) : name.split(".", 1)[0];

/**
 * @param {string} name
 */
const getBaseName = (name) => {
    if (name.endsWith(CONFIG_SUFFIX)) {
        return name.slice(0, -CONFIG_SUFFIX.length);
    } else if (name.endsWith(TEST_SUFFIX)) {
        return name.slice(0, -TEST_SUFFIX.length);
    } else {
        return name;
    }
};

/**
 * @param {string} name
 */
const getSuitePath = (name) => name.replace("../tests/", "");

/**
 * Returns the list of module names to load for a given list of addons.
 * These name lists are cached for each combination of addons.
 *
 * @param  {Iterable<string>} addons
 */
const getModuleNames = (addons) => {
    const addonsList = [...addons];
    const key = addonsList.sort().join(",");
    if (!moduleNamesCache[key]) {
        moduleNamesCache[key] = sortedModuleNames.filter(
            (name) => !name.endsWith(TEST_SUFFIX) && addonsList.includes(getAddonName(name))
        );
    }
    return moduleNamesCache[key];
};

/**
 * Keeps the original definition of a factory.
 *
 * @param {string} name
 */
const makeFixedFactory = (name) => {
    return () => {
        if (!loader.modules.has(name)) {
            loader.startModule(name);
        }
        return loader.modules.get(name);
    };
};

/**
 * Toned-down version of the RPC + ORM features since this file cannot depend on
 * them.
 *
 * @param {string} model
 * @param {string} method
 * @param {any[]} args
 * @param {Record<string, any>} kwargs
 */
const orm = async (model, method, args, kwargs) => {
    const response = await realFetch(`/web/dataset/call_kw/${model}/${method}`, {
        body: JSON.stringify({
            id: nextRpcId++,
            jsonrpc: "2.0",
            method: "call",
            params: { args, kwargs, method, model },
        }),
        headers: {
            "Content-Type": "application/json",
        },
        method: "POST",
    });
    const { error, result } = await response.json();
    if (error) {
        throw error;
    }
    return result;
};

const runTests = async () => {
    // Sort modules to accelerate loading time
    /** @type {Record<string, Deferred>} */
    const defs = {};
    const nonLoaded = new Map();
    for (const [name, { deps }] of loader.factories) {
        nonLoaded.set(name, deps);
        const [modDef, ...depDefs] = [name, ...deps].map((dep) => (defs[dep] ||= new Deferred()));
        Promise.all(depDefs).then(() => {
            sortedModuleNames.push(name);
            modDef.resolve();
            nonLoaded.delete(name);
        });
    }

    let timeout;
    await Promise.race([
        Promise.all(Object.values(defs)),
        new Promise((resolve, reject) => {
            timeout = setTimeout(
                () =>
                    reject(
                        [
                            `Missing dependencies:`,
                            ...new Set(
                                [...nonLoaded].flatMap(([name, deps]) =>
                                    deps.filter((d) => !sortedModuleNames.includes(d))
                                )
                            ),
                        ].join("\n")
                    ),
                1000
            );
        }),
    ]);
    clearTimeout(timeout);

    const testModuleNames = [...loader.factories.keys()].filter(
        (name) =>
            name.endsWith(TEST_SUFFIX) && !loader.factories.has(getBaseName(name) + CONFIG_SUFFIX)
    );

    // Dry run
    const { suites } = await dryRun(() => describeSuite(testModuleNames));

    // Run all test files
    const suitePaths = suites.map((s) => s.fullName);
    await Promise.all(
        testModuleNames.map(async (moduleName) => {
            const path = getSuitePath(getBaseName(moduleName));
            if (suitePaths.includes(path)) {
                await describeSuite([moduleName], {});
            }
        })
    );

    // Start test runner
    await start({ auto: true });
};

const DEFAULT_MOCKS = {
    // Fixed modules
    "@web/core/template_inheritance": makeFixedFactory,
    "web.assets_unit_tests_setup.bundle.xml": makeFixedFactory,
    "im_livechat.embed_assets_unit_tests_setup.bundle.xml": makeFixedFactory,
    // Other mocks
    "@web/core/browser/browser": mockBrowserFactory,
    "@web/core/templates": makeTemplateFactory,
    "@web/core/user": mockUserFactory,
    "@web/session": mockSessionFactory,
};

const dependencyCache = {};
const { loader } = odoo;
/** @type {Set<string>} */
const modelsToFetch = new Set();
/** @type {Record<string, string[]>} */
const moduleNamesCache = {};
/** @type {Map<string, Record<string, any>>} */
const serverModelCache = new Map();
/** @type {string[]} */
const sortedModuleNames = [];
let nextRpcId = 1e9;

// Invoke tests after the module loader finished loading.
queueMicrotask(runTests);

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Iterable<string>} entryPoints
 * @param {ModuleSetParams} [params]
 */
export async function defineModuleSet(entryPoints, params) {
    const addons = await fetchDependencies(entryPoints);
    if (params?.addons) {
        for (const addon of params.addons) {
            addons.add(addon);
        }
    }
    const mocks = { ...DEFAULT_MOCKS, ...params?.mocks };

    const checkKeys = watchKeys(window);

    const moduleNames = getModuleNames(new Set(addons));
    /** @type {typeof odoo.loader} */
    const subLoader = new loader.constructor();
    for (const name of moduleNames) {
        if (name in mocks) {
            // Use mock
            const originalFactory = loader.factories.get(name);
            subLoader.factories.set(name, {
                deps: [],
                fn: mocks[name](name, originalFactory),
            });
            subLoader.startModule(name);
        } else if (loader.modules.has(name)) {
            // Keep the original instance
            subLoader.modules.set(name, loader.modules.get(name));
        } else {
            // Run (or re-run) module factory
            subLoader.factories.set(name, loader.factories.get(name));
            subLoader.startModule(name);
        }
    }

    checkKeys(true);

    return { addons, moduleNames, subLoader };
}

/**
 * @param {Iterable<string>} entryPoints
 * @param {ModuleSetParams} [params]
 */
export async function describeSuite(entryPoints, params) {
    const entryModuleNames = [...entryPoints].map((name) => {
        if (!name.endsWith(TEST_SUFFIX) && !name.endsWith(CONFIG_SUFFIX)) {
            throw new Error(
                `cannot start suite for module "${name}": module name must end with "${TEST_SUFFIX}" or "${CONFIG_SUFFIX}"`
            );
        }
        return getBaseName(name);
    });

    const { addons, subLoader } = await defineModuleSet(entryPoints, params);

    /**
     * @param {string} url
     */
    const filterTemplateUrl = (url) => addons.has(url.split("/")[1]);

    for (const moduleName of entryModuleNames) {
        const testModuleName = moduleName + TEST_SUFFIX;
        subLoader.factories.set(testModuleName, loader.factories.get(testModuleName));

        // Run test factory
        describe(getSuitePath(moduleName), () => {
            const { clearProcessedTemplates, setUrlFilters } =
                subLoader.modules.get("@web/core/templates");

            before(() => {
                odoo.loader = subLoader;
                odoo.define = subLoader.define.bind(subLoader);
                setUrlFilters([filterTemplateUrl]);
            });

            after(() => {
                setUrlFilters([]);
                clearProcessedTemplates();
            });

            subLoader.startModule(testModuleName);
        });
    }
}

export function clearServerModelCache() {
    serverModelCache.clear();
}

/**
 * @param {Iterable<string>} modelNames
 */
export async function fetchModelDefinitions(modelNames) {
    // Fetch missing definitions
    const namesList = [...modelsToFetch];
    if (namesList.length) {
        const formData = new FormData();
        formData.set("csrf_token", odoo.csrf_token);
        formData.set("model_names", JSON.stringify(namesList));

        const response = await realFetch("/web/model/get_definitions", {
            body: formData,
            method: "POST",
        });
        if (!response.ok) {
            const [s, some, does] =
                namesList.length === 1 ? ["", "this", "does"] : ["s", "some or all of these", "do"];
            const message = `could not fetch definition${s} for server model${s} "${namesList.join(
                `", "`
            )}": ${some} model${s} ${does} not exist`;
            throw new Error(message);
        }
        const modelDefs = await response.json();

        for (const [modelName, modelDef] of Object.entries(modelDefs)) {
            serverModelCache.set(modelName, modelDef);
            modelsToFetch.delete(modelName);
        }
    }

    return [...modelNames].map((modelName) => [modelName, serverModelCache.get(modelName)]);
}

/**
 * @param {string} modelName
 */
export function registerModelToFetch(modelName) {
    if (!serverModelCache.has(modelName)) {
        modelsToFetch.add(modelName);
    }
}
