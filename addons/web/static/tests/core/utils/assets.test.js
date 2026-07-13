import {
    animationFrame,
    beforeEach,
    describe,
    expect,
    getFixture,
    manuallyDispatchProgrammaticEvent,
    mockFetch,
    test,
} from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { assets, loadBundle, loadCSS, loadJS } from "@web/core/assets";

describe.current.tags("headless");

function mountIframe() {
    const iframe = document.createElement("iframe");
    getFixture().appendChild(iframe);
    return iframe.contentDocument;
}

/**
 * @param {Document} doc
 * @param {(node: Node) => any} [callback]
 */
function stepOnAssetAppended(doc, callback) {
    patchWithCleanup(doc.head, {
        appendChild(node) {
            const srcAttribute = node.tagName === "LINK" ? "href" : "src";
            expect.step([doc, node.tagName, node.type, node.getAttribute(srcAttribute)]);

            callback?.(node);
        },
    });
}

const bundles = {
    "/web/bundle/test.bundle": [
        { type: "link", src: "file1.css" },
        { type: "link", src: "file2.css" },
        { type: "script", src: "file1.js" },
        { type: "script", src: "file2.js" },
    ],
};

beforeEach(() => {
    mockFetch((route) => {
        expect.step(`fetch bundle: ${route.pathname}`);
        return bundles[route.pathname];
    });
    patchWithCleanup(assets, {
        globalCache: new Map(),
        documentCaches: new WeakMap(),
    });
});

test("loadJS: load invalid JS lib", async () => {
    stepOnAssetAppended(document, (node) => {
        // Simulates a failed request to an invalid file.
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadJS("/some/invalid/file.js")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.js failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );

    expect.verifySteps([[document, "SCRIPT", "text/javascript", "/some/invalid/file.js"]]);
});

test("loadCSS: load invalid CSS lib", async () => {
    patchWithCleanup(assets.retries, {
        count: 3,
        delay: 1, // Fail fast.
        extraDelay: 1,
    });

    stepOnAssetAppended(document, (node) => {
        // Simulates a failed request to an invalid file.
        manuallyDispatchProgrammaticEvent(node, "error");
    });

    await expect(loadCSS("/some/invalid/file.css")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.css failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );

    expect.verifySteps([
        // First try
        [document, "LINK", "text/css", "/some/invalid/file.css"],
        // 3 other tries
        [document, "LINK", "text/css", "/some/invalid/file.css"],
        [document, "LINK", "text/css", "/some/invalid/file.css"],
        [document, "LINK", "text/css", "/some/invalid/file.css"],
    ]);
});

test("loadBundle: load js and css files", async () => {
    stepOnAssetAppended(document);

    loadBundle("test.bundle");
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        [document, "LINK", "text/css", "file1.css"],
        [document, "LINK", "text/css", "file2.css"],
        [document, "SCRIPT", "text/javascript", "file1.js"],
        [document, "SCRIPT", "text/javascript", "file2.js"],
    ]);
});

test("loadBundle: load only js files", async () => {
    stepOnAssetAppended(document);

    loadBundle("test.bundle", { css: false });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        [document, "SCRIPT", "text/javascript", "file1.js"],
        [document, "SCRIPT", "text/javascript", "file2.js"],
    ]);
});

test("loadBundle: load only css files", async () => {
    stepOnAssetAppended(document);

    loadBundle("test.bundle", { js: false });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        [document, "LINK", "text/css", "file1.css"],
        [document, "LINK", "text/css", "file2.css"],
    ]);
});

test("loadBundle: load same bundle in main document and an iframe", async () => {
    const iframeDoc = mountIframe();

    stepOnAssetAppended(document);
    stepOnAssetAppended(iframeDoc);

    loadBundle("test.bundle");
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        [document, "LINK", "text/css", "file1.css"],
        [document, "LINK", "text/css", "file2.css"],
        [document, "SCRIPT", "text/javascript", "file1.js"],
        [document, "SCRIPT", "text/javascript", "file2.js"],
    ]);

    loadBundle("test.bundle", { targetDoc: iframeDoc });
    await animationFrame();
    expect.verifySteps([
        // no fetching as the bundle is cached globally
        [iframeDoc, "LINK", "text/css", "file1.css"],
        [iframeDoc, "LINK", "text/css", "file2.css"],
        [iframeDoc, "SCRIPT", "text/javascript", "file1.js"],
        [iframeDoc, "SCRIPT", "text/javascript", "file2.js"],
    ]);
});

test("loadBundle: load same bundles in 2 iframes", async () => {
    const firstDoc = mountIframe();
    const secondDoc = mountIframe();

    stepOnAssetAppended(document); // Nothing should be added in this test
    stepOnAssetAppended(firstDoc);
    stepOnAssetAppended(secondDoc);

    loadBundle("test.bundle", { targetDoc: firstDoc });
    await animationFrame();
    expect.verifySteps([
        "fetch bundle: /web/bundle/test.bundle",
        [firstDoc, "LINK", "text/css", "file1.css"],
        [firstDoc, "LINK", "text/css", "file2.css"],
        [firstDoc, "SCRIPT", "text/javascript", "file1.js"],
        [firstDoc, "SCRIPT", "text/javascript", "file2.js"],
    ]);

    loadBundle("test.bundle", { targetDoc: secondDoc });
    await animationFrame();
    expect.verifySteps([
        [secondDoc, "LINK", "text/css", "file1.css"],
        [secondDoc, "LINK", "text/css", "file2.css"],
        [secondDoc, "SCRIPT", "text/javascript", "file1.js"],
        [secondDoc, "SCRIPT", "text/javascript", "file2.js"],
    ]);
});
