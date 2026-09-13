// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { SupersededError } from "@web/core/utils/concurrency";
import {
    NavigationToken,
    NavigationTracker,
} from "@web/webclient/actions/navigation_token";

describe.current.tags("headless");

test("a minted token is current until the next mint", () => {
    const tracker = new NavigationTracker();
    const first = tracker.mint();
    expect(first.isCurrent()).toBe(true);
    const second = tracker.mint();
    expect(first.isCurrent()).toBe(false);
    expect(second.isCurrent()).toBe(true);
});

test("snapshot reads the clock without advancing it", () => {
    const tracker = new NavigationTracker();
    const minted = tracker.mint();
    const observer = tracker.snapshot();
    expect(observer).toBeInstanceOf(NavigationToken);
    expect(observer.epoch).toBe(minted.epoch);
    expect(minted.isCurrent()).toBe(true, {
        message: "observing must not cancel the navigation under way",
    });
});

test("throwIfSuperseded is silent while current, SupersededError once not", () => {
    const tracker = new NavigationTracker();
    const token = tracker.mint();
    expect(() => token.throwIfSuperseded()).not.toThrow();
    tracker.mint();
    expect(() => token.throwIfSuperseded()).toThrow(SupersededError);
});

test("settle resolves with the promise's value while current", async () => {
    const tracker = new NavigationTracker();
    const value = await tracker.mint().settle(Promise.resolve("value"));
    expect(value).toBe("value");
});

test("settle rejects with the promise's own error while current", async () => {
    const tracker = new NavigationTracker();
    await expect(
        tracker.mint().settle(Promise.reject(new Error("own failure"))),
    ).rejects.toThrow(/own failure/);
});

test("a newer mint rejects a pending settle eagerly, before its promise settles", async () => {
    const tracker = new NavigationTracker();
    const never = new Deferred();
    const guarded = tracker.mint().settle(never);
    tracker.mint();
    await expect(guarded).rejects.toThrow(SupersededError);
});

test("a stale settlement is dropped: the superseded rejection is the only outcome", async () => {
    const tracker = new NavigationTracker();
    const slow = new Deferred();
    /** @type {string[]} */
    const outcomes = [];
    const guarded = tracker
        .mint()
        .settle(slow)
        .then(
            (value) => outcomes.push(`resolved:${value}`),
            (error) => outcomes.push(error.constructor.name),
        );
    tracker.mint();
    slow.resolve("late");
    await guarded;
    await Promise.resolve();
    expect(outcomes).toEqual(["SupersededError"]);
});

test("settling on an already-stale token rejects immediately", async () => {
    const tracker = new NavigationTracker();
    const stale = tracker.mint();
    tracker.mint();
    await expect(stale.settle(new Deferred())).rejects.toThrow(SupersededError);
});

test("guard is mint + settle: it supersedes the navigation before it", async () => {
    const tracker = new NavigationTracker();
    const first = tracker.mint();
    const pending = first.settle(new Deferred());
    const value = await tracker.guard(Promise.resolve("winner"));
    expect(value).toBe("winner");
    expect(first.isCurrent()).toBe(false);
    await expect(pending).rejects.toThrow(SupersededError);
});

test("a resolved settle clears the pending slot: the next mint rejects nobody", async () => {
    const tracker = new NavigationTracker();
    const done = await tracker.guard(Promise.resolve("done"));
    expect(done).toBe("done");
    const next = tracker.mint();
    expect(next.isCurrent()).toBe(true);
});

test("two settles in one epoch: the next mint supersedes BOTH, neither leaks", async () => {
    const tracker = new NavigationTracker();
    const first = tracker.snapshot().settle(new Deferred());
    const second = tracker.snapshot().settle(new Deferred());

    let firstState = "pending";
    let secondState = "pending";
    first.catch((error) => (firstState = error.name));
    second.catch((error) => (secondState = error.name));

    tracker.mint();
    for (let i = 0; i < 5; i++) {
        await Promise.resolve();
    }

    expect(firstState).toBe("SupersededError");
    expect(secondState).toBe("SupersededError");
});

test("already-stale settlement consumes a source rejection", async () => {
    const tracker = new NavigationTracker();
    const stale = tracker.mint();
    tracker.mint();
    await expect(stale.settle(Promise.reject(new Error("source")))).rejects.toThrow(
        SupersededError,
    );
    // HOOT's unhandled rejection collector must remain empty after settlement.
    await new Promise((resolve) => setTimeout(resolve, 0));
});
