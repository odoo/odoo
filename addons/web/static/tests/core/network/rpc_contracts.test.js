// @ts-check

import { after, before, Deferred, describe, expect, test, tick } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { mockIndexedDBForTests } from "@web/../tests/_framework/mock_indexed_db.hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    disableLogging,
    enableLogging,
    getStatus,
    makeLogger,
} from "@web/core/debug/debug_logger";
import {
    ConnectionAbortedError,
    InvalidResponseError,
    rpc,
    rpcBus,
    RPCError,
} from "@web/core/network/rpc";
import { RPCCache } from "@web/core/network/rpc_cache";
import { globalSingleton } from "@web/core/utils/global_singleton";

describe.current.tags("headless");
mockIndexedDBForTests();
const log = makeLogger("web.rpc.contracts");

before(() => {
    const state = /** @type {any} */ (globalSingleton("rpc", () => ({})));
    const previousCache = state.rpcCache;
    const previousLog = getStatus().spec;
    enableLogging("web.rpc", { persist: false });
    after(() => {
        if (state.rpcCache !== previousCache) {
            state.rpcCache?.invalidate();
        }
        rpc.setCache(previousCache);
        if (previousLog) {
            enableLogging(previousLog, { persist: false });
        } else {
            disableLogging({ persist: false });
        }
    });
});

const malformedEnvelopes = [
    null,
    true,
    0,
    "not an envelope",
    [],
    {},
    { error: null },
    { error: {} },
    { error: { code: "200", message: "bad code" } },
    { error: { code: 200, message: null } },
    { result: 1, error: { code: 200, message: "ambiguous" } },
];
for (const body of malformedEnvelopes) {
    test(`invalid envelope ${JSON.stringify(body)} is reported once and never retried`, async () => {
        let calls = 0;
        /** @type {any[]} */
        const responses = [];
        const onResponse = (event) => responses.push(event.detail);
        rpcBus.addEventListener("RPC:RESPONSE", onResponse);
        after(() => rpcBus.removeEventListener("RPC:RESPONSE", onResponse));
        mockFetch(() => {
            calls++;
            return new Response(JSON.stringify(body), {
                headers: { "Content-Type": "application/json" },
            });
        });
        await expect(rpc("/invalid-envelope", {}, { retry: 1 })).rejects.toThrow(
            InvalidResponseError,
        );
        expect(calls).toBe(1);
        expect(responses).toHaveLength(1);
        expect(responses[0].error.retryable).toBe(false);
        log.logic("invalid envelope", () => ({ body, calls }));
    });
}

test("valid falsy results and server errors retain their meaning", async () => {
    for (const result of [null, false, 0, "", [], {}]) {
        mockFetch(() => ({ result }));
        expect(await rpc("/valid-envelope")).toEqual(result);
    }
    mockFetch(() => ({ error: { code: 200, message: "Server rejected the call" } }));
    await expect(rpc("/server-error")).rejects.toThrow(RPCError);
});

test("cached RPC recovers from a synchronous invalid-timeout error", async () => {
    rpc.setCache(new RPCCache("sync-recovery", 1));
    let calls = 0;
    mockFetch(() => {
        calls++;
        return { result: "recovered" };
    });
    await expect(
        rpc("/setup-recovery", {}, { cache: true, timeout: -1 }),
    ).rejects.toThrow(TypeError);
    expect(await rpc("/setup-recovery", {}, { cache: true })).toBe("recovered");
    expect(calls).toBe(1);
});

test("a synchronous refresh failure preserves warm data and allows another refresh", async () => {
    const cache = new RPCCache("warm-sync-recovery", 1);
    await cache.read("table", "key", () => Promise.resolve("warm"));
    expect(
        await cache.read(
            "table",
            "key",
            () => {
                throw new ConnectionAbortedError();
            },
            { update: "always" },
        ),
    ).toBe("warm");
    const gate = new Deferred();
    const refreshed = new Deferred();
    expect(
        await cache.read("table", "key", () => gate, {
            update: "always",
            callback: (value, changed) => refreshed.resolve({ value, changed }),
        }),
    ).toBe("warm");
    gate.resolve("fresh");
    expect(await refreshed).toEqual({ value: "fresh", changed: true });
    expect(await cache.read("table", "key", () => Promise.resolve("unexpected"))).toBe(
        "fresh",
    );
});

test("header variants have independent warm cache entries and canonical header spelling", async () => {
    rpc.setCache(new RPCCache("header-variants", 1));
    let calls = 0;
    mockFetch((_, init) => {
        calls++;
        return { result: new Headers(init.headers).get("X-Variant") };
    });
    const read = (headers) => rpc("/variants", {}, { cache: true, headers });
    expect(await read({ "X-Variant": "A", "X-Other": "same" })).toBe("A");
    expect(await read({ "X-Variant": "B", "X-Other": "same" })).toBe("B");
    expect(await read(new Headers({ "x-other": "same", "x-variant": "A" }))).toBe("A");
    expect(
        await read([
            ["X-Variant", "B"],
            ["X-Other", "same"],
        ]),
    ).toBe("B");
    expect(calls).toBe(2);
});

test("dedup plus cache keeps simultaneous header variants independent", async () => {
    rpc.setCache(new RPCCache("cold-header-variants", 1));
    const gate = new Deferred();
    let calls = 0;
    mockFetch(async (_, init) => {
        calls++;
        await gate;
        return { result: new Headers(init.headers).get("X-Variant") };
    });
    const a = rpc(
        "/cold-variants",
        {},
        {
            cache: true,
            dedup: true,
            headers: { "X-Variant": "A" },
        },
    );
    const b = rpc(
        "/cold-variants",
        {},
        {
            cache: true,
            dedup: true,
            headers: { "X-Variant": "B" },
        },
    );
    gate.resolve();
    expect(await Promise.all([a, b])).toEqual(["A", "B"]);
    expect(calls).toBe(2);
});

test("custom-header responses stay in RAM with opaque keys while default headers can use disk", async () => {
    const cache = new RPCCache("private-header-variants", 1, "11".repeat(16));
    rpc.setCache(cache);
    const secret = "probe-credential-do-not-store";
    const originalRead = cache.read;
    /** @type {string[]} */
    const keys = [];
    let diskReads = 0;
    let diskWrites = 0;
    patchWithCleanup(cache, {
        read(table, key, ...args) {
            keys.push(key);
            return originalRead.call(this, table, key, ...args);
        },
        async _readFromDisk() {
            diskReads++;
            return undefined;
        },
        _writeToDisk() {
            diskWrites++;
        },
    });
    mockFetch(() => ({ result: "value" }));
    await rpc(
        "/private-variant",
        {},
        {
            cache: { type: "disk" },
            headers: { Authorization: secret },
        },
    );
    expect(diskReads).toBe(0);
    expect(diskWrites).toBe(0);
    expect(keys[0]).not.toInclude(secret);
    await rpc(
        "/default-variant",
        {},
        {
            cache: { type: "disk" },
            headers: { "Content-Type": "text/plain" },
        },
    );
    expect(diskReads).toBe(1);
    expect(diskWrites).toBe(1);
});

test("custom headers do not bypass cache-settings validation", () => {
    rpc.setCache(new RPCCache("header-settings", 1));
    expect(() =>
        rpc(
            "/invalid-cache-type",
            {},
            {
                cache: { type: "invalid" },
                headers: { "X-Variant": "A" },
            },
        ),
    ).toThrow(/Invalid "type"/);
});

test("evicted header identities are never reassigned to a different response", async () => {
    rpc.setCache(new RPCCache("header-scope-eviction", 1));
    let calls = 0;
    mockFetch((_, init) => {
        calls++;
        return { result: new Headers(init.headers).get("X-Variant") };
    });
    const read = (value) =>
        rpc("/scope-eviction", {}, { cache: true, headers: { "X-Variant": value } });
    for (let i = 0; i < 130; i++) {
        expect(await read(String(i))).toBe(String(i));
    }
    expect(await read("0")).toBe("0");
    expect(calls).toBe(131);
});

test("aborting one cached header variant does not cancel a different variant", async () => {
    rpc.setCache(new RPCCache("header-scope-abort", 1));
    const gate = new Deferred();
    mockFetch(async (_, init) => {
        await gate;
        return { result: new Headers(init.headers).get("X-Variant") };
    });
    const a = rpc("/variant-abort", {}, { cache: true, headers: { "X-Variant": "A" } });
    const b = rpc("/variant-abort", {}, { cache: true, headers: { "X-Variant": "B" } });
    a.abort();
    await expect(a).rejects.toThrow(ConnectionAbortedError);
    gate.resolve();
    expect(await b).toBe("B");
    await tick();
});
