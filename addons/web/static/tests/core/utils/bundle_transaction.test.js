// @ts-check

import { afterEach, describe, expect, test } from "@odoo/hoot";
import {
    deferUntilBundlesSettled,
    isBundleEvaluating,
    resetBundleTransactions,
    runInBundleTransaction,
} from "@web/core/utils/bundle_transaction";

describe.current.tags("headless");

afterEach(() => resetBundleTransactions());

test("nothing in flight: the caller runs its own reaction", () => {
    expect(isBundleEvaluating()).toBe(false);
    expect(deferUntilBundlesSettled(() => {})).toBe(false);
});

test("a reaction raised during evaluation is held until it finishes", async () => {
    /** @type {any[]} */
    const calls = [];
    const evaluation = runInBundleTransaction(async () => {
        expect(deferUntilBundlesSettled(() => calls.push("reaction"))).toBe(true);
        expect(calls).toEqual([], {
            message: "must not run while the bundle is half applied",
        });
        await Promise.resolve();
        calls.push("second module evaluated");
    });
    await evaluation;
    expect(calls).toEqual(["second module evaluated", "reaction"]);
});

test("many reactions from one bundle collapse into a single run", async () => {
    let runs = 0;
    const react = () => runs++;
    await runInBundleTransaction(async () => {
        for (let i = 0; i < 5; i++) {
            deferUntilBundlesSettled(react);
        }
    });
    expect(runs).toBe(1);
});

test("a bundle ending while another evaluates resolves applied, once that one ends", async () => {
    /** @type {any[]} */
    const calls = [];
    const { promise: secondModule, resolve: evaluateSecondModule } =
        Promise.withResolvers();
    const first = runInBundleTransaction(async () => {
        deferUntilBundlesSettled(() => calls.push("first reaction"));
    }).then(() => calls.push("first resolved"));
    const second = runInBundleTransaction(async () => {
        deferUntilBundlesSettled(() => calls.push("second reaction"));
        await secondModule;
        calls.push("second module evaluated");
    });
    await Promise.resolve();
    await Promise.resolve();
    expect(calls).toEqual([], {
        message: "the first must not resolve on a half-applied registry",
    });
    evaluateSecondModule();
    await Promise.all([first, second]);
    expect(calls).toEqual([
        "second module evaluated",
        "first reaction",
        "second reaction",
        "first resolved",
    ]);
});

test("a bundle with nothing to react to does not wait for the others", async () => {
    const { promise: stall, resolve: unstall } = Promise.withResolvers();
    const slow = runInBundleTransaction(() => stall);
    expect(await runInBundleTransaction(async () => "quick")).toBe("quick");
    unstall();
    await slow;
});

test("a bundle that throws still settles its reactions", async () => {
    /** @type {any[]} */
    const calls = [];
    await expect(
        runInBundleTransaction(async () => {
            deferUntilBundlesSettled(() => calls.push("reaction"));
            throw new Error("module evaluation failed");
        }),
    ).rejects.toThrow("module evaluation failed");
    expect(calls).toEqual(["reaction"], {
        message: "a failed bundle must not strand held reactions forever",
    });
    expect(isBundleEvaluating()).toBe(false);
});

test("a reaction that throws does not stop the others", async () => {
    /** @type {any[]} */
    const calls = [];
    await runInBundleTransaction(async () => {
        deferUntilBundlesSettled(() => {
            throw new Error("first reaction failed");
        });
        deferUntilBundlesSettled(() => calls.push("second"));
    });
    expect(calls).toEqual(["second"]);
});

test("the value of the evaluation is passed through", async () => {
    expect(await runInBundleTransaction(async () => 42)).toBe(42);
});

test("an async reaction is awaited, so the bundle resolves applied", async () => {
    /** @type {any[]} */
    const calls = [];
    await runInBundleTransaction(async () => {
        deferUntilBundlesSettled(async () => {
            await Promise.resolve();
            calls.push("slow reaction finished");
        });
    });
    expect(calls).toEqual(["slow reaction finished"], {
        message: "loadBundle must not resolve before the reaction has run",
    });
});
