// @ts-check

import "@web/webclient/debug/profiling/profiling_service";

import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";

describe.current.tags("headless");

/** @returns {any} */
function debugItemFactory() {
    return registry.category("debug").category("default").get("profilingItem");
}

/** @param {string} tag */
function fakeProfilingService(tag) {
    return {
        profilingItem: () => ({ type: "component", tag }),
    };
}

describe("the profiling debug item is registered once, resolved per env", () => {
    test("it is registered at module scope, not per service construction", () => {
        expect(typeof debugItemFactory()).toBe("function", {
            message:
                "the entry must exist without any ProfilingService having been " +
                "constructed; it used to be added from the constructor",
        });
    });

    test("it resolves against the env it is asked about", () => {
        const factory = debugItemFactory();
        const first = factory({
            env: { services: { profiling: fakeProfilingService("first") } },
        });
        const second = factory({
            env: { services: { profiling: fakeProfilingService("second") } },
        });

        expect(first.tag).toBe("first");
        expect(second.tag).toBe("second");
    });

    test("it yields nothing when the service did not start", () => {
        expect(debugItemFactory()({ env: { services: {} } })).toBe(null);
    });
});

test("profiling serializes derived parameter edits without losing earlier keys", async () => {
    const first = new Deferred();
    const calls = [];
    const service = registry
        .category("services")
        .get("profiling")
        .start(
            { debug: true },
            {
                action: {},
                lazy_session: { getValue: async () => false },
                orm: {
                    call: async (_model, _method, _args, kwargs) => {
                        calls.push(kwargs);
                        if (calls.length === 1) {
                            await first;
                        }
                        return {
                            session: false,
                            collectors: kwargs.collectors,
                            params: kwargs.params,
                        };
                    },
                },
            },
        );
    const a = service.setParam("first", 1);
    const b = service.setParam("second", 2);
    await Promise.resolve();
    expect(calls).toHaveLength(1);
    first.resolve();
    await Promise.all([a, b]);
    expect(service.state.params).toEqual({ first: 1, second: 2 });
    expect(calls[1].params).toEqual({ first: 1, second: 2 });
});

test("a rejected profiling mutation does not poison the next queued edit", async () => {
    let calls = 0;
    const service = registry
        .category("services")
        .get("profiling")
        .start(
            { debug: true },
            {
                action: {},
                lazy_session: { getValue: async () => false },
                orm: {
                    call: async (_model, _method, _args, kwargs) => {
                        makeLogger("web.profiling.test").logic("mutation", {
                            params: kwargs.params,
                        });
                        if (++calls === 1) {
                            throw new Error("first mutation rejected");
                        }
                        return {
                            session: false,
                            collectors: kwargs.collectors,
                            params: kwargs.params,
                        };
                    },
                },
            },
        );
    const first = service.setParam("rejected", 1).catch((error) => error.message);
    const second = service.setParam("accepted", 2);
    expect(await first).toBe("first mutation rejected");
    await second;
    expect(calls).toBe(2);
    expect(service.state.params).toEqual({ accepted: 2 });
});
