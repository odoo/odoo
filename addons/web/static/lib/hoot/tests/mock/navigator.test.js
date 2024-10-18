/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { mockSendBeacon, mockTouch, mockVibrate } from "@odoo/hoot-mock";
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
        test.tags("secure")("read/write calls are resolved immediatly", async () => {
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

    test("maxTouchPoints", () => {
        mockTouch(false);

        expect(navigator.maxTouchPoints).toBe(0);

        mockTouch(true);

        expect(navigator.maxTouchPoints).toBe(1);
    });

    test("sendBeacon", () => {
        expect(() => navigator.sendBeacon("/route", new Blob([]))).toThrow(/sendBeacon/);

        mockSendBeacon(expect.step);

        expect.verifySteps([]);

        navigator.sendBeacon("/route", new Blob([]));

        expect.verifySteps(["/route"]);
    });

    test("vibrate", () => {
        expect(() => navigator.vibrate(100)).toThrow(/vibrate/);

        mockVibrate(expect.step);

        expect.verifySteps([]);

        navigator.vibrate(100);

        expect.verifySteps([100]);
    });
});
