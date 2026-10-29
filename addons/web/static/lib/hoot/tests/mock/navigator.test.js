/** @odoo-module */

import {
    describe,
    expect,
    microTick,
    mockPermission,
    mockSendBeacon,
    mockTouch,
    mockVibrate,
    test,
} from "@odoo/hoot";
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
        test.tags("secure");
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

    describe("permission-gated APIs", () => {
        test("geolocation positions are never available", async () => {
            const onSuccess = () => expect.step("success");
            const onError = (error) => expect.step(`error:${error.code}`);

            navigator.geolocation.getCurrentPosition(onSuccess, onError);

            expect.verifySteps([]);

            await microTick();

            expect.verifySteps(["error:1"]); // PERMISSION_DENIED

            mockPermission("geolocation", "granted");
            navigator.geolocation.watchPosition(onSuccess, onError);
            await microTick();

            expect.verifySteps(["error:2"]); // POSITION_UNAVAILABLE
        });

        test.tags("secure");
        test("permission-gated requests are rejected", async () => {
            await expect(navigator.credentials.get()).rejects.toThrow(/not allowed/);
            await expect(navigator.storage.getDirectory()).rejects.toThrow(/not allowed/);
            await expect(navigator.storage.persist()).resolves.toBe(false);
            await expect(navigator.wakeLock.request("screen")).rejects.toThrow(/not allowed/);
        });
    });

    test("unmocked native methods can be called", () => {
        expect(navigator.javaEnabled()).toBe(false);
        expect(navigator.javaEnabled).toBe(navigator.javaEnabled);
    });

    test("permission statuses are notified of their changes", async () => {
        const camera = await navigator.permissions.query({ name: "camera" });
        camera.onchange = () => expect.step(camera.state);

        mockPermission("camera", "granted");

        expect.verifySteps(["granted"]);
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
