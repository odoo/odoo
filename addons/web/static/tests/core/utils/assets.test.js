import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { assets, loadCSS, loadJS } from "@web/core/assets";

describe.current.tags("headless");

/**
 * @param {(node: Node) => void} callback
 */
const mockHeadAppendChild = (callback) =>
    patchWithCleanup(document.head, {
        appendChild: callback,
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
