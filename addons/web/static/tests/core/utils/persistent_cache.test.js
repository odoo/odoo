import { describe, expect, test } from "@odoo/hoot";
import { Deferred, microTick } from "@odoo/hoot-mock";
import { PersistentCache } from "@web/core/utils/persistent_cache";

const symbol = Symbol("Promise");

function promiseState(promise) {
    return Promise.race([promise, Promise.resolve(symbol)]).then(
        (value) => (value === symbol ? { status: "pending" } : { status: "fulfilled", value }),
        (reason) => ({ status: "rejected", reason })
    );
}

describe.current.tags("headless");

test("RamCache: can cache a simple call", async () => {
    // The fist call to persistentCache.read will save the result on the RamCache.
    // Each next call will retrive the ram cache independently, without executing the fallback
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
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
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

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
    await microTick();

    // The cache is updated when the fetch is back
    promInRamCache = persistentCache.ramCache.ram.table.key;
    expect(await promInRamCache).toEqual({ test: 123 });
    expect(await promFirst).toEqual({ test: 123 });
    expect(await promsSecond).toEqual({ test: 123 });
});

test("PersistentCache: can cache a simple call", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }))
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
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
            return Promise.resolve(def);
        })
    ).toEqual({ test: 123 });
    expect.verifySteps(["Fallback"]);

    // the fallback returned a different value
    def.resolve({ test: 456 });
    await microTick();
    await microTick();
    await microTick();
    // Both caches are updated with the last value
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":456}'
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });
});

test("invalidate table", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }))
    ).toEqual({
        test: 123,
    });

    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    //invalidate the table
    persistentCache.invalidate("table");

    // `table` is empty
    expect(persistentCache.indexedDB.mockIndexedDB.table).toEqual({});
    expect(persistentCache.ramCache.ram.table).toEqual({});
});

test("invalidate multiple tables", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }))
    ).toEqual({
        test: 123,
    });

    expect(
        await persistentCache.read("table2", "key", () => Promise.resolve({ test: 456 }))
    ).toEqual({
        test: 456,
    });

    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(persistentCache.indexedDB.mockIndexedDB.table2.key.ciphertext).toBe(
        'encrypted data:{"test":456}'
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
    expect(await promiseState(persistentCache.ramCache.ram.table2.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });

    //invalidate the table
    persistentCache.invalidate(["table", "table2"]);

    // `table` is empty
    expect(persistentCache.indexedDB.mockIndexedDB.table).toEqual({});
    expect(persistentCache.indexedDB.mockIndexedDB.table2).toEqual({});
    expect(persistentCache.ramCache.ram.table).toEqual({});
    expect(persistentCache.ramCache.ram.table2).toEqual({});
});

test("IndexedDB Crypt: can cache a simple call", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    await persistentCache.encryptReady;

    expect(
        await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }))
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // Simulate a reload (Clear the Ram Cache)
    persistentCache.ramCache.invalidate();
    expect(persistentCache.ramCache.ram).toEqual({});
    const def = new Deferred();

    // we return the disk cache value - decrypted.
    expect(
        await persistentCache.read("table", "key", () => {
            expect.step("Fallback");
            return Promise.resolve(def);
        })
    ).toEqual({ test: 123 });
    expect.verifySteps(["Fallback"]);

    // the fallback returned a different value
    def.resolve({ test: 456 });
});

test("update callback - Ram Value", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }))
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    const def = new Deferred();

    // we return the RAM cache value.
    expect(
        await persistentCache.read(
            "table",
            "key",
            () => {
                expect.step("Fallback");
                return Promise.resolve(def);
            },
            {
                onFinish: (hasChanged, result) => {
                    expect.step("Callback");
                    expect(result).toEqual({ test: 456 });
                },
            }
        )
    ).toEqual({ test: 123 });
    expect.verifySteps(["Fallback"]);

    // the fallback returned a different value
    def.resolve({ test: 456 });
    await microTick();
    await microTick();
    await microTick();
    expect.verifySteps(["Callback"]);
    // Both caches are updated with the last value
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":456}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });
});

test("update callback - Disk Value", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }))
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // Simulate a reload (Clear the Ram Cache)
    persistentCache.ramCache.invalidate();
    expect(persistentCache.ramCache.ram).toEqual({});
    const def = new Deferred();

    // we return the Disk cache value.
    expect(
        await persistentCache.read(
            "table",
            "key",
            () => {
                expect.step("Fallback");
                return Promise.resolve(def);
            },
            {
                onFinish: (hasChanged, result) => {
                    expect.step("Callback");
                    expect(result).toEqual({ test: 456 });
                },
            }
        )
    ).toEqual({ test: 123 });
    expect.verifySteps(["Fallback"]);

    // the fallback returned a different value
    def.resolve({ test: 456 });
    await microTick();
    await microTick();
    await microTick();
    expect.verifySteps(["Callback"]);
    // Both caches are updated with the last value
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":456}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });
});

test("Ram value shouldn't change (update the rpc response)", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // fill the cache
    const res = await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    expect(res).toEqual({ test: 123 });
    res.plop = true;

    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
});

test("Ram value shouldn't change (update the Ram response)", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // fill the cache
    let res = await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    const def = new Deferred();
    res = await persistentCache.read("table", "key", () => def);

    // res came from the RAM
    expect(res).toEqual({ test: 123 });
    res.plop = true;

    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
});

test("Ram value shouldn't change (update the IndexedDB response)", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // fill the cache
    let res = await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // Simulate a reload (Clear the Ram Cache)
    persistentCache.ramCache.invalidate();
    expect(persistentCache.ramCache.ram).toEqual({});

    const def = new Deferred();
    res = await persistentCache.read("table", "key", () => def);

    // res came from IndexedDB
    expect(res).toEqual({ test: 123 });
    res.plop = true;

    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
});

test("Changing the result shouldn't force the call to onFinish with hasChanged (RAM value)", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    let res;
    // fill the cache
    res = await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // read the RAM Value !
    const def = new Deferred();
    res = await persistentCache.read("table", "key", () => def, {
        onFinish: (hasChanged) => {
            if (hasChanged) {
                expect.step("onFinish with hasChanged shouldn't be called");
            }
        },
    });
    expect(res).toEqual({
        test: 123,
    });

    //modify the result
    res.plop = true;
    expect(res).toEqual({
        test: 123,
        plop: true,
    });

    // resolve with the same value as the cache !
    def.resolve({ test: 123 });
});

test("Changing the result shouldn't force the call to onFinish with hasChanged (IndexedDB value)", async () => {
    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    let res;
    // fill the cache
    res = await persistentCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(persistentCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(persistentCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // Simulate a reload (Clear the Ram Cache)
    persistentCache.ramCache.invalidate();
    expect(persistentCache.ramCache.ram).toEqual({});

    // read the IndexedDB Value !
    const def = new Deferred();
    res = await persistentCache.read("table", "key", () => def, {
        onFinish: (hasChanged) => {
            if (hasChanged) {
                expect.step("onFinish with hasChanged shouldn't be called");
            }
        },
    });
    expect(res).toEqual({
        test: 123,
    });

    //modify the result
    res.plop = true;
    expect(res).toEqual({
        test: 123,
        plop: true,
    });

    // resolve with the same value as the cache !
    def.resolve({ test: 123 });
});

test("DiskCache: multiple consecutive calls, call once fallback", async () => {
    // The fist call to persistentCache.read will save the promise to the Ram Cache.
    // Each next call (before the end of the first call) will retrive the promise of the first call
    // without executing the fallback
    // the onFinish callback of each call is executed.

    const persistentCache = new PersistentCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    const def = new Deferred();
    let id = 0;
    const persistentCacheRead = () => {
        persistentCache.read(
            "table",
            "key",
            () => {
                expect.step("fallback");
                return def;
            },
            {
                onFinish: () => {
                    expect.step("onFinish" + id++);
                },
            }
        );
    };

    persistentCacheRead();
    persistentCacheRead();
    persistentCacheRead();
    persistentCacheRead();

    def.resolve({ test: 123 });
    await microTick();

    expect.verifySteps(["fallback", "onFinish0", "onFinish1", "onFinish2", "onFinish3"]);
});
