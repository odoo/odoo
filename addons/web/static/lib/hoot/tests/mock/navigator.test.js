/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { parseUrl } from "../local_helpers";

/**
 * @param {Promise<any>} promise
 */
const ensureResolvesImmediatly = (promise) =>
    Promise.race([
        promise,
        new Promise((resolve, reject) => reject("failed to resolve in a single micro tick")),
    ]);

describe(parseUrl(import.meta.url), () => {
    describe("clipboard", () => {
        test("read/write calls are resolved immediatly", async () => {
            navigator.clipboard.write([
                new ClipboardItem({
                    "text/plain": new Blob(["some text"], { type: "text/plain" }),
                }),
            ]);

            const items = await ensureResolvesImmediatly(navigator.clipboard.read());

            expect(items).toHaveLength(1);
            expect(items[0]).toBeInstanceOf(ClipboardItem);

            const blob = await ensureResolvesImmediatly(items[0].getType("text/plain"));

            expect(blob).toBeInstanceOf(Blob);

            const value = await ensureResolvesImmediatly(blob.text());

            expect(value).toBe("some text");
        });
    });
});
