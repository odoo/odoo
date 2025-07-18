// ! WARNING: this module cannot depend on modules not ending with ".hoot" (except libs) !

import { describe, dryRun, globals, start, stop } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-dom";
import { watchKeys, watchListeners } from "@odoo/hoot-mock";

import { mockBrowserFactory } from "./mock_browser.hoot";
import { mockCurrencyFactory } from "./mock_currency.hoot";
import { mockSessionFactory } from "./mock_session.hoot";
import { makeTemplateFactory } from "./mock_templates.hoot";
import { mockUserFactory } from "./mock_user.hoot";

/**
 * @typedef {{
 *  addonsKey: string;
 *  filter?: (path: string) => boolean;
 *  moduleNames: string[];
 * }} ModuleSet
 *
 * @typedef {{
 *  addons?: Iterable<string>;
 * }} ModuleSetParams
 */

const { fetch: realFetch } = globals;
const { define, loader } = odoo;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Record<any, any>} object
 */
function clearObject(object) {
    for (const key in object) {
        delete object[key];
    }
}

/**
 * @param {string} fileSuffix
 * @param {string[]} entryPoints
 * @param {Set<string>} additionalAddons
 */
async function defineModuleSet(fileSuffix, entryPoints, additionalAddons) {
    /** @type {ModuleSet} */
    const moduleSet = {};
    if (additionalAddons.has("*")) {
        // Use all addons
        moduleSet.addonsKey = "*";
        moduleSet.moduleNames = sortedModuleNames.filter((name) => !name.endsWith(fileSuffix));
    } else {
        // Use subset of addons
        for (const entryPoint of entryPoints) {
            additionalAddons.add(getAddonName(entryPoint));
        }
        const addons = await fetchDependencies(additionalAddons);
        for (const addon in AUTO_INCLUDED_ADDONS) {
            if (addons.has(addon)) {
                for (const toInclude of AUTO_INCLUDED_ADDONS[addon]) {
                    addons.add(toInclude);
                }
            }
        }
        const filter = (path) => addons.has(getAddonName(path));

        // Module names are cached for each configuration of addons
        const joinedAddons = [...addons].sort().join(",");
        if (!moduleNamesCache.has(joinedAddons)) {
            moduleNamesCache.set(
                joinedAddons,
                sortedModuleNames.filter((name) => !name.endsWith(fileSuffix) && filter(name))
            );
        }

        moduleSet.addonsKey = joinedAddons;
        moduleSet.filter = filter;
        moduleSet.moduleNames = moduleNamesCache.get(joinedAddons);
    }

    return moduleSet;
}

/**
 * @param {string} fileSuffix
 * @param {string[]} entryPoints
 */
async function describeDrySuite(fileSuffix, entryPoints) {
    const moduleSet = await defineModuleSet(fileSuffix, entryPoints, new Set(["*"]));
    const moduleSetLoader = new ModuleSetLoader(moduleSet);

    moduleSetLoader.setup();

    for (const entryPoint of entryPoints) {
        // Run test factory
        describe(getSuitePath(entryPoint), () => {
            // Load entry point module
            const fullModuleName = entryPoint + fileSuffix;
            const module = moduleSetLoader.startModule(fullModuleName);

            // Check exports (shouldn't have any)
            const exports = Object.keys(module || {});
            if (exports.length) {
                throw new Error(
                    `Test files cannot have exports, found the following exported member(s) in module ${fullModuleName}:${exports
                        .map((name) => `\n - ${name}`)
                        .join("")}`
                );
            }
        });
    }

    moduleSetLoader.cleanup();
}

/**
 * @param {Set<string>} addons
 */
async function fetchDependencies(addons) {
    // Fetch missing dependencies
    const addonsToFetch = [];
    for (const addon of addons) {
        if (!dependencyCache[addon] && !DEFAULT_ADDONS.includes(addon)) {
            addonsToFetch.push(addon);
            dependencyCache[addon] = new Deferred();
        }
    }
    if (addonsToFetch.length) {
        if (!dependencyBatch.length) {
            dependencyBatchPromise = Deferred.resolve().then(() => {
                const module_names = [...new Set(dependencyBatch)];
                dependencyBatch = [];
                return orm("ir.module.module.dependency", "all_dependencies", [], { module_names });
            });
        }
        dependencyBatch.push(...addonsToFetch);
        dependencyBatchPromise.then((allDependencies) => {
            for (const [moduleName, dependencyNames] of Object.entries(allDependencies)) {
                dependencyCache[moduleName] ||= new Deferred();
                dependencyCache[moduleName].resolve();

                dependencies[moduleName] = dependencyNames.filter(
                    (dep) => !DEFAULT_ADDONS.includes(dep)
                );
            }

            resolveAddonDependencies(dependencies);
        });
    }

    await Promise.all([...addons].map((addon) => dependencyCache[addon]));

    return getDependencies(addons);
}

/**
 * @param {string} name
 */
function findMockFactory(name) {
    if (MODULE_MOCKS_BY_NAME.has(name)) {
        return MODULE_MOCKS_BY_NAME.get(name);
    }
    for (const [key, factory] of MODULE_MOCKS_BY_REGEX) {
        if (key instanceof RegExp && key.test(name)) {
            return factory;
        }
    }
    return null;
}

/**
 * Reduce the size of the given field and freeze it.
 *
 * @param {Record<string, unknown>>} field
 */
function freezeField(field) {
    delete field.name;
    if (field.groupable) {
        delete field.groupable;
    }
    if (!field.readonly && !field.related) {
        delete field.readonly;
    }
    if (!field.required) {
        delete field.required;
    }
    if (field.searchable) {
        delete field.searchable;
    }
    if (field.sortable) {
        delete field.sortable;
    }
    if (field.store && !field.related) {
        delete field.store;
    }
    return Object.freeze(field);
}

/**
 * Reduce the size of the given model and freeze it.
 *
 * @param {Record<string, unknown>>} model
 */
function freezeModel(model) {
    if (model.fields) {
        for (const [fieldName, field] of Object.entries(model.fields)) {
            model.fields[fieldName] = freezeField(field);
        }
        Object.freeze(model.fields);
    }
    if (model.inherit) {
        if (model.inherit.length) {
            model.inherit = model.inherit.filter((m) => m !== "base");
        }
        if (!model.inherit.length) {
            delete model.inherit;
        }
    }
    if (model.order === "id") {
        delete model.order;
    }
    if (model.parent_name === "parent_id") {
        delete model.parent_name;
    }
    if (model.rec_name === "name") {
        delete model.rec_name;
    }
    return Object.freeze(model);
}

/**
 * @param {string} name
 */
function getAddonName(name) {
    return name.match(R_PATH_ADDON)?.[1];
}

/**
 * @param {Iterable<string>} addons
 */
function getDependencies(addons) {
    const result = new Set(DEFAULT_ADDONS);
    for (const addon of addons) {
        if (DEFAULT_ADDONS.includes(addon)) {
            continue;
        }
        result.add(addon);
        for (const dep of dependencies[addon]) {
            result.add(dep);
        }
    }
    return result;
}

/**
 * @param {string} name
 */
function getSuitePath(name) {
    return name.replace("../tests/", "");
}

/**
 * Keeps the original definition of a factory.
 *
 * @param {string} name
 */
function makeFixedFactory(name) {
    return () => {
        if (!loader.modules.has(name)) {
            loader.startModule(name);
        }
        return loader.modules.get(name);
    };
}

/**
 * Toned-down version of the RPC + ORM features since this file cannot depend on
 * them.
 *
 * @param {string} model
 * @param {string} method
 * @param {any[]} args
 * @param {Record<string, any>} kwargs
 */
async function orm(model, method, args, kwargs) {
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
}

/**
 * @template {Record<string, string[]>} T
 * @param {T} dependencies
 */
function resolveAddonDependencies(dependencies) {
    const findJob = () =>
        Object.entries(remaining).find(([, deps]) => deps.every((dep) => dep in solved));

    const remaining = { ...dependencies };
    /** @type {T} */
    const solved = {};

    let entry;
    while ((entry = findJob())) {
        const [name, deps] = entry;
        solved[name] = [...new Set(deps.flatMap((dep) => [dep, ...solved[dep]]))];
        delete remaining[name];
    }

    const remainingKeys = Object.keys(remaining);
    if (remainingKeys.length) {
        throw new Error(`Unresolved dependencies: ${remainingKeys.join(", ")}`);
    }

    Object.assign(dependencies, solved);
}

/**
 * @param {Record<string, unknown>>} model
 */
function unfreezeModel(model) {
    const fields = Object.create(null);
    if (model.fields) {
        for (const [fieldName, field] of Object.entries(model.fields)) {
            fields[fieldName] = { ...field };
        }
    }
    return { ...model, fields };
}

/**
 * This method tries to manually run the garbage collector (if exposed) and logs
 * the current heap size (if available). It is meant to be called right after a
 * suite's module set has been fully executed.
 *
 * This is used for debugging memory leaks, or if the containing process running
 * unit tests doesn't know how much available memory it actually has.
 *
 * To enable this feature, the containing process must simply use the `--expose-gc`
 * flag.
 *
 * @param {string} label
 * @param {number} [testCount]
 */
async function __gcAndLogMemory(label, testCount) {
    if (typeof window.gc !== "function") {
        return;
    }

    // Cleanup last retained textarea
    const textarea = document.createElement("textarea");
    document.body.appendChild(textarea);
    textarea.value = "aaa";
    textarea.focus();
    textarea.remove();

    // Run garbage collection
    await window.gc({ type: "major", execution: "async" });

    // Log memory usage
    const logs = [
        `[MEMINFO] ${label} (after GC)`,
        "- used:",
        window.performance.memory.usedJSHeapSize,
        "- total:",
        window.performance.memory.totalJSHeapSize,
        "- limit:",
        window.performance.memory.jsHeapSizeLimit,
    ];
    if (Number.isInteger(testCount)) {
        logs.push("- tests:", testCount);
    }
    console.log(...logs);
}

/** @extends {OdooModuleLoader} */
class ModuleSetLoader extends loader.constructor {
    cleanups = [];

    /**
     * @param {ModuleSet} moduleSet
     */
    constructor(moduleSet) {
        super();

        this.factories = new Map(loader.factories);
        this.modules = new Map(loader.modules);
        this.moduleSet = moduleSet;

        odoo.define = this.define.bind(this);
        odoo.loader = this;
    }

    /**
     * @override
     * @type {typeof loader["addJob"]}
     */
    addJob(name) {
        if (this.canAddModule(name)) {
            super.addJob(...arguments);
        }
    }

    /**
     * @param {string} name
     */
    canAddModule(name) {
        const { filter } = this.moduleSet;
        return !filter || filter(name) || R_DEFAULT_MODULE.test(name);
    }

    cleanup() {
        odoo.define = define;
        odoo.loader = loader;

        while (this.cleanups.length) {
            this.cleanups.pop()();
        }
    }

    /**
     * @override
     * @type {typeof loader["define"]}
     */
    define(name, deps, factory) {
        if (!loader.factories.has(name)) {
            // Lazy-loaded modules are added to the main loader for next ModuleSetLoader
            // instances.
            loader.define(name, deps, factory, true);
            // We assume that lazy-loaded modules are not required by any other
            // module.
            sortedModuleNames.push(name);
            moduleNamesCache.clear();
        }
        return super.define(...arguments);
    }

    setup() {
        this.cleanups.push(
            watchKeys(window.odoo),
            watchKeys(window, ALLOWED_GLOBAL_KEYS),
            watchListeners()
        );

        // Load module set modules (without entry point)
        for (const name of this.moduleSet.moduleNames) {
            const mockFactory = findMockFactory(name);
            if (mockFactory) {
                // Use mock
                this.factories.set(name, {
                    deps: [],
                    fn: mockFactory(name, this.factories.get(name)),
                });
            }
            if (!this.modules.has(name)) {
                // Run (or re-run) module factory
                this.startModule(name);
            }
        }
    }

    /**
     * @override
     * @type {typeof loader["startModule"]}
     */
    startModule(name) {
        if (this.canAddModule(name)) {
            return super.startModule(...arguments);
        }
        this.jobs.delete(name);
        return null;
    }
}

const ALLOWED_GLOBAL_KEYS = [
    "ace", // Ace editor
    // Bootstrap.js is voluntarily ignored as it is deprecated
    "Chart", // Chart.js
    "DOMPurify", // DOMPurify
    "FullCalendar", // Full Calendar
    "L", // Leaflet
    "lamejs", // LameJS
    "luxon", // Luxon
    "odoo", // Odoo global object
    "owl", // Owl
    "pdfjsLib", // PDF JS
    "Popper", // Popper
    "SignaturePad", // Signature Pad
    "StackTrace", // StackTrace
    "ZXing", // ZXing
];
const AUTO_INCLUDED_ADDONS = {
    /**
     * spreadsheet addons defines a module that does not starts with `@spreadsheet` but `@odoo` (`@odoo/o-spreadsheet)
     * To ensure that this module is loaded, we have to include `odoo` in the dependencies
     */
    spreadsheet: ["odoo"],
    /**
     * Add all view types by default
     */
    web_enterprise: ["web_gantt", "web_grid", "web_map"],
};
const CSRF_TOKEN = odoo.csrf_token;
const DEFAULT_ADDONS = ["base", "web"];
const MODULE_MOCKS_BY_NAME = new Map([
    // Fixed modules
    ["@web/core/template_inheritance", makeFixedFactory],
    // Other mocks
    ["@web/core/browser/browser", mockBrowserFactory],
    ["@web/core/currency", mockCurrencyFactory],
    ["@web/core/templates", makeTemplateFactory],
    ["@web/core/user", mockUserFactory],
    ["@web/session", mockSessionFactory],
]);
const MODULE_MOCKS_BY_REGEX = new Map([
    // Fixed modules
    [/\.bundle\.xml$/, makeFixedFactory],
]);
const R_DEFAULT_MODULE = /^@odoo\/(owl|hoot)/;
const R_PATH_ADDON = /^[@/]?(\w+)/;
const TEMPLATE_MODULE_NAME = "@web/core/templates";

/** @type {Record<string, string[]} */
const dependencies = {};
/** @type {Record<string, Deferred} */
const dependencyCache = {};
/** @type {Record<string, Promise<Response>} */
const globalFetchCache = Object.create(null);
/** @type {Set<string>} */
const modelsToFetch = new Set();
/** @type {Map<string, string[]>} */
const moduleNamesCache = new Map();
/** @type {Map<string, Record<string, unknown>>} */
const serverModelCache = new Map();
/** @type {string[]} */
const sortedModuleNames = [];

/** @type {string[]} */
let dependencyBatch = [];
/** @type {Promise<Record<string, string[]>> | null} */
let dependencyBatchPromise = null;
let nextRpcId = 1e9;

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

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
        formData.set("csrf_token", CSRF_TOKEN);
        formData.set("model_names", JSON.stringify(namesList));

        const response = await realFetch("/web/model/get_definitions", {
            body: formData,
            method: "POST",
        });
        if (!response.ok) {
            const [s, some, does] =
                namesList.length === 1 ? ["", "this", "does"] : ["s", "some or all of these", "do"];
            const message = `Could not fetch definition${s} for server model${s} "${namesList.join(
                `", "`
            )}": ${some} model${s} ${does} not exist`;
            throw new Error(message);
        }
        const modelDefs = await response.json();

        for (const [modelName, modelDef] of Object.entries(modelDefs)) {
            serverModelCache.set(modelName, freezeModel(modelDef));
            modelsToFetch.delete(modelName);
        }
    }

    const result = Object.create(null);
    for (const modelName of modelNames) {
        result[modelName] = unfreezeModel(serverModelCache.get(modelName));
    }
    return result;
}

/**
 * @param {string | URL} input
 * @param {RequestInit} [init]
 */
export function globalCachedFetch(input, init) {
    if (init?.method && init.method.toLowerCase() !== "get") {
        throw new Error(`cannot use a global cached fetch with HTTP method "${init.method}"`);
    }
    const key = String(input);
    if (!(key in globalFetchCache)) {
        globalFetchCache[key] = realFetch(input, init).catch((reason) => {
            delete globalFetchCache[key];
            throw reason;
        });
    }
    return globalFetchCache[key].then((response) => response.clone());
}

/**
 * @param {string} modelName
 */
export function registerModelToFetch(modelName) {
    if (!serverModelCache.has(modelName)) {
        modelsToFetch.add(modelName);
    }
}

/**
 * @param {{ fileSuffix?: string }} [options]
 */
export async function runTests(options) {
    const { fileSuffix = "" } = options || {};
    // Find dependency issues
    const errors = loader.findErrors(loader.factories.keys());
    delete errors.unloaded; // Only a few modules have been loaded yet => irrelevant
    if (Object.keys(errors).length) {
        return loader.reportErrors(errors);
    }

    // Sort modules to accelerate loading time
    /** @type {Record<string, Deferred>} */
    const defs = {};
    /** @type {string[]} */
    const testModuleNames = [];
    for (const [name, { deps }] of loader.factories) {
        // Register test module
        if (name.endsWith(fileSuffix)) {
            const baseName = name.slice(0, -fileSuffix.length);
            testModuleNames.push(baseName);
        }

        // Register module dependencies
        const [modDef, ...depDefs] = [name, ...deps].map((dep) => (defs[dep] ||= new Deferred()));
        Promise.all(depDefs).then(() => {
            sortedModuleNames.push(name);
            modDef.resolve();
        });
    }

    await Promise.all(Object.values(defs));

    // Dry run
    const { suites } = await dryRun(() => describeDrySuite(fileSuffix, testModuleNames));

    // Run all test files
    const filteredSuitePaths = new Set(suites.map((s) => s.fullName));
    let currentAddonsKey = "";
    for (const moduleName of testModuleNames) {
        const suitePath = getSuitePath(moduleName);
        if (!filteredSuitePaths.has(suitePath)) {
            continue;
        }

        const moduleSet = await defineModuleSet(fileSuffix, [moduleName], new Set());
        const moduleSetLoader = new ModuleSetLoader(moduleSet);

        if (currentAddonsKey !== moduleSet.addonsKey) {
            if (moduleSetLoader.modules.has(TEMPLATE_MODULE_NAME)) {
                // If templates module is available: set URL filter to filter out
                // static templates and cleanup current processed templates.
                const templateModule = moduleSetLoader.modules.get(TEMPLATE_MODULE_NAME);
                templateModule.setUrlFilters(moduleSet.filter ? [moduleSet.filter] : []);
                templateModule.clearProcessedTemplates();
            }
            currentAddonsKey = moduleSet.addonsKey;
        }

        const suite = describe(suitePath, () => {
            moduleSetLoader.setup();
            moduleSetLoader.startModule(moduleName + fileSuffix);
        });

        // Run recently added tests
        const running = await start(suite);

        moduleSetLoader.cleanup();
        await __gcAndLogMemory(suite.fullName, suite.reporting.tests);

        if (!running) {
            break;
        }
    }

    await stop();

    // Perform final cleanups
    moduleNamesCache.clear();
    serverModelCache.clear();
    clearObject(dependencies);
    clearObject(dependencyCache);
    clearObject(globalFetchCache);
    const templateModule = loader.modules.get(TEMPLATE_MODULE_NAME);
    if (templateModule) {
        templateModule.setUrlFilters([]);
        templateModule.clearProcessedTemplates();
    }

    await __gcAndLogMemory("tests done");
}
