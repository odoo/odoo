import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { mockFetch } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import {
    assets,
    assetCacheByDocument,
    globalBundleCache,
    loadBundle,
    loadCSS,
    loadJS,
} from "@web/core/assets";

describe.current.tags("headless");

/**
 * @param {(node: Node) => void} callback
 */
const mockHeadAppendChild = (callback) => {
    patchWithCleanup(document.head, {
        appendChild: callback,
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
    assetCacheByDocument.delete(document);
});

test("loadJS: load invalid JS lib", async () => {
    expect.assertions(4);

    mockHeadAppendChild((node) => {
        expect(node).toBeInstanceOf(HTMLScriptElement);
        expect(node).toHaveAttribute("type", "text/javascript");
        expect(node).toHaveAttribute("src", "/some/invalid/file.js");

        // Simulates a failed request to an invalid file.
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadJS("/some/invalid/file.js")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.js failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );
});

test("loadCSS: load invalid CSS lib", async () => {
    expect.assertions(4 * 4 + 1);

    assets.retries = { count: 3, delay: 1, extraDelay: 1 }; // Fail fast.

    mockHeadAppendChild((node) => {
        expect(node).toBeInstanceOf(HTMLLinkElement);
        expect(node).toHaveAttribute("rel", "stylesheet");
        expect(node).toHaveAttribute("type", "text/css");
        expect(node).toHaveAttribute("href", "/some/invalid/file.css");

        // Simulates a failed request to an invalid file.
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadCSS("/some/invalid/file.css")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.css failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );
});

test("loadBundle: load js and css files", async () => {
    mockFetch((route) => {
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(`add ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`);
    });

    loadBundle("test.bundle");
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
    mockFetch((route) => {
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(`add ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`);
    });

    loadBundle("test.bundle", { css: false });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add SCRIPT - text/javascript - file1.js",
        "add SCRIPT - text/javascript - file2.js",
    ]);
});

test("loadBundle: load only css files", async () => {
    mockFetch((route) => {
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(`add ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`);
    });

    loadBundle("test.bundle", { js: false });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add LINK - text/css - file1.css",
        "add LINK - text/css - file2.css",
    ]);
});

test("loadBundle: load same bundle in main document and an iframe", async () => {
    mockFetch((route) => {
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add document ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`
        );
    });

    const iframe = document.createElement("iframe");
    document.body.appendChild(iframe);
    const iframeDocument = iframe.contentDocument;
    patchWithCleanup(iframeDocument.head, {
        appendChild: (node) => {
            const srcAttribute = node.tagName === "LINK" ? "href" : "src";
            expect.step(
                `add iframe document ${node.tagName} - ${node.type} - ${node.getAttribute(
                    srcAttribute
                )}`
            );
        },
    });

    loadBundle("test.bundle");
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add document LINK - text/css - file1.css",
        "add document LINK - text/css - file2.css",
        "add document SCRIPT - text/javascript - file1.js",
        "add document SCRIPT - text/javascript - file2.js",
    ]);

    loadBundle("test.bundle", { targetDoc: iframeDocument });
    await animationFrame();
    expect.verifySteps([
        // no fetching as the bundle is cached globally
        "add iframe document LINK - text/css - file1.css",
        "add iframe document LINK - text/css - file2.css",
        "add iframe document SCRIPT - text/javascript - file1.js",
        "add iframe document SCRIPT - text/javascript - file2.js",
    ]);

    iframe.remove();
});

test("loadBundle: load same bundles in 2 iframes", async () => {
    mockFetch((route) => {
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });

    mockHeadAppendChild(async (node) => {
        const srcAttribute = node.tagName === "LINK" ? "href" : "src";
        expect.step(
            `add document ${node.tagName} - ${node.type} - ${node.getAttribute(srcAttribute)}`
        );
    });

    const iframeFirst = document.createElement("iframe");
    const iframeSecond = document.createElement("iframe");
    document.body.appendChild(iframeFirst);
    document.body.appendChild(iframeSecond);
    const iframeDocumentFirst = iframeFirst.contentDocument;
    const iframeDocumentSecond = iframeSecond.contentDocument;
    patchWithCleanup(iframeDocumentFirst.head, {
        appendChild: (node) => {
            const srcAttribute = node.tagName === "LINK" ? "href" : "src";
            expect.step(
                `add iframe document ${node.tagName} - ${node.type} - ${node.getAttribute(
                    srcAttribute
                )}`
            );
        },
    });
    patchWithCleanup(iframeDocumentSecond.head, {
        appendChild: (node) => {
            const srcAttribute = node.tagName === "LINK" ? "href" : "src";
            expect.step(
                `add iframe document ${node.tagName} - ${node.type} - ${node.getAttribute(
                    srcAttribute
                )}`
            );
        },
    });

    loadBundle("test.bundle", { targetDoc: iframeDocumentFirst });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        "add iframe document LINK - text/css - file1.css",
        "add iframe document LINK - text/css - file2.css",
        "add iframe document SCRIPT - text/javascript - file1.js",
        "add iframe document SCRIPT - text/javascript - file2.js",
    ]);

    loadBundle("test.bundle", { targetDoc: iframeDocumentSecond });
    await animationFrame();
    expect.verifySteps([
        "add iframe document LINK - text/css - file1.css",
        "add iframe document LINK - text/css - file2.css",
        "add iframe document SCRIPT - text/javascript - file1.js",
        "add iframe document SCRIPT - text/javascript - file2.js",
    ]);

    iframeFirst.remove();
    iframeSecond.remove();
});
