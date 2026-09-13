// @ts-check

import {
    after,
    beforeEach,
    Deferred,
    describe,
    expect,
    runAllTimers,
    test,
    tick,
} from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { mockIndexedDBForTests } from "@web/../tests/_framework/mock_indexed_db.hoot";
import { isolateLogging } from "@web/../tests/core/debug/logging_helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { enableLogging, makeLogger } from "@web/core/debug/debug_logger";
import { ConnectionLostError, rpc, rpcBus, RPCError } from "@web/core/network/rpc";
import { RPCCache } from "@web/core/network/rpc_cache";
import { globalSingleton } from "@web/core/utils/global_singleton";

describe.current.tags("headless");
mockIndexedDBForTests();
const log = makeLogger("web.rpc.snapshot");

beforeEach(() => {
    after(isolateLogging());
    enableLogging("web.rpc,web.rpc.snapshot", { persist: false });
    const state = /** @type {any} */ (globalSingleton("rpc", () => ({})));
    const previous = state.rpcCache;
    const cache = new RPCCache("snapshot", 1, "11".repeat(16));
    rpc.setCache(cache);
    after(() => {
        cache.invalidate();
        rpc.setCache(previous);
    });
});

for (const settings of [
    { dedup: true },
    { cache: true },
    { dedup: true, cache: true },
]) {
    test(`one serialization defines key and body ${JSON.stringify(settings)}`, async () => {
        let serializations = 0;
        let calls = 0;
        const gate = new Deferred();
        const params = { value: { toJSON: () => ++serializations } };
        mockFetch(async (_, { body }) => {
            calls++;
            const value = JSON.parse(String(body)).params.value;
            await gate;
            return { result: value };
        });
        const a = rpc("/snapshot", params, settings);
        const b = rpc("/snapshot", { value: 1 }, settings);
        gate.resolve();
        expect(await Promise.all([a, b])).toEqual([1, 1]);
        expect(calls).toBe(1);
        expect(serializations).toBe(1);
        log.logic("one snapshot", { settings, calls, serializations });
    });
}

test("disk lookup cannot change the request after its cache key is chosen", async () => {
    const state = /** @type {any} */ (globalSingleton("rpc", () => ({})));
    const gate = new Deferred();
    patchWithCleanup(state.rpcCache, {
        async _readFromDisk() {
            await gate;
            return undefined;
        },
        _writeToDisk() {},
    });
    let calls = 0;
    mockFetch((_, { body }) => {
        calls++;
        return { result: JSON.parse(String(body)).params.ids };
    });
    const params = { ids: [1] };
    const pending = rpc("/deferred-snapshot", params, { cache: { type: "disk" } });
    params.ids.push(2);
    gate.resolve();
    expect(await pending).toEqual([1]);
    expect(await rpc("/deferred-snapshot", { ids: [1] }, { cache: true })).toEqual([1]);
    expect(calls).toBe(1);
    log.logic("deferred cache snapshot", { calls, callerIds: params.ids });
});

test("retry retains the snapshot despite caller and bus-listener mutations", async () => {
    let serializations = 0;
    const params = { value: 1, converted: { toJSON: () => ++serializations } };
    const requests = [];
    const mutate = ({ detail }) => {
        detail.data.params.value = 99;
    };
    rpcBus.addEventListener("RPC:REQUEST", mutate);
    after(() => rpcBus.removeEventListener("RPC:REQUEST", mutate));
    mockFetch((_, { body }) => {
        requests.push(JSON.parse(String(body)).params);
        if (requests.length === 1) {
            throw new TypeError("network unavailable");
        }
        return { result: requests.at(-1) };
    });
    const pending = rpc("/retry-snapshot", params, {
        retry: { retries: 1, baseMs: 1, maxMs: 1 },
    });
    params.value = 2;
    await tick();
    expect(await pending).toEqual({ value: 1, converted: 1 });
    expect(requests).toEqual([
        { value: 1, converted: 1 },
        { value: 1, converted: 1 },
    ]);
    expect(serializations).toBe(1);
    expect(params.value).toBe(2);
    log.logic("retry snapshot", { requests, serializations });
});

test("root toJSON receives params and can omit the entire field", async () => {
    const keys = [];
    mockFetch((_, { body }) => {
        const data = JSON.parse(String(body));
        return { result: Object.hasOwn(data, "params") };
    });
    expect(
        await rpc(
            "/omit-snapshot",
            {
                toJSON(key) {
                    keys.push(key);
                },
            },
            { dedup: true },
        ),
    ).toBe(false);
    expect(keys).toEqual(["params"]);
    log.logic("omitted params", { keys });
});

test("RPC interception transforms the logical call once before snapshotting", async () => {
    let interceptions = 0;
    patchWithCleanup(rpc, {
        _rpc(url, params, settings) {
            interceptions++;
            return super._rpc(url, { ...params, intercepted: interceptions }, settings);
        },
    });
    mockFetch((_, { body }) => ({ result: JSON.parse(String(body)).params }));
    expect(await rpc("/interception", {}, { cache: true, dedup: true })).toEqual({
        intercepted: 1,
    });
    expect(interceptions).toBe(1);
    log.logic("interception boundary", { interceptions });
});

test("serialization failures leave no cache or dedup entry behind", async () => {
    const settings = { cache: true, dedup: true };
    let fail = true;
    const params = {
        toJSON() {
            if (fail) {
                throw new Error("serialization failed");
            }
            return { value: 1 };
        },
    };
    expect(() => rpc("/serialization-failure", params, settings)).toThrow(
        "serialization failed",
    );
    fail = false;
    mockFetch((_, { body }) => ({ result: JSON.parse(String(body)).params.value }));
    expect(await rpc("/serialization-failure", params, settings)).toBe(1);
    log.logic("serialization recovery");
});

for (const value of [null, undefined]) {
    test(`a server error retains its type when params serialize to ${value}`, async () => {
        let calls = 0;
        mockFetch(() => {
            calls++;
            return { error: { code: 200, message: "Invalid params" } };
        });
        await expect(
            rpc("/invalid-params", { toJSON: () => value }, { retry: 1 }),
        ).rejects.toThrow(RPCError);
        expect(calls).toBe(1);
        log.logic("server rejection", { value, calls });
    });
}

for (const kind of ["record", "pairs", "Headers"]) {
    test(`cached retries retain caller header identity (${kind})`, async () => {
        /** @type {HeadersInit} */
        const headers =
            kind === "Headers"
                ? new Headers({ "X-Variant": "A" })
                : kind === "pairs"
                  ? [["X-Variant", "A"]]
                  : { "X-Variant": "A" };
        const seen = [];
        mockFetch((_, init) => {
            const variant = new Headers(init.headers).get("X-Variant");
            seen.push(variant);
            if (seen.length === 1) {
                throw new TypeError("network unavailable");
            }
            return { result: variant };
        });
        const pending = rpc(
            "/header-snapshot",
            {},
            {
                headers,
                cache: true,
                retry: { retries: 1, baseMs: 1, maxMs: 1 },
            },
        );
        if (headers instanceof Headers) {
            headers.set("X-Variant", "B");
        } else if (Array.isArray(headers)) {
            headers[0][1] = "B";
        } else {
            headers["X-Variant"] = "B";
        }
        await tick();
        expect(await pending).toBe("A");
        expect(
            await rpc(
                "/header-snapshot",
                {},
                {
                    headers: { "X-Variant": "A" },
                    cache: true,
                },
            ),
        ).toBe("A");
        expect(seen).toEqual(["A", "A"]);
        log.logic("header identity", { kind, seen });
    });
}

test("request event settings cannot change a retry or the caller settings", async () => {
    const settings = {
        headers: new Headers({ "X-Variant": "A" }),
        silent: true,
        retry: { retries: 1, baseMs: 1, maxMs: 1 },
    };
    const seen = [];
    const events = [];
    const responses = [];
    const mutate = ({ detail }) => {
        events.push(detail.settings.silent);
        detail.settings.headers.set("X-Variant", "B");
        detail.settings.silent = false;
    };
    rpcBus.addEventListener("RPC:REQUEST", mutate);
    after(() => rpcBus.removeEventListener("RPC:REQUEST", mutate));
    const onResponse = ({ detail }) => responses.push(detail.settings.silent);
    rpcBus.addEventListener("RPC:RESPONSE", onResponse);
    after(() => rpcBus.removeEventListener("RPC:RESPONSE", onResponse));
    mockFetch((_, init) => {
        seen.push(new Headers(init.headers).get("X-Variant"));
        if (seen.length === 1) {
            throw new TypeError("network unavailable");
        }
        return { result: true };
    });
    const pending = rpc("/event-settings", {}, settings);
    await tick();
    expect(await pending).toBe(true);
    expect(seen).toEqual(["A", "A"]);
    expect(events).toEqual([true, true]);
    expect(responses).toEqual([true, true]);
    expect(settings.headers.get("X-Variant")).toBe("A");
    expect(settings.silent).toBe(true);
    log.logic("event settings isolation", { seen, events });
});

test("parameter serialization cannot mutate the captured retry options", async () => {
    const settings = { retry: { retries: 1, baseMs: 1, maxMs: 1 } };
    let calls = 0;
    mockFetch(() => {
        if (++calls === 1) {
            throw new TypeError("network unavailable");
        }
        return { result: true };
    });
    const pending = rpc(
        "/retry-options",
        {
            toJSON() {
                settings.retry.retries = 0;
                return {};
            },
        },
        settings,
    );
    // Attach before advancing the clock so a regression does not create an
    // unrelated unhandled rejection in the test runner.
    const outcome = pending.catch((error) => error);
    await tick();
    expect(await outcome).toBe(true);
    expect(calls).toBe(2);
    log.logic("captured retry options", { calls });
});

test("retry rejects an initial setup failure through its returned promise", async () => {
    await expect(
        rpc("/invalid-timeout", {}, { timeout: -1, retry: 1 }),
    ).rejects.toThrow(TypeError);
    log.logic("initial retry setup rejected");
});

test("a later retry setup failure settles the chain instead of escaping its timer", async () => {
    const scheduled = new Deferred();
    const setupError = new Error("timeout setup failed");
    let setups = 0;
    let retry = () => {};
    patchWithCleanup(AbortSignal, {
        timeout() {
            if (++setups === 2) {
                throw setupError;
            }
            return new AbortController().signal;
        },
    });
    patchWithCleanup(browser, {
        setTimeout(callback) {
            retry = /** @type {() => void} */ (callback);
            scheduled.resolve();
            return 123;
        },
    });
    mockFetch(() => {
        throw new TypeError("network unavailable");
    });
    /** @type {unknown} */
    let outcome;
    const pending = rpc("/retry-setup", {}, { timeout: 100, retry: 1 });
    pending.then(
        (value) => {
            outcome = value;
        },
        (error) => {
            outcome = error;
        },
    );
    await scheduled;
    expect(() => retry()).not.toThrow();
    await Promise.resolve();
    expect(outcome).toBe(setupError);
    expect(setups).toBe(2);
    pending.abort(false);
    log.logic("later retry setup rejected", {
        setups,
        settled: outcome === setupError,
    });
});

for (const inherited of [false, true]) {
    test(`capture a ${inherited ? "inherited" : "non-enumerable"} supported option once`, async () => {
        let reads = 0;
        const options = Object.defineProperty({}, "silent", {
            get() {
                reads++;
                return true;
            },
        });
        const settings = inherited ? Object.create(options) : options;
        const flags = [];
        const onRequest = ({ detail }) => flags.push(detail.settings.silent);
        rpcBus.addEventListener("RPC:REQUEST", onRequest);
        after(() => rpcBus.removeEventListener("RPC:REQUEST", onRequest));
        mockFetch(() => ({ result: true }));
        expect(await rpc("/option-accessor", {}, settings)).toBe(true);
        expect(flags).toEqual([true]);
        expect(reads).toBe(1);
        log.logic("option capture", { inherited, reads, flags });
    });
}

for (const retry of [0, 1]) {
    test(`synchronously throwing transport balances events (retry=${retry})`, async () => {
        const requests = [];
        const responses = [];
        const onRequest = ({ detail }) => requests.push(detail.data.id);
        const onResponse = ({ detail }) => responses.push(detail.data.id);
        rpcBus.addEventListener("RPC:REQUEST", onRequest);
        rpcBus.addEventListener("RPC:RESPONSE", onResponse);
        after(() => {
            rpcBus.removeEventListener("RPC:REQUEST", onRequest);
            rpcBus.removeEventListener("RPC:RESPONSE", onResponse);
        });
        patchWithCleanup(browser, {
            fetch() {
                throw new TypeError("transport wrapper failed");
            },
        });
        /** @type {unknown} */
        let outcome;
        let returnedPromise = false;
        let done;
        try {
            const pending = rpc(
                "/sync-transport",
                {},
                {
                    retry: retry ? { retries: retry, baseMs: 1, maxMs: 1 } : 0,
                },
            );
            returnedPromise = typeof pending?.then === "function";
            done = pending.catch((error) => {
                outcome = error;
            });
        } catch (error) {
            outcome = error;
        }
        await runAllTimers();
        await done;
        expect(returnedPromise).toBe(true);
        expect(outcome).toBeInstanceOf(ConnectionLostError);
        expect(requests).toHaveLength(retry + 1);
        expect(responses).toEqual(requests);
        log.logic("transport lifecycle balance", {
            returnedPromise,
            requests,
            responses,
        });
    });
}
