/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("setup network values", async () => {
        expect(document.cookie).toBe("");

        document.cookie = "cids=4";
        document.title = "kek";

        expect(document.cookie).toBe("cids=4");
        expect(document.title).toBe("kek");
    });

    test("values are reset between test", async () => {
        expect(document.cookie).toBe("");
        expect(document.title).toBe("");
    });
});
