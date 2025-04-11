import { expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { animationFrame } from "@odoo/hoot-dom";
import { PersistentCache } from "@web/core/utils/persistent_cache";

function promiseState(promise) {
    const pendingState = { status: "pending" };

    return Promise.race([promise, pendingState]).then(
        (value) => (value === pendingState ? value : { status: "fulfilled", value }),
        (reason) => ({ status: "rejected", reason })
    );
}
// TODO: add tests about invalidate

test("RamCache: can cache a simple call", async () => {
    // The fist call to persistentCache.read will save the result on the RamCache.
    // Each next call will retrive the ram cache independently, without executing the fallback
    const persistentCache = new PersistentCache("mockRpc", 1);
    const persistentCacheRead = (number) =>
        persistentCache.read("table", "key", () => {
            expect.step("fallback");
            return Promise.resolve({ test: number });
        });
    expect(await persistentCacheRead(123)).toEqual({ test: 123 });
    expect(await persistentCacheRead(456)).toEqual({ test: 123 });
    expect(await persistentCacheRead(789)).toEqual({ test: 123 });
    expect.verifySteps(["fallback"]);
});

test("RamCache: ram is set with promises", async () => {
    const def = new Deferred();
    const persistentCache = new PersistentCache("mockRpc", 1);

    // If two identical calls are made in succession, only one fallback will be made.
    // The second call will get the result of the first call (or a promise if the first call is not yet finish).
    const promFirst = persistentCache.read("table", "key", () => def);
    const promsSecond = persistentCache.read("table", "key", () => def);

    // Only one record in cache
    expect(Object.keys(persistentCache.ramCache.ram.table).length).toBe(1);
    let promInRamCache = persistentCache.ramCache.ram.table.key;

    // Note that proms, promisea and promiseb are the same promise.
    expect(await promiseState(promInRamCache)).toEqual({ status: "pending" });
    expect(await promiseState(promFirst)).toEqual({ status: "pending" });
    expect(await promiseState(promsSecond)).toEqual({ status: "pending" });

    def.resolve({ test: 123 });
    await animationFrame();

    // The cache is updated when the fetch is back
    promInRamCache = persistentCache.ramCache.ram.table.key;
    expect(await promInRamCache).toEqual({ test: 123 });
    expect(await promFirst).toEqual({ test: 123 });
    expect(await promsSecond).toEqual({ test: 123 });
});

test("PersistentCache: can cache a simple call", async () => {
    const persistentCache = new PersistentCache("mockRpc", 1);

    expect(
        await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }))
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    expect(persistentCache.indexedDB.mockIndexedDB.table.key).toEqual({ test: 123 });
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // Simulate a reload (Clear the Ram Cache)
    persistentCache.ramCache.invalidate();
    expect(persistentCache.ramCache.ram).toEqual({});
    const def = new Deferred();

    // we return the disk cache value.
    expect(
        await persistentCache.read("table", "key", () => {
            expect.step("Fallback");
            return def;
        })
    ).toEqual({ test: 123 });

    // the fallback returned a different value
    def.resolve({ test: 456 });
    await animationFrame();
    expect.verifySteps(["Fallback"]);
    // Both caches are updated with the last value
    expect(persistentCache.indexedDB.mockIndexedDB.table.key).toEqual({ test: 456 });
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });
});
