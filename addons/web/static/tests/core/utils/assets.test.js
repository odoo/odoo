import { after, describe, expect, test } from "@odoo/hoot";
import { observe } from "@odoo/hoot-dom";

import { assets, loadCSS, loadJS } from "@web/core/assets";

describe.current.tags("headless");

test("loadJS: load invalid JS lib", async () => {
    expect.assertions(4);

    after(
        observe(document.head, (mutations) => {
            for (const mutation of mutations) {
                for (const script of mutation.addedNodes) {
                    expect(script).toBeInstanceOf(HTMLScriptElement);
                    expect(script).toHaveAttribute("type", "text/javascript");
                    expect(script).toHaveAttribute("src", "/some/invalid/file.js");

                    after(() => script.remove());
                }
            }
        })
    );

    await expect(loadJS("/some/invalid/file.js")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.js failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );
});

test("loadCSS: load invalid CSS lib", async () => {
    expect.assertions(4 * 4 + 1);

    assets.retries = { count: 3, delay: 1, extraDelay: 1 }; // Fail fast.

    after(
        observe(document.head, (mutations) => {
            for (const mutation of mutations) {
                for (const link of mutation.addedNodes) {
                    expect(link).toBeInstanceOf(HTMLLinkElement);
                    expect(link).toHaveAttribute("rel", "stylesheet");
                    expect(link).toHaveAttribute("type", "text/css");
                    expect(link).toHaveAttribute("href", "/some/invalid/file.css");

                    after(() => link.remove());
                }
            }
        })
    );

    await expect(loadCSS("/some/invalid/file.css")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.css failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );
});
