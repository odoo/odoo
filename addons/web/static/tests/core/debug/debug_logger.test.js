// @ts-check

import { after, describe, expect, test } from "@odoo/hoot";
import { isolateLogging } from "@web/../tests/core/debug/logging_helpers";
import {
    disableLogging,
    enableLogging,
    getStats,
    getStatus,
    makeLogger,
    parseSpec,
    resolveKinds,
} from "@web/core/debug/debug_logger";

describe.current.tags("headless");

/** @param {() => void | Promise<void>} body */
async function captureConsoleDebug(body) {
    /** @type {any[][]} */
    const captured = [];
    const original = console.debug;
    console.debug = (...args) => captured.push(args);
    try {
        await body();
    } finally {
        console.debug = original;
    }
    return captured;
}

/** @param {any[][]} captured */
function labels(captured) {
    return captured.map((args) => args[0].replace(/%c/g, ""));
}

function cleanLogging() {
    after(isolateLogging());
}

test("logging cleanup restores a disabled specification without enabling all namespaces", () => {
    cleanLogging();
    disableLogging({ persist: false });
    const restore = isolateLogging();
    enableLogging("test.temporary", { persist: false });
    restore();
    expect(getStatus().spec).toBe("");
    expect(makeLogger("unrelated.namespace").enabled).toBe(false);
});

test("logging cleanup restores a nonempty specification exactly", () => {
    cleanLogging();
    const spec = "test.*:logic,-test.excluded";
    enableLogging(spec, { persist: false });
    const restore = isolateLogging();
    disableLogging({ persist: false });
    restore();
    expect(getStatus().spec).toBe(spec);
    expect(makeLogger("test.allowed").isEnabled("logic")).toBe(true);
    expect(makeLogger("test.excluded").enabled).toBe(false);
});

describe("spec", () => {
    test("a bare namespace enables every kind", () => {
        const rules = parseSpec("web.action");
        expect(rules).toHaveLength(1);
        expect(resolveKinds("web.action", rules)).toBe(15);
        expect(resolveKinds("web.action.sub", rules)).toBe(0);
    });

    test("a glob matches dotted descendants and kinds narrow it", () => {
        const rules = parseSpec("mail.*:perf+lifecycle");
        expect(resolveKinds("mail.store", rules)).toBe(2 | 8);
        expect(resolveKinds("mail.store.record", rules)).toBe(2 | 8);
        expect(resolveKinds("web.action", rules)).toBe(0);
    });

    test("a negated token subtracts from an earlier match", () => {
        const rules = parseSpec("*, -mail.*:lifecycle");
        expect(resolveKinds("mail.store", rules)).toBe(15 & ~8);
        expect(resolveKinds("web.model", rules)).toBe(15);
    });

    test("an unknown kind falls back to every kind", () => {
        expect(resolveKinds("x", parseSpec("x:bogus"))).toBe(15);
    });
});

describe("logger", () => {
    test("is silent and free when disabled", async () => {
        expect.assertions(4);
        cleanLogging();
        disableLogging({ persist: false });
        const log = makeLogger("test.silent");
        expect(log.enabled).toBe(false);
        const captured = await captureConsoleDebug(() => {
            log.logic("a");
            log.pipeline("b");
            log.lifecycle("c");
            const end = log.perf("d");
            expect(end()).toBe(0);
        });
        expect(captured).toHaveLength(0);
        expect(getStats()).toHaveLength(0);
    });

    test("prints namespace, kind and label once enabled", async () => {
        cleanLogging();
        enableLogging("test.on:logic+pipeline", { persist: false });
        const log = makeLogger("test.on");
        expect(log.enabled).toBe(true);
        expect(log.isEnabled("lifecycle")).toBe(false);
        const captured = await captureConsoleDebug(() => {
            log.logic("decide", { a: 1 });
            log.pipeline("stage");
            log.lifecycle("mounted");
        });
        expect(labels(captured)).toEqual([
            "[test.on] logic decide",
            "[test.on] pipeline stage",
        ]);
        expect(captured[0][4]).toEqual({ a: 1 });
    });

    test("lazy data is resolved only when printing", async () => {
        cleanLogging();
        const log = makeLogger("test.lazy");
        let calls = 0;
        const lazy = () => ++calls && { calls };
        disableLogging({ persist: false });
        log.logic("off", lazy);
        expect(calls).toBe(0);
        enableLogging("test.lazy", { persist: false });
        const captured = await captureConsoleDebug(() => log.logic("on", lazy));
        expect(calls).toBe(1);
        expect(captured[0][4]).toEqual({ calls: 1 });
    });

    test("a perf span records stats and reports milliseconds", async () => {
        cleanLogging();
        enableLogging("test.perf:perf", { persist: false });
        const log = makeLogger("test.perf");
        const captured = await captureConsoleDebug(() => {
            log.perf("load")({ rows: 3 });
            log.perf("load")();
        });
        expect(labels(captured)[0]).toMatch(/^\[test\.perf\] perf load \d+\.\d\dms$/);
        expect(captured[0][4]).toEqual({ rows: 3 });
        const [row] = getStats();
        expect(row.ns).toBe("test.perf");
        expect(row.label).toBe("load");
        expect(row.count).toBe(2);
    });

    test("measure wraps sync and async work and rethrows", async () => {
        expect.assertions(5);
        cleanLogging();
        enableLogging("test.measure", { persist: false });
        const log = makeLogger("test.measure");
        await captureConsoleDebug(async () => {
            expect(log.measure("sync", () => 4)).toBe(4);
            expect(await log.measure("async", () => Promise.resolve(5))).toBe(5);
            expect(() =>
                log.measure("throws", () => {
                    throw new Error("boom");
                }),
            ).toThrow("boom");
            await expect(
                log.measure("rejects", () => Promise.reject(new Error("nope"))),
            ).rejects.toThrow("nope");
        });
        expect(
            getStats()
                .map((row) => row.label)
                .sort(),
        ).toEqual(["async", "rejects", "sync", "throws"]);
    });

    test("child namespaces resolve against the spec and status lists them", () => {
        cleanLogging();
        enableLogging("test.parent.*", { persist: false });
        const parent = makeLogger("test.parent");
        const child = parent.child("leaf");
        expect(child.ns).toBe("test.parent.leaf");
        expect(parent.enabled).toBe(false);
        expect(child.enabled).toBe(true);
        expect(makeLogger("test.parent.leaf")).toBe(child);
        expect(getStatus().active).toInclude(
            "test.parent.leaf:logic+perf+pipeline+lifecycle",
        );
    });

    test("a spec change reaches loggers created before it", async () => {
        cleanLogging();
        const log = makeLogger("test.late");
        expect(log.enabled).toBe(false);
        enableLogging("test.late", { persist: false });
        expect(log.enabled).toBe(true);
        disableLogging({ persist: false });
        expect(log.enabled).toBe(false);
    });

    test("the state lives on the window so every bundle copy shares it", () => {
        cleanLogging();
        const shared = /** @type {any} */ (globalThis).__odooLogState;
        const log = makeLogger("test.shared");
        expect(shared.loggers.get("test.shared")).toBe(log);
        enableLogging("test.shared", { persist: false });
        expect(shared.spec).toBe("test.shared");
        expect(log.enabled).toBe(true);
    });
});
