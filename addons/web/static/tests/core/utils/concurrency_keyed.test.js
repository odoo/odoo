// @ts-check

import { after, before, describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import {
    disableLogging,
    enableLogging,
    getStatus,
    makeLogger,
} from "@web/core/debug/debug_logger";
import { Deferred, KeepLastByKey, SupersededError } from "@web/core/utils/concurrency";

describe.current.tags("headless");
const log = makeLogger("web.concurrency.keyed");
before(() => {
    const previous = getStatus().spec;
    enableLogging("web.concurrency.keyed", { persist: false });
    after(() => {
        if (previous) {
            enableLogging(previous, { persist: false });
        } else {
            disableLogging({ persist: false });
        }
    });
});

/** @param {KeepLastByKey<any>} guard */
function retainedKeys(guard) {
    const keys = [...guard._byKey.keys()];
    log.logic("retained keys", () => ({ keys }));
    return keys;
}

test("settled requests release their keys on success and failure", async () => {
    const guard = new KeepLastByKey();
    for (let i = 0; i < 100; i++) {
        expect(await guard.add(String(i), Promise.resolve(i))).toBe(i);
    }
    const error = new Error("request failed");
    expect(
        await guard.add("failed", Promise.reject(error)).catch((reason) => reason),
    ).toBe(error);
    expect(retainedKeys(guard)).toEqual([]);
});

test("superseded settlement cannot release a newer request's key", async () => {
    const guard = new KeepLastByKey({ rejectSuperseded: true });
    const first = new Deferred();
    const second = new Deferred();
    const third = new Deferred();
    const firstResult = guard.add("group", first).catch((error) => error);
    const secondResult = guard.add("group", second).catch((error) => error);
    expect(await firstResult).toBeInstanceOf(SupersededError);
    first.resolve(1);
    await tick();
    expect(retainedKeys(guard)).toEqual(["group"]);
    const thirdResult = guard.add("group", third);
    expect(await secondResult).toBeInstanceOf(SupersededError);
    third.resolve(3);
    expect(await thirdResult).toBe(3);
    second.resolve(2);
    await tick();
    expect(retainedKeys(guard)).toEqual([]);
});

test("keys remain independent and empty keys can be cancelled", async () => {
    const guard = new KeepLastByKey({ rejectSuperseded: true });
    const first = guard.add("", new Deferred()).catch((error) => error);
    const second = new Deferred();
    const result = guard.add("other", second);
    guard.cancel("");
    expect(await first).toBeInstanceOf(SupersededError);
    expect(retainedKeys(guard)).toEqual(["other"]);
    second.resolve(2);
    expect(await result).toBe(2);
    expect(retainedKeys(guard)).toEqual([]);
});

for (const operation of ["cancel", "forget"]) {
    test(`${operation} releases a hung task and allows immediate key reuse`, async () => {
        const guard = new KeepLastByKey({ rejectSuperseded: true });
        const first = guard.add("group", new Deferred()).catch((error) => error);
        guard[operation]("group");
        expect(retainedKeys(guard)).toEqual([]);
        const next = new Deferred();
        const result = guard.add("group", next);
        expect(await first).toBeInstanceOf(SupersededError);
        expect(retainedKeys(guard)).toEqual(["group"]);
        next.resolve(2);
        expect(await result).toBe(2);
        expect(retainedKeys(guard)).toEqual([]);
    });
}

test("cancel all releases hung tasks in the default pending mode", async () => {
    const guard = new KeepLastByKey();
    let aborts = 0;
    for (const key of ["one", "two"]) {
        guard.add(key, new Deferred(), { abort: () => aborts++ }).then(
            () => expect.step("unexpected fulfillment"),
            () => expect.step("unexpected rejection"),
        );
    }
    guard.cancel();
    log.logic("cancel all", () => ({ aborts }));
    expect(aborts).toBe(2);
    expect(retainedKeys(guard)).toEqual([]);
    await tick();
    expect.verifySteps([]);
    expect(await guard.add("one", Promise.resolve(1))).toBe(1);
});

test("default supersession stays pending while the latest task releases its key", async () => {
    const guard = new KeepLastByKey();
    const old = new Deferred();
    guard.add("group", old).then(
        () => expect.step("unexpected fulfillment"),
        () => expect.step("unexpected rejection"),
    );
    expect(await guard.add("group", Promise.resolve(2))).toBe(2);
    old.reject(new Error("stale failure"));
    await tick();
    expect.verifySteps([]);
    expect(retainedKeys(guard)).toEqual([]);
});

for (const key of [undefined, "group"]) {
    test(`cancellation (${key}) preserves work created by an abort handler`, async () => {
        const guard = new KeepLastByKey({ rejectSuperseded: true });
        const next = new Deferred();
        /** @type {Promise<any> | undefined} */
        let replacement;
        const original = guard
            .add("group", new Deferred(), {
                abort: () => {
                    replacement = guard.add("group", next);
                },
            })
            .catch((error) => error);
        guard.cancel(key);
        expect(await original).toBeInstanceOf(SupersededError);
        expect(retainedKeys(guard)).toEqual(["group"]);
        next.resolve(2);
        expect(await replacement).toBe(2);
        expect(retainedKeys(guard)).toEqual([]);
    });
}
