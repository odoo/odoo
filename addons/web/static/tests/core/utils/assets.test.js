// @ts-check

import { after, afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { mockFetch } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    assetCacheByDocument,
    assets,
    AssetsLoadingError,
    esmBundleCache,
    globalBundleCache,
    loadBundle,
    loadCSS,
    loadJS,
} from "@web/core/assets";

describe.current.tags("headless");

/**
 * @param {Node} node
 * @returns {node is HTMLLinkElement | HTMLScriptElement}
 */
function isAssetElement(node) {
    return (
        node.nodeType === Node.ELEMENT_NODE &&
        ["LINK", "SCRIPT"].includes(node.nodeName)
    );
}

/**
 * @param {(node: HTMLLinkElement | HTMLScriptElement) => any} callback
 * @param {HTMLHeadElement} [head]
 */
const mockHeadAppendChild = (callback, head = document.head) => {
    patchWithCleanup(head, {
        appendChild(node) {
            if (!isAssetElement(node)) {
                throw new Error("Expected an asset element");
            }
            callback(node);
            return node;
        },
    });
};

const bundles = {
    "/web/bundle/test.bundle": [
        { type: "link", src: "file1.css" },
        { type: "link", src: "file2.css" },
        { type: "script", src: "file1.js" },
        { type: "script", src: "file2.js" },
    ],
};

beforeEach(() => {
    globalBundleCache.clear();
    esmBundleCache.clear();
    assetCacheByDocument.delete(document);
});

/** @type {Promise<any>[]} */
let pendingLoads = [];

/**
 * @param {Promise<any>} prom
 * @returns {Promise<any>}
 */
const startLoad = (prom) => {
    pendingLoads.push(prom.catch(() => {}));
    return prom;
};

afterEach(async () => {
    window.dispatchEvent(new Event("pagehide"));
    await Promise.all(pendingLoads);
    pendingLoads = [];
});

test("loadJS: load invalid JS lib", async () => {
    expect.assertions(3 * 4 + 1);

    patchWithCleanup(assets, { retries: { count: 3, delay: 1, extraDelay: 1 } });

    mockHeadAppendChild((node) => {
        expect(node).toBeInstanceOf(HTMLScriptElement);
        expect(node).toHaveAttribute("type", "text/javascript");
        expect(node).toHaveAttribute("src", "/some/invalid/file.js");

        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadJS("/some/invalid/file.js")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.js failed/,
        { message: "Trying to load an invalid file rejects the promise" },
    );
});

test("loadJS: a bundle URL fails fast, the way a stylesheet bundle does", async () => {
    patchWithCleanup(assets, { retries: { count: 3, delay: 1, extraDelay: 1 } });
    let appended = 0;
    mockHeadAppendChild((node) => {
        appended++;
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadJS("/web/assets/1/bundle.js")).rejects.toThrow(
        /The loading of \/web\/assets\/1\/bundle.js failed/,
    );
    expect(appended).toBe(1);
});

test("loadJS: concurrent loads of the same url share one script + retry chain", async () => {
    patchWithCleanup(assets, { retries: { count: 3, delay: 1, extraDelay: 1 } });
    let appended = 0;
    mockHeadAppendChild((node) => {
        appended++;
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    const first = loadJS("/dedupe/file.js");
    const second = loadJS("/dedupe/file.js");
    expect(second).toBe(first);

    await expect(first).rejects.toThrow(/The loading of \/dedupe\/file.js failed/);
    expect(appended).toBe(4);
});

test("loadJS: inserted scripts opt out of async execution", async () => {
    expect.assertions(1);

    mockHeadAppendChild((node) => {
        expect(/** @type {HTMLScriptElement} */ (node).async).toBe(false, {
            message: "scripts must execute in insertion order",
        });
        manuallyDispatchProgrammaticEvent(node, "load");
    });

    await loadJS("/some/ordered/file.js");
});

test("loadCSS: load invalid CSS lib", async () => {
    expect.assertions(4 * 4 + 1);

    assets.retries = { count: 3, delay: 1, extraDelay: 1 };

    mockHeadAppendChild((node) => {
        expect(node).toBeInstanceOf(HTMLLinkElement);
        expect(node).toHaveAttribute("rel", "stylesheet");
        expect(node).toHaveAttribute("type", "text/css");
        expect(node).toHaveAttribute("href", "/some/invalid/file.css");

        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadCSS("/some/invalid/file.css")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.css failed/,
        { message: "Trying to load an invalid file rejects the promise" },
    );
});

test("loadCSS: concurrent loads of the same url share one link + retry chain", async () => {
    patchWithCleanup(assets, {
        retries: { count: 3, delay: 1, extraDelay: 1 },
    });
    let appended = 0;
    mockHeadAppendChild((node) => {
        appended++;
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    const first = loadCSS("/dedupe/file.css");
    const second = loadCSS("/dedupe/file.css");
    expect(second).toBe(first);

    await expect(first).rejects.toThrow(/The loading of \/dedupe\/file.css failed/);
    expect(appended).toBe(4);
});

test("loadCSS: content-addressed bundle URLs fail fast without retries", async () => {
    patchWithCleanup(assets, {
        retries: { count: 3, delay: 1, extraDelay: 1 },
    });
    let appended = 0;
    mockHeadAppendChild((node) => {
        appended++;
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadCSS("/web/assets/1/web.assets_web.min.css")).rejects.toThrow(
        /The loading of \/web\/assets\/1\/web.assets_web.min.css failed/,
    );
    expect(appended).toBe(1);
});

/** @param {(node: Node) => void} [afterAppend] */
const attachForRealThenFail = (afterAppend) => {
    const realAppendChild = document.head.appendChild.bind(document.head);
    mockHeadAppendChild((node) => {
        realAppendChild(node);
        afterAppend?.(node);
        manuallyDispatchProgrammaticEvent(node, "error");
        return node;
    });
};

test("loadCSS: a failed link is detached from the head", async () => {
    patchWithCleanup(assets, { retries: { count: 0, delay: 1, extraDelay: 1 } });
    const url = "data:text/css,/*never-loads*/";
    /** @type {Node | null} */
    let attached = null;
    attachForRealThenFail((node) => {
        attached = node;
        expect(/** @type {Element} */ (node).isConnected).toBe(true);
    });

    await expect(loadCSS(url)).rejects.toThrow(/failed/);
    expect(/** @type {any} */ (attached).isConnected).toBe(false, {
        message: "the failed <link> must not stay in the head",
    });
});

test("loadJS: a failed script is detached from the head", async () => {
    const url = "data:text/javascript,/*never-loads*/";
    /** @type {Node | null} */
    let attached = null;
    attachForRealThenFail((node) => {
        attached = node;
        expect(/** @type {Element} */ (node).isConnected).toBe(true);
    });

    await expect(loadJS(url)).rejects.toThrow(/failed/);
    expect(/** @type {any} */ (attached).isConnected).toBe(false, {
        message: "the failed <script> must not stay in the head",
    });
});

test("loadBundle: load js and css files", async () => {
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`,
        );
    });

    startLoad(loadBundle("test.bundle"));
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add LINK - text/css - file1.css",
        "add LINK - text/css - file2.css",
        "add SCRIPT - text/javascript - file1.js",
        "add SCRIPT - text/javascript - file2.js",
    ]);
});

test("loadBundle: load only js files", async () => {
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`,
        );
    });

    startLoad(loadBundle("test.bundle", { css: false }));
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add SCRIPT - text/javascript - file1.js",
        "add SCRIPT - text/javascript - file2.js",
    ]);
});

test("loadBundle: load only css files", async () => {
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`,
        );
    });

    startLoad(loadBundle("test.bundle", { js: false }));
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add LINK - text/css - file1.css",
        "add LINK - text/css - file2.css",
    ]);
});

test("loadBundle: load same bundle in main document and an iframe", async () => {
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add document ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`,
        );
    });

    const iframe = document.createElement("iframe");
    document.body.appendChild(iframe);
    const iframeDocument = iframe.contentDocument;
    mockHeadAppendChild((node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add iframe document ${node.tagName} - ${node.type} - ${node.getAttribute(
                srcAttribute,
            )}`,
        );
    }, iframeDocument.head);

    startLoad(loadBundle("test.bundle"));
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add document LINK - text/css - file1.css",
        "add document LINK - text/css - file2.css",
        "add document SCRIPT - text/javascript - file1.js",
        "add document SCRIPT - text/javascript - file2.js",
    ]);

    const iframeLoad = loadBundle("test.bundle", { targetDoc: iframeDocument });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add iframe document LINK - text/css - file1.css",
        "add iframe document LINK - text/css - file2.css",
        "add iframe document SCRIPT - text/javascript - file1.js",
        "add iframe document SCRIPT - text/javascript - file2.js",
    ]);

    iframe.remove();
    await expect(iframeLoad).rejects.toThrow(/was interrupted: the page was hidden/);
});

test("loadBundle: load same bundles in 2 iframes", async () => {
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add document ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`,
        );
    });

    const iframeFirst = document.createElement("iframe");
    const iframeSecond = document.createElement("iframe");
    document.body.appendChild(iframeFirst);
    document.body.appendChild(iframeSecond);
    const iframeDocumentFirst = iframeFirst.contentDocument;
    const iframeDocumentSecond = iframeSecond.contentDocument;
    mockHeadAppendChild((node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add iframe document ${node.tagName} - ${node.type} - ${node.getAttribute(
                srcAttribute,
            )}`,
        );
    }, iframeDocumentFirst.head);
    mockHeadAppendChild((node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add iframe document ${node.tagName} - ${node.type} - ${node.getAttribute(
                srcAttribute,
            )}`,
        );
    }, iframeDocumentSecond.head);

    const firstLoad = loadBundle("test.bundle", { targetDoc: iframeDocumentFirst });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add iframe document LINK - text/css - file1.css",
        "add iframe document LINK - text/css - file2.css",
        "add iframe document SCRIPT - text/javascript - file1.js",
        "add iframe document SCRIPT - text/javascript - file2.js",
    ]);

    const secondLoad = loadBundle("test.bundle", { targetDoc: iframeDocumentSecond });
    await animationFrame();
    expect.verifySteps([
        "add iframe document LINK - text/css - file1.css",
        "add iframe document LINK - text/css - file2.css",
        "add iframe document SCRIPT - text/javascript - file1.js",
        "add iframe document SCRIPT - text/javascript - file2.js",
    ]);

    iframeFirst.remove();
    iframeSecond.remove();
    await expect(firstLoad).rejects.toThrow(/was interrupted: the page was hidden/);
    await expect(secondLoad).rejects.toThrow(/was interrupted: the page was hidden/);
});

test("getBundle: non-ok JSON response rejects and is not cached", async () => {
    let failRequests = true;
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        if (failRequests) {
            return new Response(JSON.stringify({ error: "Bad Gateway" }), {
                status: 502,
                headers: { "Content-Type": "application/json" },
            });
        }
        return bundles[route.pathname];
    });

    await expect(assets.getBundle("test.bundle")).rejects.toThrow(AssetsLoadingError);

    failRequests = false;
    const bundle = await assets.getBundle("test.bundle");
    expect(bundle.cssLibs).toEqual(["file1.css", "file2.css"]);
    expect(bundle.jsLibs).toEqual(["file1.js", "file2.js"]);
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "fetch bundle: /web/bundle/test.bundle",
    ]);
});

test("getBundle: successful response is cached (single fetch for two calls)", async () => {
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    const first = await assets.getBundle("test.bundle");
    const second = await assets.getBundle("test.bundle");
    expect(second).toBe(first);
    expect.verifySteps(["fetch bundle: /web/bundle/test.bundle"]);
});

test("loadESMBundle: same-document imports specifiers and registers them on odoo.loader", async () => {
    const registered = [];
    patchWithCleanup(odoo.loader, {
        registerNativeModules: (modules) => registered.push(modules),
    });

    const spec = "data:text/javascript,export const answer = 42;";
    await assets.loadESMBundle([spec]);

    expect(registered.length).toBe(1);
    expect(registered[0][spec].answer).toBe(42);
});

test("loadESMBundle: a specifier list the page already walked is not walked again", async () => {
    const registered = [];
    patchWithCleanup(odoo.loader, {
        registerNativeModules: (modules) => registered.push(modules),
    });
    const marker = `__esm_specifier_${Date.now()}`;
    const spec = `data:text/javascript,globalThis.${marker} = (globalThis.${marker} || 0) + 1;`;

    await assets.loadESMBundle([spec]);
    const second = assets.loadESMBundle([spec]);
    expect(registered.length).toBe(1);
    await second;
    expect(registered.length).toBe(1);
    expect(globalThis[marker]).toBe(1);
    delete globalThis[marker];
});

test("loadESMBundle: a specifier the loader already holds is that module, not a second import", async () => {
    const registered = [];
    const held = { answer: 42 };
    const spec = "@web/../tests/assets_test_already_held";
    odoo.loader.modules.set(spec, held);
    after(() => odoo.loader.modules.delete(spec));
    patchWithCleanup(odoo.loader, {
        registerNativeModules: (modules) => registered.push(modules),
    });

    await assets.loadESMBundle([spec], {
        importMap: { [spec]: "data:text/javascript,export const answer = 'other';" },
    });

    expect(registered.length).toBe(1);
    expect(registered[0][spec]).toBe(held);
});

test("loadESMBundle: a failed specifier walk is retried on the next load", async () => {
    patchWithCleanup(odoo.loader, { registerNativeModules: () => {} });
    const spec = "data:text/javascript,throw new Error('boom');";

    await expect(assets.loadESMBundle([spec])).rejects.toThrow();
    expect(esmBundleCache.has(JSON.stringify([spec]))).toBe(false);
});

test("loadBundle: a compiled runtime bundle is one import(), not a specifier walk", async () => {
    const registered = [];
    patchWithCleanup(odoo.loader, {
        registerNativeModules: (modules) => registered.push(modules),
    });
    const marker = `__esm_bundle_${Date.now()}`;
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return {
            is_esm: true,
            esm_url: `data:text/javascript,globalThis.${marker} = (globalThis.${marker} || 0) + 1;`,
            specifiers: ["@web/ignored"],
            import_map: {},
            files: [],
            template_url: null,
        };
    });

    await loadBundle("compiled.bundle");
    await loadBundle("compiled.bundle");
    expect.verifySteps(["fetch bundle: /web/bundle/compiled.bundle"]);
    expect(globalThis[marker]).toBe(1);
    expect(registered).toEqual([]);
    delete globalThis[marker];
});

test("loadBundle: a compiled runtime bundle reaches another document as a module script", async () => {
    const { iframe, targetDoc, captured } = makeCrossDocTarget(new Map());
    mockFetch(() => ({
        is_esm: true,
        esm_url: "/web/assets/esm/abc/lazy.esm.js",
        specifiers: [],
        import_map: { luxon: "/web/static/lib/luxon/luxon.js" },
        files: [],
        template_url: null,
    }));

    startLoad(loadBundle("compiled.crossdoc", { targetDoc }));
    await animationFrame();
    const script = captured.find((n) => n.tagName === "SCRIPT" && n.type === "module");
    expect(script).not.toBe(undefined);
    expect(script.getAttribute("src")).toBe("/web/assets/esm/abc/lazy.esm.js");
    const imports = getInjectedImports(captured);
    expect(imports.luxon).toBe("/web/static/lib/luxon/luxon.js");
    iframe.remove();
});

/** @param {Map<string, object>} modules */
const makeCrossDocTarget = (modules) => {
    const iframe = document.createElement("iframe");
    document.body.appendChild(iframe);
    const targetDoc = iframe.contentDocument;
    const targetWin = iframe.contentWindow;
    if (!targetDoc || !targetWin) {
        throw new Error("Test iframe is unavailable");
    }
    Object.assign(targetWin, { odoo: { loader: { modules } } });
    /** @type {HTMLScriptElement[]} */
    const captured = [];
    patchWithCleanup(targetDoc.head, {
        appendChild: (node) => {
            if (!(node instanceof targetDoc.createElement("script").constructor)) {
                throw new Error("Expected a script element");
            }
            captured.push(
                /** @type {HTMLScriptElement} */ (/** @type {Node} */ (node)),
            );
            return node;
        },
    });
    return { iframe, targetDoc, targetWin, captured };
};

/** @param {Node[]} captured */
const getInjectedImports = (captured) => {
    const mapNode = captured.find(
        (n) =>
            n.nodeName === "SCRIPT" &&
            /** @type {HTMLScriptElement} */ (n).type === "importmap",
    );
    return mapNode ? JSON.parse(mapNode.textContent || "{}").imports : null;
};

test("loadESMBundle: cross-document builds bridge import map, reusing server bridges", async () => {
    const { iframe, targetDoc, targetWin, captured } = makeCrossDocTarget(
        new Map([
            ["@web/foo", { bar: 1, default: {} }],
            ["@web/served", { baz: 2 }],
            ["@web/own", { qux: 3 }],
            ["@odoo/owl", { Component: 1 }],
        ]),
    );
    const serverMap = {
        "@web/served": "/web/assets/esm/bridges/abc.js",
        "@web/own": "/web/own/static/src/own.js",
        "@web/extra": "/web/assets/esm/bridges/def.js",
    };

    const promise = assets.loadESMBundle(["@web/served"], {
        targetDoc,
        importMap: serverMap,
    });
    const imports = getInjectedImports(captured);

    expect(imports["@web/foo"].startsWith("data:")).toBe(true);
    expect(imports["/web/static/src/foo.js"]).toBe(imports["@web/foo"]);
    const fooSrc = decodeURIComponent(
        imports["@web/foo"].slice("data:text/javascript,".length),
    );
    expect(fooSrc.includes('odoo.loader.modules.get("@web/foo")')).toBe(true);
    expect(fooSrc.includes("_e0 = _m.bar;")).toBe(true);
    expect(fooSrc.includes("_e0 as bar")).toBe(true);

    expect(imports["@web/served"]).toBe("/web/assets/esm/bridges/abc.js");
    expect(imports["/web/static/src/served.js"]).toBe("/web/assets/esm/bridges/abc.js");

    expect(imports["@web/own"]).toBe("/web/own/static/src/own.js");
    expect(imports["/web/static/src/own.js"].startsWith("data:")).toBe(true);

    expect(imports["@odoo/owl"]).toBe(undefined);

    expect(imports["@web/extra"]).toBe("/web/assets/esm/bridges/def.js");

    const scriptNode = captured.find((n) => n.type === "module");
    if (!scriptNode) {
        throw new Error("No module script was injected");
    }
    expect(Boolean(scriptNode)).toBe(true);
    const token = (scriptNode.textContent || "").match(
        /__odoo_esm_bundle_loaded_(\d+)/,
    )?.[1];
    targetWin.dispatchEvent(new Event(`__odoo_esm_bundle_loaded_${token}`));
    await expect(promise).resolves.toBe(undefined);

    iframe.remove();
});

test("loadESMBundle: a specifier the document already maps is imported by URL", async () => {
    const { iframe, targetDoc, targetWin, captured } = makeCrossDocTarget(new Map());
    targetDoc.head.innerHTML =
        '<script type="importmap">' +
        JSON.stringify({
            imports: { "@web/claimed": "/web/assets/esm/bridges/dead.js" },
        }) +
        "</" +
        "script>";

    const promise = assets.loadESMBundle(["@web/claimed", "@web/free"], {
        targetDoc,
        importMap: {
            "@web/claimed": "/web/static/src/claimed.js",
            "@web/free": "/web/static/src/free.js",
        },
    });

    const imports = getInjectedImports(captured);
    expect(imports["@web/claimed"]).toBe(undefined);
    expect(imports["@web/free"]).toBe("/web/static/src/free.js");

    const scriptNode = captured.find((n) => n.type === "module");
    if (!scriptNode) {
        throw new Error("No module script was injected");
    }
    const pairs = JSON.parse(
        (scriptNode.textContent || "").match(/const specs = (\[[\s\S]*\]);/)?.[1] ||
            "null",
    );
    const bySpec = Object.fromEntries(pairs);
    expect(bySpec["@web/claimed"].endsWith("/web/static/src/claimed.js")).toBe(true);
    expect(bySpec["@web/free"]).toBe("@web/free");

    const token = (scriptNode.textContent || "").match(
        /__odoo_esm_bundle_loaded_(\d+)/,
    )?.[1];
    targetWin.dispatchEvent(new Event(`__odoo_esm_bundle_loaded_${token}`));
    await expect(promise).resolves.toBe(undefined);
    iframe.remove();
});

test("loadESMBundle: re-declaring the same target is not a conflict", async () => {
    const { iframe, targetDoc, targetWin, captured } = makeCrossDocTarget(new Map());
    targetDoc.head.innerHTML =
        '<script type="importmap">' +
        JSON.stringify({ imports: { "@web/same": "/web/static/src/same.js" } }) +
        "</" +
        "script>";

    const promise = assets.loadESMBundle(["@web/same"], {
        targetDoc,
        importMap: { "@web/same": "/web/static/src/same.js" },
    });

    const scriptNode = captured.find((n) => n.type === "module");
    if (!scriptNode) {
        throw new Error("No module script was injected");
    }
    const pairs = JSON.parse(
        (scriptNode.textContent || "").match(/const specs = (\[[\s\S]*\]);/)?.[1] ||
            "null",
    );
    expect(Object.fromEntries(pairs)["@web/same"]).toBe("@web/same");

    const token = (scriptNode.textContent || "").match(
        /__odoo_esm_bundle_loaded_(\d+)/,
    )?.[1];
    targetWin.dispatchEvent(new Event(`__odoo_esm_bundle_loaded_${token}`));
    await expect(promise).resolves.toBe(undefined);
    iframe.remove();
});

test("loadESMBundle: cross-document rejects with the injected script's error detail", async () => {
    const { iframe, targetDoc, targetWin, captured } = makeCrossDocTarget(new Map());

    const promise = assets.loadESMBundle(["@web/x"], {
        targetDoc,
        importMap: { "@web/x": "data:text/javascript,export default 1" },
    });
    const scriptNode = captured.find((n) => n.type === "module");
    if (!scriptNode) {
        throw new Error("No module script was injected");
    }
    const token = (scriptNode.textContent || "").match(
        /__odoo_esm_bundle_error_(\d+)/,
    )?.[1];
    targetWin.dispatchEvent(
        new CustomEvent(`__odoo_esm_bundle_error_${token}`, {
            detail: new Error("boom in iframe"),
        }),
    );
    await expect(promise).rejects.toThrow(/boom in iframe/);

    iframe.remove();
});

test("loadBundle: an iframe's own assets are not requested again", async () => {
    mockFetch((input) => {
        const route = /** @type {URL} */ (input);
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    const iframe = document.createElement("iframe");
    document.body.appendChild(iframe);
    const iframeDocument = iframe.contentDocument;
    const existingLink = iframeDocument.createElement("link");
    existingLink.rel = "stylesheet";
    existingLink.setAttribute("href", "file1.css");
    iframeDocument.head.appendChild(existingLink);
    const existingScript = iframeDocument.createElement("script");
    existingScript.setAttribute("src", "file1.js");
    iframeDocument.head.appendChild(existingScript);

    mockHeadAppendChild((node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(`add ${node.tagName} ${node.getAttribute(srcAttribute)}`);
    }, iframeDocument.head);

    const iframeLoad = loadBundle("test.bundle", { targetDoc: iframeDocument });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add LINK file2.css",
        "add SCRIPT file2.js",
    ]);

    iframe.remove();
    await expect(iframeLoad).rejects.toThrow(/was interrupted: the page was hidden/);
});

test("getBundle: a classic descriptor naming only ESM chunks fails loudly", async () => {
    mockFetch(
        () =>
            new Response(
                JSON.stringify([
                    { type: "link", src: "/web/assets/x/bundle.min.css" },
                    { type: "script", src: null },
                    { type: "script", src: "/web/assets/esm/abc/bundle.esm.js" },
                ]),
                { headers: { "Content-Type": "application/json" } },
            ),
    );
    await expect(assets.getBundle("test.mislabelled")).rejects.toThrow(
        /named 1 ESM chunk\(s\) and no loadable script/,
    );
});

test("getBundle: an ESM chunk alongside a real script is still just skipped", async () => {
    mockFetch(
        () =>
            new Response(
                JSON.stringify([
                    { type: "link", src: "/web/assets/x/bundle.min.css" },
                    { type: "script", src: "/web/assets/esm/abc/bundle.esm.js" },
                    { type: "script", src: "/web/assets/x/bundle.min.js" },
                ]),
                { headers: { "Content-Type": "application/json" } },
            ),
    );
    const bundle = await assets.getBundle("test.mixed");
    expect(bundle.jsLibs).toEqual(["/web/assets/x/bundle.min.js"]);
    expect(bundle.cssLibs).toEqual(["/web/assets/x/bundle.min.css"]);
});

describe("a target document that cannot take the element", () => {
    function headlessDocument() {
        return /** @type {Document} */ (
            document.implementation.createDocument(null, null, null)
        );
    }

    test("loadJS rejects rather than hanging", async () => {
        const targetDoc = headlessDocument();
        await expect(assets.loadJS("/some/where.js", { targetDoc })).rejects.toThrow(
            /could not take it/,
        );
    });

    test("loadCSS rejects rather than hanging", async () => {
        const targetDoc = headlessDocument();
        await expect(assets.loadCSS("/some/where.css", { targetDoc })).rejects.toThrow(
            /could not take it/,
        );
    });

    test("a failed mount leaves nothing cached, so a later load can succeed", async () => {
        const targetDoc = headlessDocument();
        await expect(assets.loadJS("/twice.js", { targetDoc })).rejects.toThrow();
        await expect(assets.loadJS("/twice.js", { targetDoc })).rejects.toThrow();
    });
});

describe("the whenReady re-seed", () => {
    /** @returns {Document} */
    function parsedDocument() {
        return new DOMParser().parseFromString(
            `<!doctype html><html><head></head><body></body></html>`,
            "text/html",
        );
    }

    /**
     * @param {Document} doc
     * @param {string} src
     */
    function appendScript(doc, src) {
        const el = doc.createElement("script");
        el.setAttribute("src", src);
        doc.head.appendChild(el);
    }

    test("creating the cache seeds it from whatever head already holds", () => {
        const doc = parsedDocument();
        appendScript(doc, "/early.js");
        loadJS("/early.js", { targetDoc: doc });
        expect([...(assetCacheByDocument.get(doc)?.keys() ?? [])]).toEqual([
            "/early.js",
        ]);
        expect(doc.head.querySelectorAll("script[src]")).toHaveLength(1);
    });

    test("a script that enters head after the cache exists is re-injected without a re-seed", () => {
        const doc = parsedDocument();
        appendScript(doc, "/early.js");
        loadJS("/early.js", { targetDoc: doc });

        appendScript(doc, "/late.js");
        expect(assetCacheByDocument.get(doc)?.has("/late.js")).toBe(false);

        loadJS("/late.js", { targetDoc: doc }).catch(() => {});
        expect(doc.head.querySelectorAll('script[src="/late.js"]')).toHaveLength(2);
    });

    test("re-seeding an existing cache makes the later script known", () => {
        const doc = parsedDocument();
        appendScript(doc, "/early.js");
        loadJS("/early.js", { targetDoc: doc });

        appendScript(doc, "/late.js");
        assets.reseedFromDocument(doc);
        expect(assetCacheByDocument.get(doc)?.has("/late.js")).toBe(true);

        loadJS("/late.js", { targetDoc: doc });
        expect(doc.head.querySelectorAll('script[src="/late.js"]')).toHaveLength(1);
    });
});
