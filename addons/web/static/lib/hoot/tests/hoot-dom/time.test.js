/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import {
    Deferred,
    advanceTime,
    animationFrame,
    microTick,
    runAllTimers,
    tick,
    waitUntil,
} from "@odoo/hoot-dom";
import { parseUrl } from "../local_helpers";

// timeout of 1 second to ensure all timeouts are actually mocked
describe.timeout(1_000);
describe(parseUrl(import.meta.url), () => {
    test("advanceTime", async () => {
        expect.assertions(8);

        await advanceTime(5_000);

        const timeoutId = window.setTimeout(() => expect.step("timeout"), "2000");
        const intervalId = window.setInterval(() => expect.step("interval"), 3_000);
        const animationHandle = window.requestAnimationFrame((delta) => {
            expect(delta).toBeGreaterThan(5_000);
            expect.step("animation");
        });

        expect(timeoutId).toBeGreaterThan(0);
        expect(intervalId).toBeGreaterThan(0);
        expect(animationHandle).toBeGreaterThan(0);
        expect.verifySteps([]);

        await advanceTime(10_000); // 10 seconds

        expect.verifySteps(["animation", "timeout", "interval", "interval", "interval"]);

        await advanceTime(10_000);

        expect.verifySteps(["interval", "interval", "interval"]);

        window.clearInterval(intervalId);

        await advanceTime(10_000);

        expect.verifySteps([]);
    });

    test("Deferred", async () => {
        const def = new Deferred();

        def.then(() => expect.step("resolved"));

        expect.step("before");

        def.resolve(14);

        expect.step("after");

        await expect(def).resolves.toBe(14);

        expect.verifySteps(["before", "after", "resolved"]);
    });

    test("tick", async () => {
        let count = 0;

        const nextTickPromise = tick().then(() => ++count);

        expect(count).toBe(0);

        await expect(nextTickPromise).resolves.toBe(1);

        expect(count).toBe(1);
    });

    test("runAllTimers", async () => {
        expect.assertions(4);

        window.setTimeout(() => expect.step("timeout"), 1e6);
        window.requestAnimationFrame((delta) => {
            expect(delta).toBeGreaterThan(1);
            expect.step("animation");
        });

        expect.verifySteps([]);

        const ms = await runAllTimers();

        expect(ms).toBeCloseTo(1e6, { margin: 10 });
        expect.verifySteps(["animation", "timeout"]);
    });

    test("waitUntil: already true", async () => {
        const promise = waitUntil(() => "some value").then((value) => {
            expect.step("resolved");
            return value;
        });

        expect.verifySteps([]);
        expect(promise).toBeInstanceOf(Promise);

        await microTick();

        expect.verifySteps(["resolved"]);
        await expect(promise).resolves.toBe("some value");
    });

    test("waitUntil: rejects", async () => {
        await expect(waitUntil(() => false, { timeout: 0 })).rejects.toThrow();
    });

    test("waitUntil: lazy", async () => {
        let returnValue = "";
        const promise = waitUntil(() => returnValue).then((v) => expect.step(v));

        expect.verifySteps([]);
        expect(promise).toBeInstanceOf(Promise);

        await animationFrame();
        await animationFrame();

        expect.verifySteps([]);

        returnValue = "test";

        await animationFrame();

        expect.verifySteps(["test"]);
    });
});
