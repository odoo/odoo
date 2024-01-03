/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import { Deferred, advanceTime, runAllTimers, tick } from "@odoo/hoot-mock";
import { parseUrl } from "../local_helpers";

describe(parseUrl(import.meta.url), () => {
    test("advanceTime", async () => {
        const timeoutId = window.setTimeout(() => expect.step("timeout"), 100);
        const intervalId = window.setInterval(() => expect.step("interval"), 150);
        const animationHandle = window.requestAnimationFrame((delta) =>
            expect.step(`animation:${Math.floor(delta)}`)
        );

        expect(timeoutId).toBeGreaterThan(0);
        expect(intervalId).toBeGreaterThan(0);
        expect(animationHandle).toBeGreaterThan(0);
        expect([]).toVerifySteps();

        await advanceTime(1000); // just to be sure

        expect(["animation:16", "timeout", "interval"]).toVerifySteps();

        await advanceTime(1000);

        expect(["interval"]).toVerifySteps();

        window.clearInterval(intervalId);

        await advanceTime(1000);

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
        window.setTimeout(() => expect.step("timeout"), 1e6);
        window.requestAnimationFrame((delta) => expect.step(`animation:${Math.floor(delta)}`));

        expect([]).toVerifySteps();

        const ms = await runAllTimers();

        expect(ms).toBeWithin(1e6 - 1, 1e6 + 1); // more or less
        expect(["animation:16", "timeout"]).toVerifySteps();
    });
});
