// @ts-check
/** @odoo-module native */

import { Component, onWillStart, whenReady, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { session } from "@web/session";

import {
    getBridgeModuleSource,
    isLoaderBridgeUrl,
    specToModuleUrl,
    toDataModuleUrl,
} from "./module_bridge.js";
import { registry } from "./registry.js";
import { makeAssetLog } from "./utils/asset_log.js";
import { runInBundleTransaction } from "./utils/bundle_transaction.js";
import { globalSingleton } from "./utils/global_singleton.js";

const log = makeAssetLog("js");
const debugLog = makeLogger("web.assets");

/**
 * @typedef {{
 * cssLibs: string[];
 * jsLibs: string[];
 * esmUrl: string | null;
 * esmSpecifiers: string[] | null;
 * esmImportMap: Record<string, string> | null;
 * }} BundleFileNames
 */

const __odoo_assets_state__ = globalSingleton("assets", () => ({
    globalBundleCache: new Map(),
    assetCacheByDocument: new WeakMap(),
    crossDocESMBundleCache: new WeakMap(),
    esmBundleCache: new Map(),
    injectedImportMapKeys: new Map(),
    crossDocImportMapKeys: new WeakMap(),
    crossDocLoadSeq: 0,
}));

export const globalBundleCache = __odoo_assets_state__.globalBundleCache;
export const assetCacheByDocument = __odoo_assets_state__.assetCacheByDocument;
const crossDocESMBundleCache = __odoo_assets_state__.crossDocESMBundleCache;
export const esmBundleCache = __odoo_assets_state__.esmBundleCache;
const injectedImportMapKeys = __odoo_assets_state__.injectedImportMapKeys;
const crossDocImportMapKeys = __odoo_assets_state__.crossDocImportMapKeys;

/**
 * @param {Document} targetDoc
 * @returns {Map<string, string>}
 */
function getInjectedImportMapKeys(targetDoc) {
    if (targetDoc === document || targetDoc.defaultView === window) {
        return injectedImportMapKeys;
    }
    let keys = crossDocImportMapKeys.get(targetDoc);
    if (!keys) {
        keys = new Map();
        crossDocImportMapKeys.set(targetDoc, keys);
    }
    return keys;
}

/**
 * @param {string} url
 * @param {Document} targetDoc
 * @returns {string}
 */
function absoluteTarget(url, targetDoc) {
    try {
        return new URL(url, targetDoc.baseURI).href;
    } catch {
        return url;
    }
}

/**
 * @param {Document} targetDoc
 * @param {Map<string, string>} [keys]
 * @returns {number}
 */
function addInjectedImportMapKeys(targetDoc, keys) {
    const head = targetDoc.head || targetDoc.documentElement;
    if (!head) {
        return 0;
    }
    const injected = keys ?? getInjectedImportMapKeys(targetDoc);
    let seeded = 0;
    for (const script of head.querySelectorAll('script[type="importmap"]')) {
        const text = script.textContent || "";
        if (!text.trim()) {
            continue;
        }
        try {
            const parsed = JSON.parse(text);
            const imports = parsed && parsed.imports;
            if (imports && typeof imports === "object") {
                for (const [spec, url] of Object.entries(imports)) {
                    if (!injected.has(spec)) {
                        injected.set(spec, absoluteTarget(url, targetDoc));
                        seeded++;
                    }
                }
            }
        } catch {}
    }
    return seeded;
}

/**
 * @param {string} specifier
 * @param {Record<string, string> | null | undefined} importMap
 * @param {Map<string, string>} injected
 * @param {Document} targetDoc
 * @returns {{ target: string, conflict: boolean }}
 */
function resolveSpecifierTarget(specifier, importMap, injected, targetDoc) {
    const wanted = importMap?.[specifier];
    if (!wanted) {
        return { target: specifier, conflict: false };
    }
    const claimed = injected.get(specifier);
    const wantedAbs = absoluteTarget(wanted, targetDoc);
    if (claimed === undefined || claimed === wantedAbs) {
        return { target: specifier, conflict: false };
    }
    return { target: wantedAbs, conflict: true };
}

/**
 * @param {Document} targetDoc
 * @param {Record<string, string>} importMap
 * @param {Map<string, string>} injected
 * @returns {{ fresh: number, dup: number, conflicts: string[] }}
 */
function addFreshImportMapEntries(targetDoc, importMap, injected) {
    /** @type {Record<string, string>} */
    const freshEntries = {};
    let dup = 0;
    /** @type {string[]} */
    const conflicts = [];
    for (const [spec, url] of Object.entries(importMap)) {
        const claimed = injected.get(spec);
        const wanted = absoluteTarget(url, targetDoc);
        if (claimed === undefined) {
            freshEntries[spec] = url;
            injected.set(spec, wanted);
        } else if (claimed === wanted) {
            dup++;
        } else {
            conflicts.push(spec);
        }
    }
    const fresh = Object.keys(freshEntries).length;
    if (fresh) {
        const mapEl = targetDoc.createElement("script");
        mapEl.type = "importmap";
        mapEl.textContent = JSON.stringify({ imports: freshEntries });
        (targetDoc.head || targetDoc.documentElement).appendChild(mapEl);
    }
    return { fresh, dup, conflicts };
}

/**
 * @param {Document} targetDoc
 * @returns {Map<string, Promise<any>>}
 */
function getAssetCache(targetDoc) {
    let cacheMap = assetCacheByDocument.get(targetDoc);
    if (!cacheMap) {
        cacheMap = new Map();
        assetCacheByDocument.set(targetDoc, cacheMap);
        loadFromDocument(targetDoc, cacheMap);
    }
    return cacheMap;
}

/**
 * @param {Document} targetDoc
 * @param {Map<string, Promise<any>>} cacheMap
 */
function loadFromDocument(targetDoc, cacheMap) {
    const head = targetDoc.head;
    if (!head) {
        return;
    }
    const seed = (/** @type {string | null} */ url) => {
        if (url && !cacheMap.has(url)) {
            cacheMap.set(url, Promise.resolve());
        }
    };
    for (const script of head.querySelectorAll("script[src]")) {
        seed(script.getAttribute("src"));
    }
    for (const link of head.querySelectorAll("link[rel=stylesheet][href]")) {
        seed(link.getAttribute("href"));
    }
}

/** @param {Document} targetDoc */
function reseedFromDocument(targetDoc) {
    const cacheMap = assetCacheByDocument.get(targetDoc);
    if (cacheMap) {
        loadFromDocument(targetDoc, cacheMap);
    } else {
        getAssetCache(targetDoc);
    }
}

whenReady(() => {
    reseedFromDocument(document);
    const seeded = addInjectedImportMapKeys(document);
    log("whenReady:seeded-import-map-keys", seeded);
});

/**
 * @param {HTMLLinkElement | HTMLScriptElement} el
 * @param {(event: Event) => any} onLoad
 * @param {(error: Error) => any} onError
 * @param {() => void} [onPageHideCleanup]
 * @param {(error: Error) => any} [onInterrupt]
 */
const onLoadAndError = (el, onLoad, onError, onPageHideCleanup, onInterrupt) => {
    const view = el.ownerDocument?.defaultView ?? window;

    const onLoadListener = (/** @type {Event} */ event) => {
        removeListeners();
        onLoad(event);
    };

    const onErrorListener = (/** @type {Event} */ error) => {
        removeListeners();
        onError(/** @type {any} */ (error));
    };

    const onPageHide = () => {
        removeListeners();
        onPageHideCleanup?.();
        onInterrupt?.(
            new AssetsLoadingError(
                `The loading of ${el.getAttribute("src") || el.getAttribute("href")} was interrupted: the page was hidden`,
            ),
        );
    };

    const removeListeners = () => {
        el.removeEventListener("load", onLoadListener);
        el.removeEventListener("error", onErrorListener);
        view.removeEventListener("pagehide", onPageHide);
    };

    el.addEventListener("load", onLoadListener);
    el.addEventListener("error", onErrorListener);
    view.addEventListener("pagehide", onPageHide);
};

/**
 * @param {Document} targetDoc
 * @returns {string}
 */
function pageBundleOf(targetDoc) {
    const mapEl = targetDoc.querySelector('script[type="importmap"][data-bundle]');
    return (mapEl && mapEl.getAttribute("data-bundle")) || "";
}

/**
 * @param {string} bundleName
 * @param {{ targetDoc?: Document }} [options]
 * @returns {Promise<BundleFileNames>}
 */
export function getBundle(bundleName, options) {
    return assets.getBundle(bundleName, options);
}

/**
 * @param {string} bundleName
 * @param {{ targetDoc?: Document, css?: boolean, js?: boolean }} [options]
 * @returns {Promise<void[]>}
 */
export function loadBundle(bundleName, options) {
    return assets.loadBundle(bundleName, options);
}

/**
 * @param {string} url
 * @param {{ targetDoc?: Document }} [options]
 * @returns {Promise<void>}
 */
export function loadJS(url, options) {
    return assets.loadJS(url, options);
}

/**
 * @param {string} url
 * @param {{ retryCount?: number, targetDoc?: Document }} [options]
 * @returns {Promise<void>}
 */
export function loadCSS(url, options) {
    return assets.loadCSS(url, options);
}

export class AssetsLoadingError extends Error {}

/**
 * @param {string[]} specifiers
 * @param {Record<string, string> | null} importMap
 * @returns {Promise<void>}
 */
function loadESMBundleHere(specifiers, importMap) {
    // a bundle the page already carries lists every module as a specifier; a
    // second load re-imported them all (~25 ms for the website builder), which
    // is a frame a caller like LazyComponent does not expect to lose
    const cacheKey = JSON.stringify(specifiers);
    if (!esmBundleCache.has(cacheKey)) {
        const promise = importESMBundleHere(specifiers, importMap).catch((reason) => {
            evictIfCurrent(esmBundleCache, cacheKey, () => promise);
            throw reason;
        });
        esmBundleCache.set(cacheKey, promise);
    } else {
        log("loadESMBundle:cache-hit", "specs=", specifiers.length);
    }
    return esmBundleCache.get(cacheKey);
}

/**
 * @param {string[]} specifiers
 * @param {Record<string, string> | null} importMap
 * @returns {Promise<void>}
 */
async function importESMBundleHere(specifiers, importMap) {
    if (importMap) {
        addInjectedImportMapKeys(document);
        const { fresh, dup, conflicts } = addFreshImportMapEntries(
            document,
            importMap,
            injectedImportMapKeys,
        );
        log(
            "loadESMBundle:importMap filter",
            "fresh=",
            fresh,
            "dup=",
            dup,
            "conflict=",
            conflicts.length,
            "total=",
            fresh + dup + conflicts.length,
        );
        if (conflicts.length) {
            log("loadESMBundle:specifier already claimed elsewhere", conflicts);
        }
        if (fresh) {
            log("loadESMBundle:injected fresh import map entries=", fresh);
        }
    }
    const results = await runInBundleTransaction(() =>
        Promise.all(
            specifiers.map(async (specifier) => {
                // a module the page already registered is that module: importing
                // it again through a bridge would hand the loader a second
                // namespace object for the same singleton
                const registered = /** @type {any} */ (
                    globalThis
                ).odoo?.loader?.modules?.get(specifier);
                if (
                    registered !== undefined &&
                    typeof registered.__setImplUrl !== "function"
                ) {
                    return [specifier, registered];
                }
                const { target } = resolveSpecifierTarget(
                    specifier,
                    importMap,
                    injectedImportMapKeys,
                    document,
                );
                const mod = await import(target);
                const mappedUrl = importMap?.[specifier];
                if (mappedUrl && typeof mod.__setImplUrl === "function") {
                    await mod.__setImplUrl(new URL(mappedUrl, document.baseURI).href);
                }
                return [specifier, mod];
            }),
        ),
    );
    const modules = Object.fromEntries(results);
    if (/** @type {any} */ (globalThis).odoo?.loader?.registerNativeModules) {
        odoo.loader.registerNativeModules(modules);
        log("loadESMBundle:registered", specifiers.length, "modules into odoo.loader");
    } else {
        log("loadESMBundle:warn no odoo.loader.registerNativeModules");
    }
}

/**
 * @param {Document} targetDoc
 * @param {Record<string, string> | null} importMap
 * @returns {Record<string, any>}
 */
function getBridgeImportMap(targetDoc, importMap) {
    const targetWin = /** @type {any} */ (targetDoc.defaultView);
    const serverMap = importMap || {};
    /** @type {Record<string, any>} */
    const extraMap = {};
    const loadedModules = targetWin.odoo?.loader?.modules;
    if (loadedModules && typeof loadedModules.get === "function") {
        const specs =
            typeof loadedModules.keys === "function"
                ? Array.from(loadedModules.keys())
                : [];
        for (const spec of specs) {
            if (!spec || typeof spec !== "string" || spec.startsWith("@odoo/")) {
                continue;
            }
            const mod = loadedModules.get(spec);
            if (!mod || typeof mod !== "object") {
                continue;
            }
            const bridgeTarget = isLoaderBridgeUrl(serverMap[spec])
                ? serverMap[spec]
                : toDataModuleUrl(getBridgeModuleSource(spec, Object.keys(mod)));
            if (serverMap[spec] === undefined) {
                extraMap[spec] = bridgeTarget;
            }
            const url = specToModuleUrl(spec);
            if (url && serverMap[url] === undefined) {
                extraMap[url] = bridgeTarget;
            }
        }
    }
    Object.assign(extraMap, serverMap);
    return extraMap;
}

/**
 * @param {Document} targetDoc
 * @param {string[]} specifiers
 * @param {Record<string, any>} extraMap
 * @param {Map<string, string>} injected
 * @returns {Promise<any>}
 */
function runESMBundleScript(targetDoc, specifiers, extraMap, injected) {
    const token = ++__odoo_assets_state__.crossDocLoadSeq;
    const doneEvent = `__odoo_esm_bundle_loaded_${token}`;
    const errorEvent = `__odoo_esm_bundle_error_${token}`;
    const importPairs = specifiers.map((specifier) => [
        specifier,
        resolveSpecifierTarget(specifier, extraMap, injected, targetDoc).target,
    ]);
    const scriptText = `
            (async () => {
                try {
                    const specs = ${JSON.stringify(importPairs)};
                    const pairs = await Promise.all(
                        specs.map(async ([s, t]) => [s, await import(t)])
                    );
                    const modules = Object.fromEntries(pairs);
                    if (window.odoo?.loader?.registerNativeModules) {
                        window.odoo.loader.registerNativeModules(modules);
                    }
                    window.dispatchEvent(new Event(${JSON.stringify(doneEvent)}));
                } catch (err) {
                    window.dispatchEvent(new CustomEvent(${JSON.stringify(errorEvent)}, { detail: err }));
                }
            })();
        `;
    const scriptEl = targetDoc.createElement("script");
    scriptEl.type = "module";
    scriptEl.textContent = scriptText;
    const win = /** @type {Window} */ (targetDoc.defaultView);
    return new Promise((resolve, reject) => {
        const settle = (/** @type {() => void} */ fn) => {
            win.removeEventListener(doneEvent, onDone);
            win.removeEventListener(errorEvent, onError);
            win.removeEventListener("pagehide", onPageHide);
            scriptEl.removeEventListener("error", onScriptError);
            fn();
        };
        const onDone = () => settle(() => resolve(undefined));
        const onError = (/** @type {Event} */ e) =>
            settle(() =>
                reject(
                    /** @type {CustomEvent} */ (e).detail ||
                        new Error(`loadESMBundle failed`),
                ),
            );
        const onScriptError = (/** @type {Event} */ error) =>
            settle(() =>
                reject(
                    new AssetsLoadingError(`The loading of an ESM bundle failed`, {
                        cause: error,
                    }),
                ),
            );
        const onPageHide = () =>
            settle(() =>
                reject(
                    new AssetsLoadingError(
                        `The loading of an ESM bundle was interrupted: the target document was unloaded`,
                    ),
                ),
            );
        win.addEventListener(doneEvent, onDone);
        win.addEventListener(errorEvent, onError);
        win.addEventListener("pagehide", onPageHide);
        scriptEl.addEventListener("error", onScriptError);
        (targetDoc.head || targetDoc.documentElement).appendChild(scriptEl);
    });
}

/**
 * @param {Document} targetDoc
 * @param {string[]} specifiers
 * @param {Record<string, string> | null} importMap
 * @returns {Promise<any>}
 */
async function loadESMBundleInto(targetDoc, specifiers, importMap) {
    const cacheKey = JSON.stringify(specifiers);
    if (!crossDocESMBundleCache.has(targetDoc)) {
        crossDocESMBundleCache.set(targetDoc, new Map());
    }
    const bundleCache = crossDocESMBundleCache.get(targetDoc);
    if (bundleCache.has(cacheKey)) {
        log("loadESMBundle:crossDoc cache-hit", "specs=", specifiers.length);
        return bundleCache.get(cacheKey);
    }
    const extraMap = getBridgeImportMap(targetDoc, importMap);
    const injected = getInjectedImportMapKeys(targetDoc);
    addInjectedImportMapKeys(targetDoc, injected);
    const { fresh, dup, conflicts } = addFreshImportMapEntries(
        targetDoc,
        extraMap,
        injected,
    );
    if (conflicts.length) {
        log("loadESMBundle:crossDoc specifier already claimed", conflicts);
    }
    if (fresh) {
        log(
            "loadESMBundle:crossDoc injecting extra import map entries=",
            fresh,
            "dup=",
            dup,
        );
    }
    const settlePromise = runESMBundleScript(targetDoc, specifiers, extraMap, injected);
    bundleCache.set(cacheKey, settlePromise);
    settlePromise.catch(() =>
        evictIfCurrent(bundleCache, cacheKey, () => settlePromise),
    );
    return settlePromise;
}

/**
 * @param {"loadCSS" | "loadJS"} what
 * @param {string} url
 * @param {Document} targetDoc
 * @param {number} retryCount
 * @param {(doc: Document) => HTMLLinkElement | HTMLScriptElement} build
 * @returns {Promise<void>}
 */
function loadElement(what, url, targetDoc, retryCount, build) {
    const cacheMap = getAssetCache(targetDoc);
    if (cacheMap.has(url)) {
        return /** @type {Promise<void>} */ (cacheMap.get(url));
    }
    /**
     * @param {number} attempt
     * @returns {Promise<void>}
     */
    const runAttempt = (attempt) => {
        log(
            attempt === 0 ? what : `${what}:retry`,
            url,
            ...(attempt ? ["attempt=", attempt] : []),
        );
        const el = build(targetDoc);
        /** @type {(reason?: any) => void} */
        let reject = () => {};
        const attemptPromise = new Promise((res, rej) => {
            reject = rej;
            return onLoadAndError(
                el,
                res,
                async (error) => {
                    el.remove();
                    const retryable = !url.includes("/web/assets/");
                    if (retryable && attempt < assets.retries.count) {
                        const delay =
                            assets.retries.delay + assets.retries.extraDelay * attempt;
                        await new Promise((r) => browser.setTimeout(r, delay));
                        runAttempt(attempt + 1).then(res, rej);
                    } else {
                        rej(
                            new AssetsLoadingError(`The loading of ${url} failed`, {
                                cause: error,
                            }),
                        );
                    }
                },
                () => evictIfCurrent(cacheMap, url, () => promise),
                rej,
            );
        });
        mountAsset(targetDoc, el, url, reject);
        return attemptPromise;
    };
    const promise = /** @type {Promise<void>} */ (
        runAttempt(retryCount).catch((reason) => {
            evictIfCurrent(cacheMap, url, () => promise);
            throw reason;
        })
    );
    cacheMap.set(url, promise);
    return promise;
}

/**
 * @param {Document} targetDoc
 * @param {HTMLLinkElement | HTMLScriptElement} el
 * @param {string} url
 * @param {(reason: any) => void} onError
 */
function mountAsset(targetDoc, el, url, onError) {
    try {
        (targetDoc.head || targetDoc.documentElement).appendChild(el);
    } catch (error) {
        onError(
            new AssetsLoadingError(
                `The loading of ${url} failed: its target document could not take it`,
                { cause: error },
            ),
        );
    }
}

/**
 * @param {any} result
 * @param {URL} url
 * @returns {BundleFileNames}
 */
function readBundleDescriptor(result, url) {
    if (!result || typeof result !== "object") {
        throw new AssetsLoadingError(
            `The loading of ${url} failed: unexpected bundle descriptor`,
        );
    }
    const cssLibs = [];
    const jsLibs = [];
    if (result.is_esm) {
        const esmUrl = result.esm_url || null;
        const esmSpecifiers = esmUrl ? null : result.specifiers || [];
        const esmImportMap = result.import_map || null;
        if (esmSpecifiers && result.template_url) {
            esmSpecifiers.push(result.template_url);
        }
        for (const { src, type } of Object.values(result.files || {})) {
            if (type === "link" && src) {
                cssLibs.push(src);
            } else if (type === "script" && src && !src.includes(".esm.")) {
                jsLibs.push(src);
            }
        }
        return { cssLibs, jsLibs, esmUrl, esmSpecifiers, esmImportMap };
    }
    let skippedEsm = 0;
    for (const { src, type } of Object.values(result)) {
        if (type === "link" && src) {
            cssLibs.push(src);
        } else if (type === "script" && src && !src.includes(".esm.")) {
            jsLibs.push(src);
        } else if (type === "script" && src) {
            skippedEsm++;
        }
    }
    if (skippedEsm && !jsLibs.length) {
        throw new AssetsLoadingError(
            `The loading of ${url} failed: a non-ESM descriptor named ` +
                `${skippedEsm} ESM chunk(s) and no loadable script`,
        );
    }
    return { cssLibs, jsLibs, esmUrl: null, esmSpecifiers: null, esmImportMap: null };
}

/**
 * @param {Map<string, Promise<any>>} cacheMap
 * @param {string} url
 * @param {() => Promise<any>} getOwn
 */
function evictIfCurrent(cacheMap, url, getOwn) {
    if (cacheMap.get(url) === getOwn()) {
        cacheMap.delete(url);
    }
}

registry
    .category("lazy_components")
    .addValidation((entry) => entry?.prototype instanceof Component);

export class LazyComponent extends Component {
    static template = xml`<t t-component="Component" t-props="componentProps"/>`;
    static props = {
        Component: String,
        bundle: String,
        props: { type: [Object, Function], optional: true },
    };
    setup() {
        onWillStart(async () => {
            await loadBundle(this.props.bundle);
            this.Component = registry
                .category("lazy_components")
                .get(this.props.Component);
        });
    }

    get componentProps() {
        return typeof this.props.props === "function"
            ? this.props.props()
            : this.props.props;
    }
}

export const assets = {
    reseedFromDocument,

    retries: {
        count: 3,
        delay: 5000,
        extraDelay: 2500,
    },

    /**
     * @param {string} bundleName
     * @param {{ targetDoc?: Document }} [options]
     * @returns {Promise<BundleFileNames>}
     */
    getBundle(bundleName, { targetDoc = document } = {}) {
        const cacheMap = globalBundleCache;
        const page = pageBundleOf(targetDoc);
        const cacheKey = page ? `${bundleName}|${page}` : bundleName;
        debugLog.logic("getBundle", () => ({
            bundleName,
            page,
            cached: cacheMap.has(cacheKey),
        }));
        if (cacheMap.has(cacheKey)) {
            log("getBundle:cache-hit", bundleName);
            return /** @type {Promise<BundleFileNames>} */ (cacheMap.get(cacheKey));
        }
        log("getBundle:fetch", bundleName, "page=", page);
        const url = new URL(`/web/bundle/${bundleName}`, browser.location.origin);
        for (const [key, value] of Object.entries(session.bundle_params || {})) {
            url.searchParams.set(key, value);
        }
        if (page) {
            url.searchParams.set("page", page);
        }
        const promise = (async () => {
            const response = await browser.fetch(url);
            if (!response.ok) {
                throw new AssetsLoadingError(
                    `The loading of ${url} failed with HTTP status ${response.status}`,
                );
            }
            const files = readBundleDescriptor(await response.json(), url);
            log("getBundle:done", bundleName, {
                cssLibs: files.cssLibs.length,
                jsLibs: files.jsLibs.length,
                esmSpecifiers: files.esmSpecifiers?.length ?? null,
                importMapEntries: files.esmImportMap
                    ? Object.keys(files.esmImportMap).length
                    : null,
            });
            return files;
        })().catch((reason) => {
            evictIfCurrent(cacheMap, cacheKey, () => promise);
            log("getBundle:error", bundleName, reason);
            if (reason instanceof AssetsLoadingError) {
                throw reason;
            }
            throw new AssetsLoadingError(`The loading of ${url} failed`, {
                cause: reason,
            });
        });
        cacheMap.set(cacheKey, promise);
        return promise;
    },

    /**
     * @param {string} bundleName
     * @param {Object} options
     * @param {Document} [options.targetDoc=document]
     * @param {Boolean} [options.css=true]
     * @param {Boolean} [options.js=true]
     * @returns {Promise<void[]>}
     */
    async loadBundle(bundleName, { targetDoc = document, css = true, js = true } = {}) {
        if (typeof bundleName !== "string") {
            throw new Error(
                `loadBundle(bundleName:string) accepts only bundleName argument as a string ! Not ${JSON.stringify(
                    bundleName,
                )} as ${typeof bundleName}`,
            );
        }
        log(
            "loadBundle:start",
            bundleName,
            "css=",
            css,
            "js=",
            js,
            "crossDoc=",
            targetDoc !== document,
        );
        const endLoad = debugLog.perf(`loadBundle ${bundleName}`);
        const { cssLibs, jsLibs, esmUrl, esmSpecifiers, esmImportMap } =
            await getBundle(bundleName, { targetDoc });
        const promises = [];
        if (css && cssLibs) {
            promises.push(...cssLibs.map((url) => assets.loadCSS(url, { targetDoc })));
        }
        if (js && esmUrl) {
            promises.push(
                assets.loadESMModule(esmUrl, { targetDoc, importMap: esmImportMap }),
            );
        } else if (js && esmSpecifiers) {
            promises.push(
                assets.loadESMBundle(esmSpecifiers, {
                    targetDoc,
                    importMap: esmImportMap,
                }),
            );
        }
        if (js && jsLibs && jsLibs.length) {
            promises.push(...jsLibs.map((url) => assets.loadJS(url, { targetDoc })));
        }
        const result = await Promise.all(promises);
        endLoad({
            css: cssLibs?.length || 0,
            js: jsLibs?.length || 0,
            esm: Boolean(esmUrl || esmSpecifiers),
        });
        log("loadBundle:done", bundleName, "promises=", promises.length);
        return result;
    },

    /**
     * @param {string[]} specifiers
     * @param {{ targetDoc?: Document, importMap?: Record<string, string> | null }} [options]
     * @returns {Promise<void>}
     */
    /**
     * @param {string[]} specifiers
     * @param {{ targetDoc?: Document, importMap?: Record<string, string> | null }} [options]
     * @returns {Promise<void>}
     */
    async loadESMBundle(specifiers, { targetDoc = document, importMap = null } = {}) {
        const here = targetDoc === document || targetDoc.defaultView === window;
        log(
            "loadESMBundle:start",
            "specs=",
            specifiers.length,
            "importMap=",
            importMap ? Object.keys(importMap).length : 0,
            "crossDoc=",
            !here,
        );
        return here
            ? loadESMBundleHere(specifiers, importMap)
            : loadESMBundleInto(targetDoc, specifiers, importMap);
    },

    /**
     * @param {string} url
     * @param {{ targetDoc?: Document, importMap?: Record<string, string> | null }} [options]
     * @returns {Promise<void>}
     */
    async loadESMModule(url, { targetDoc = document, importMap = null } = {}) {
        const here = targetDoc === document || targetDoc.defaultView === window;
        const injected = getInjectedImportMapKeys(targetDoc);
        addInjectedImportMapKeys(targetDoc, injected);
        if (importMap) {
            const { fresh, conflicts } = addFreshImportMapEntries(
                targetDoc,
                importMap,
                injected,
            );
            log(
                "loadESMModule:importMap",
                url,
                "fresh=",
                fresh,
                "conflict=",
                conflicts.length,
            );
        }
        if (here) {
            const cacheMap = getAssetCache(document);
            if (!cacheMap.has(url)) {
                const promise = runInBundleTransaction(() =>
                    import(absoluteTarget(url, document)).then(() => {}),
                ).catch((reason) => {
                    evictIfCurrent(cacheMap, url, () => promise);
                    throw new AssetsLoadingError(`The loading of ${url} failed`, {
                        cause: reason,
                    });
                });
                cacheMap.set(url, promise);
            }
            return /** @type {Promise<void>} */ (cacheMap.get(url));
        }
        return loadElement("loadJS", url, targetDoc, 0, (doc) => {
            const scriptEl = doc.createElement("script");
            scriptEl.setAttribute("src", url);
            scriptEl.type = "module";
            return scriptEl;
        });
    },

    /**
     * @param {string} url
     * @param {{ retryCount?: number, targetDoc?: Document }} [options]
     * @returns {Promise<void>}
     */
    loadCSS(url, { retryCount = 0, targetDoc = document } = {}) {
        return loadElement("loadCSS", url, targetDoc, retryCount, (doc) => {
            const linkEl = doc.createElement("link");
            linkEl.setAttribute("href", url);
            linkEl.type = "text/css";
            linkEl.rel = "stylesheet";
            return linkEl;
        });
    },

    /**
     * @param {string} url
     * @param {{ retryCount?: number, targetDoc?: Document }} [options]
     * @returns {Promise<void>}
     */
    loadJS(url, { retryCount = 0, targetDoc = document } = {}) {
        return loadElement("loadJS", url, targetDoc, retryCount, (doc) => {
            const scriptEl = doc.createElement("script");
            scriptEl.setAttribute("src", url);
            scriptEl.type = "text/javascript";
            scriptEl.async = false;
            return scriptEl;
        });
    },
};
