/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { Deferred, advanceTime, runAllTimers, tick } from "@odoo/hoot-mock";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    // timeout of 1 second to ensure timeouts are actually mocked
    test.timeout(1_000)("advanceTime", async () => {
        expect.assertions(8);

        const timeoutId = window.setTimeout(() => expect.step("timeout"), 2_000);
        const intervalId = window.setInterval(() => expect.step("interval"), 3_000);
        const animationHandle = window.requestAnimationFrame((delta) => {
            expect(delta).toBeGreaterThan(0);
            expect.step("animation");
        });

        expect(timeoutId).toBeGreaterThan(0);
        expect(intervalId).toBeGreaterThan(0);
        expect(animationHandle).toBeGreaterThan(0);
        expect([]).toVerifySteps();

        await advanceTime(10_000); // 10 seconds

        expect(["animation", "timeout", "interval"]).toVerifySteps();

        await advanceTime(10_000);

        expect(["interval"]).toVerifySteps();

        window.clearInterval(intervalId);

        await advanceTime(10_000);

        expect([]).toVerifySteps();
    });

    test("Deferred", async () => {
        const def = new Deferred();

        def.then(() => expect.step("resolved"));

        expect.step("before");

        def.resolve(14);

        expect.step("after");

        await expect(def).resolves.toBe(14);

        expect(["before", "after", "resolved"]).toVerifySteps();
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

        expect([]).toVerifySteps();

        const ms = await runAllTimers();

        expect(ms).toBeWithin(1e6 - 1, 1e6 + 1); // more or less
        expect(["animation", "timeout"]).toVerifySteps();
    });
});
