import { Deferred, describe, expect, microTick, test, tick } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { RPCCache } from "@web/core/network/rpc_cache";
import { IDBQuotaExceededError, IndexedDB } from "@web/core/utils/indexed_db";

const S_PENDING = Symbol("Promise");

/**
 * @param {Promise<any>} promise
 */
function promiseState(promise) {
    return Promise.race([promise, Promise.resolve(S_PENDING)]).then(
        (value) => (value === S_PENDING ? { status: "pending" } : { status: "fulfilled", value }),
        (reason) => ({ status: "rejected", reason })
    );
}

describe.current.tags("headless");

test("RamCache: can cache a simple call", async () => {
    // The fist call to rpcCache.read saves the result on the RamCache.
    // Each next call will retrive the ram cache independently, without executing the fallback
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    const rpcCacheRead = (number) =>
        rpcCache.read("table", "key", () => {
            expect.step("fallback");
            return Promise.resolve({ test: number });
        });
    expect(await rpcCacheRead(123)).toEqual({ test: 123 });
    expect(await rpcCacheRead(456)).toEqual({ test: 123 });
    expect(await rpcCacheRead(789)).toEqual({ test: 123 });
    expect.verifySteps(["fallback"]);
});

test("RamCache: ram is set with promises", async () => {
    const def = new Deferred();
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // If two identical calls are made in succession, only one fallback will be made.
    // The second call will get the result of the first call (or a promise if the first call is not yet finish).
    const promFirst = rpcCache.read("table", "key", () => def);
    const promsSecond = rpcCache.read("table", "key", () => def);

    // Only one record in cache
    expect(Object.keys(rpcCache.ramCache.ram.table).length).toBe(1);
    let promInRamCache = rpcCache.ramCache.ram.table.key;

    // Note that proms, promisea and promiseb are the same promise.
    expect(await promiseState(promInRamCache)).toEqual({ status: "pending" });
    expect(await promiseState(promFirst)).toEqual({ status: "pending" });
    expect(await promiseState(promsSecond)).toEqual({ status: "pending" });

    def.resolve({ test: 123 });
    await microTick();

    // The cache is updated when the fetch is back
    promInRamCache = rpcCache.ramCache.ram.table.key;
    expect(await promInRamCache).toEqual({ test: 123 });
    expect(await promFirst).toEqual({ test: 123 });
    expect(await promsSecond).toEqual({ test: 123 });
});

test("PersistentCache: can cache a simple call", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
            type: "disk",
        })
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // simulate a reload (clear ramCache)
    rpcCache.ramCache.invalidate();
    expect(rpcCache.ramCache.ram).toEqual({});
    const def = new Deferred();

    // we return the disk cache value.
    expect(
        await rpcCache.read(
            "table",
            "key",
            () => {
                expect.step("Fallback");
                return Promise.resolve(def);
            },
            { type: "disk" }
        )
    ).toEqual({ test: 123 });
    expect.verifySteps(["Fallback"]);

    // the fallback returned a different value
    def.resolve({ test: 456 });
    await microTick();
    await microTick();
    await microTick();
    // Both caches are updated with the last value
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":456}'
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });
});

test("invalidate table", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
            type: "disk",
        })
    ).toEqual({
        test: 123,
    });

    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    //invalidate the table
    rpcCache.invalidate("table");

    // `table` is empty
    expect(rpcCache.indexedDB.mockIndexedDB.table).toEqual({});
    expect(rpcCache.ramCache.ram.table).toEqual({});
});

test("invalidate multiple tables", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
            type: "disk",
        })
    ).toEqual({
        test: 123,
    });

    expect(
        await rpcCache.read("table2", "key", () => Promise.resolve({ test: 456 }), {
            type: "disk",
        })
    ).toEqual({
        test: 456,
    });

    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(rpcCache.indexedDB.mockIndexedDB.table2.key.ciphertext).toBe(
        'encrypted data:{"test":456}'
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
    expect(await promiseState(rpcCache.ramCache.ram.table2.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });

    //invalidate the table
    rpcCache.invalidate(["table", "table2"]);

    // `table` is empty
    expect(rpcCache.indexedDB.mockIndexedDB.table).toEqual({});
    expect(rpcCache.indexedDB.mockIndexedDB.table2).toEqual({});
    expect(rpcCache.ramCache.ram.table).toEqual({});
    expect(rpcCache.ramCache.ram.table2).toEqual({});
});

test("IndexedDB Crypt: can cache a simple call", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    await rpcCache.encryptReady;

    expect(
        await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
            type: "disk",
        })
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        'encrypted data:{"test":123}'
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // simulate a reload (clear ramCache)
    rpcCache.ramCache.invalidate();
    expect(rpcCache.ramCache.ram).toEqual({});
    const def = new Deferred();

    // we return the disk cache value - decrypted.
    expect(
        await rpcCache.read(
            "table",
            "key",
            () => {
                expect.step("Fallback");
                return Promise.resolve(def);
            },
            { type: "disk" }
        )
    ).toEqual({ test: 123 });
    expect.verifySteps(["Fallback"]);

    // the fallback returned a different value
    def.resolve({ test: 456 });
});

test("update callback - Ram Value", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }))).toEqual({
        test: 123,
    });
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    const def = new Deferred();

    // we return the RAM cache value.
    expect(
        await rpcCache.read(
            "table",
            "key",
            () => {
                expect.step("Fallback");
                return Promise.resolve(def);
            },
            {
                update: "always",
                callback: (result) => {
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
    expect.verifySteps(["Callback"]);
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });
});

test("update callback - Disk Value", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    expect(
        await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
            type: "disk",
        })
    ).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // simulate a reload (clear ramCache)
    rpcCache.ramCache.invalidate();
    expect(rpcCache.ramCache.ram).toEqual({});
    const def = new Deferred();

    // we return the Disk cache value.
    expect(
        await rpcCache.read(
            "table",
            "key",
            () => {
                expect.step("Fallback");
                return Promise.resolve(def);
            },
            {
                type: "disk",
                callback: (result) => {
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
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":456}`
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 456 },
    });
});

test("Ram value shouldn't change (update the rpc response)", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // fill the cache
    const res = await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    expect(res).toEqual({ test: 123 });
    res.plop = true;

    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
});

test("Ram value shouldn't change (update the Ram response)", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // fill the cache
    let res = await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    const def = new Deferred();
    res = await rpcCache.read("table", "key", () => def);

    // res came from the RAM
    expect(res).toEqual({ test: 123 });
    res.plop = true;

    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
});

test("Ram value shouldn't change (update the IndexedDB response)", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // fill the cache
    let res = await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
        type: "disk",
    });
    expect(res).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // simulate a reload (clear ramCache)
    rpcCache.ramCache.invalidate();
    expect(rpcCache.ramCache.ram).toEqual({});

    const def = new Deferred();
    res = await rpcCache.read("table", "key", () => def, { type: "disk" });

    // res came from IndexedDB
    expect(res).toEqual({ test: 123 });
    res.plop = true;

    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });
});

test("Changing the result shouldn't force the call to callback with hasChanged (RAM value)", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    let res;
    // fill the cache
    res = await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }));
    expect(res).toEqual({
        test: 123,
    });
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // read the RAM Value !
    const def = new Deferred();
    res = await rpcCache.read("table", "key", () => def, {
        callback: (_result, hasChanged) => {
            if (hasChanged) {
                expect.step("callback with hasChanged shouldn't be called");
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

test("Changing the result shouldn't force the call to callback with hasChanged (IndexedDB value)", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    let res;
    // fill the cache
    res = await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
        type: "disk",
    });
    expect(res).toEqual({
        test: 123,
    });
    // Both caches are correctly updated with the fetch values
    await microTick();
    await microTick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // simulate a reload (clear ramCache)
    rpcCache.ramCache.invalidate();
    expect(rpcCache.ramCache.ram).toEqual({});

    // read the IndexedDB Value !
    const def = new Deferred();
    res = await rpcCache.read("table", "key", () => def, {
        type: "disk",
        update: "always",
        callback: (_res, hasChanged) => {
            if (hasChanged) {
                expect.step("callback with hasChanged shouldn't be called");
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

test("RamCache (no update): consecutive calls (success)", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    const def = new Deferred();
    rpcCache
        .read("table", "key", () => def)
        .then((r) => {
            expect.step(`first prom resolved with ${r}`);
        });
    rpcCache
        .read("table", "key", () => expect.step("should not be called"))
        .then((r) => {
            expect.step(`second prom resolved with ${r}`);
        });

    def.resolve("some value");
    await tick();
    expect.verifySteps([
        "first prom resolved with some value",
        "second prom resolved with some value",
    ]);
});

test("RamCache (no update): consecutive calls and rejected promise", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    const def = new Deferred();
    rpcCache
        .read("table", "key", () => def)
        .catch((e) => {
            expect.step(`first prom rejected ${e.message}`);
        });
    rpcCache
        .read("table", "key", () => expect.step("should not be called"))
        .catch((e) => {
            expect.step(`second prom rejected ${e.message}`);
        });

    def.reject(new Error("boom"));
    await tick();
    expect.verifySteps(["first prom rejected boom", "second prom rejected boom"]);
});

test("RamCache: pending request and call to invalidate", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    const def = new Deferred();
    rpcCache
        .read("table", "key", () => {
            expect.step("fallback first call");
            return def;
        })
        .then((r) => {
            expect.step(`first prom resolved with ${r}`);
        });
    rpcCache.invalidate();
    rpcCache
        .read("table", "key", () => {
            expect.step("fallback second call");
            return Promise.resolve("another value");
        })
        .then((r) => {
            expect.step(`second prom resolved with ${r}`);
        });

    def.resolve("some value");
    await tick();
    expect.verifySteps([
        "fallback first call",
        "fallback second call",
        "second prom resolved with another value",
        "first prom resolved with some value",
    ]);

    // call again to ensure that the correct value is stored in the cache
    rpcCache
        .read("table", "key", () => expect.step("should not be called"))
        .then((r) => {
            expect.step(`third prom resolved with ${r}`);
        });
    await tick();
    expect.verifySteps(["third prom resolved with another value"]);
});

test("RamCache: pending request and call to invalidate, update callbacks", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    // populate the cache
    rpcCache.read("table", "key", () => {
        expect.step("first call: fallback");
        return Promise.resolve("initial value");
    });
    await tick();
    expect.verifySteps(["first call: fallback"]);

    // read cache again, with update callback
    const def = new Deferred();
    rpcCache
        .read(
            "table",
            "key",
            () => {
                expect.step("second call: fallback");
                return def;
            },
            {
                callback: (newValue) => expect.step(`second call: callback ${newValue}`),
                update: "always",
            }
        )
        .then((r) => expect.step(`second call: resolved with ${r}`));
    // read it twice, s.t. there's a pending request
    rpcCache
        .read(
            "table",
            "key",
            () => {
                expect.step("should not be called as there's a pending request");
            },
            {
                callback: (newValue) => expect.step(`third call: callback ${newValue}`),
                update: "always",
            }
        )
        .then((r) => {
            expect.step(`third call: resolved with ${r}`);
        });
    await tick();

    expect.verifySteps([
        "second call: fallback",
        "second call: resolved with initial value",
        "third call: resolved with initial value",
    ]);

    rpcCache.invalidate();
    // sanity check to ensure that cache has been invalidated
    rpcCache.read("table", "key", () => {
        expect.step("fourth call: fallback");
        return Promise.resolve("value after invalidation");
    });
    expect.verifySteps(["fourth call: fallback"]);

    // resolve def => update callbacks of requests 2 and 3 must be called
    def.resolve("updated value");
    await tick();
    expect.verifySteps([
        "second call: callback updated value",
        "third call: callback updated value",
    ]);
});

test("RamCache: pending request and call to invalidate, update callbacks in error", async () => {
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    const defs = [new Deferred(), new Deferred()];
    rpcCache
        .read("table", "key", () => {
            expect.step("first call: fallback (error)");
            return defs[0]; // will be rejected
        })
        .catch((e) => expect.step(`first call: rejected with ${e}`));

    // invalidate cache and read again
    rpcCache.invalidate();
    rpcCache
        .read("table", "key", () => {
            expect.step("second call: fallback");
            return defs[1];
        })
        .then((r) => expect.step(`second call: resolved with ${r}`));
    await tick();

    expect.verifySteps(["first call: fallback (error)", "second call: fallback"]);

    // reject first def
    defs[0].reject("my_error");
    await tick();
    expect.verifySteps(["first call: rejected with my_error"]);

    // read again, should retrieve same prom as second call which is still pending
    rpcCache
        .read("table", "key", () => expect.step("should not be called"))
        .then((r) => expect.step(`third call: resolved with ${r}`));
    await tick();
    expect.verifySteps([]);

    // read again, should retrieve same prom as second call which is still pending (update "always")
    rpcCache
        .read("table", "key", () => expect.step("should not be called"), { update: "always" })
        .then((r) => expect.step(`fourth call: resolved with ${r}`));
    await tick();
    expect.verifySteps([]);

    // resolve second def
    defs[1].resolve("updated value");
    await tick();
    expect.verifySteps([
        "second call: resolved with updated value",
        "third call: resolved with updated value",
        "fourth call: resolved with updated value",
    ]);
});

test("DiskCache: multiple consecutive calls, empty cache", async () => {
    // The fist call to rpcCache.read saves the promise to the RAM cache.
    // Each next call (before the end of the first call) retrieves the same result as the first call
    // without executing the fallback.
    // The callback of each call is executed.

    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    const def = new Deferred();
    let id = 0;
    const rpcCacheRead = () => {
        rpcCache.read(
            "table",
            "key",
            () => {
                expect.step("fallback");
                return def;
            },
            {
                callback: () => {
                    expect.step(`callback ${++id}`);
                },
            }
        );
    };

    rpcCacheRead();
    rpcCacheRead();
    rpcCacheRead();

    expect.verifySteps(["fallback"]);
    def.resolve({ test: 123 });
    await tick();

    expect.verifySteps(["callback 1", "callback 2", "callback 3"]);
});

test("DiskCache: multiple consecutive calls, value already in disk cache", async () => {
    // The first call to rpcCache.read saves the promise to the RAM cache.
    // Each next call (before the end of the first call) retrieves the same result as the first call.
    // Each call receives as value the disk value, then each callback is executed.
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    const def = new Deferred();

    // fill the cache
    await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
        type: "disk",
    });
    await tick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // simulate a reload (clear ramCache)
    rpcCache.ramCache.invalidate();
    expect(rpcCache.ramCache.ram).toEqual({});

    const rpcCacheRead = (id) =>
        rpcCache.read(
            "table",
            "key",
            () => {
                expect.step(`fallback ${id}`);
                return def;
            },
            {
                type: "disk",
                callback: (result, hasChanged) => {
                    expect.step(
                        `callback ${id}: ${JSON.stringify(result)} ${hasChanged ? "(changed)" : ""}`
                    );
                },
            }
        );

    rpcCacheRead(1).then((result) => expect.step("res call 1: " + JSON.stringify(result)));
    await tick();
    rpcCacheRead(2).then((result) => expect.step("res call 2: " + JSON.stringify(result)));
    await tick();
    rpcCacheRead(3).then((result) => expect.step("res call 3: " + JSON.stringify(result)));
    await tick();

    expect.verifySteps([
        "fallback 1",
        'res call 1: {"test":123}',
        'res call 2: {"test":123}',
        'res call 3: {"test":123}',
    ]);

    def.resolve({ test: 456 });
    await tick();
    expect.verifySteps([
        'callback 1: {"test":456} (changed)',
        'callback 2: {"test":456} (changed)',
        'callback 3: {"test":456} (changed)',
    ]);
});

test("DiskCache: multiple consecutive calls, fallback fails", async () => {
    // The first call to rpcCache.read saves the promise to the RAM cache.
    // Each next call (before the end of the first call) retrieves the same result as the first call.
    // The fallback fails.
    // Each call receives as value the disk value, callbacks aren't executed.
    expect.errors(1);
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    const def = new Deferred();

    // fill the cache
    await rpcCache.read("table", "key", () => Promise.resolve({ test: 123 }), {
        type: "disk",
    });
    await tick();
    expect(rpcCache.indexedDB.mockIndexedDB.table.key.ciphertext).toBe(
        `encrypted data:{"test":123}`
    );
    expect(await promiseState(rpcCache.ramCache.ram.table.key)).toEqual({
        status: "fulfilled",
        value: { test: 123 },
    });

    // simulate a reload (clear ramCache)
    rpcCache.ramCache.invalidate();
    expect(rpcCache.ramCache.ram).toEqual({});

    const rpcCacheRead = (id) =>
        rpcCache.read(
            "table",
            "key",
            () => {
                expect.step(`fallback ${id}`);
                return def;
            },
            {
                type: "disk",
                callback: () => {
                    expect.step("callback (should not be executed)");
                },
            }
        );

    rpcCacheRead(1).then((result) => expect.step("res call 1: " + JSON.stringify(result)));
    await tick();
    rpcCacheRead(2).then((result) => expect.step("res call 2: " + JSON.stringify(result)));
    await tick();
    rpcCacheRead(3).then((result) => expect.step("res call 3: " + JSON.stringify(result)));
    await tick();

    expect.verifySteps([
        "fallback 1",
        'res call 1: {"test":123}',
        'res call 2: {"test":123}',
        'res call 3: {"test":123}',
    ]);

    def.reject(new Error("my RPCError"));
    await tick();
    await tick();

    expect.verifySteps([]);
    expect.verifyErrors(["my RPCError"]);
});

test("DiskCache: multiple consecutive calls, empty cache, fallback fails", async () => {
    // The first call to rpcCache.read saves the promise to the RAM cache. That promise will be
    // rejected.
    // Each next call (before the end of the first call) retrieves the same result as the first call.
    // The fallback fails.
    // Each call receives the error.
    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );
    const def = new Deferred();

    const rpcCacheRead = (id) =>
        rpcCache.read(
            "table",
            "key",
            () => {
                expect.step(`fallback ${id}`);
                return def;
            },
            {
                type: "disk",
                callback: () => {
                    expect.step("callback (should not be executed)");
                },
            }
        );

    rpcCacheRead(1).catch((error) => expect.step(`error call 1: ${error.message}`));
    await tick();
    rpcCacheRead(2).catch((error) => expect.step(`error call 2: ${error.message}`));
    await tick();
    rpcCacheRead(3).catch((error) => expect.step(`error call 3: ${error.message}`));
    await tick();

    expect.verifySteps(["fallback 1"]);

    def.reject(new Error("my RPCError"));
    await tick();

    expect.verifySteps([
        "error call 1: my RPCError",
        "error call 2: my RPCError",
        "error call 3: my RPCError",
    ]);
});

test("DiskCache: write throws an IDBQuotaExceededError", async () => {
    patchWithCleanup(IndexedDB.prototype, {
        deleteDatabase() {
            expect.step("delete db");
        },
        write() {
            expect.step("write");
            return Promise.reject(new IDBQuotaExceededError());
        },
    });

    const rpcCache = new RPCCache(
        "mockRpc",
        1,
        "85472d41873cdb504b7c7dfecdb8993d90db142c4c03e6d94c4ae37a7771dc5b"
    );

    const fallback = () => {
        expect.step(`fallback`);
        return Promise.resolve("value");
    };
    await rpcCache.read("table", "key", fallback, { type: "disk" });

    await expect.waitForSteps(["fallback", "write", "delete db"]);
});
