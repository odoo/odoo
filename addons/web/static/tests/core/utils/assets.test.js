import { expect, test } from "@odoo/hoot";

import { assets, loadJS, loadCSS } from "@web/core/assets";

test.tags("headless")("loadJS: load invalid JS lib", async () => {
    await expect(loadJS("/some/invalid/file.js")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.js failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );
    expect(document).toContain("script[src='/some/invalid/file.js']", {
        message: "Document contains a script with the src we asked to load",
    });
});

test.tags("headless")("loadCSS: load invalid CSS lib", async () => {
    assets.retries = { count: 3, delay: 1, extraDelay: 1 }; // Fail fast.
    await expect(loadCSS("/some/invalid/file.css")).rejects.toThrow(
        /The loading of \/some\/invalid\/file.css failed/,
        { message: "Trying to load an invalid file rejects the promise" }
    );
    expect(document).toContain("script[src='/some/invalid/file.css']", {
        message: "Document contains a link with the href we asked to load",
    });
});
