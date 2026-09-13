// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { ModelEvent } from "@web/core/events";
import { UrgentSaveCoordinator } from "@web/model/relational_model/urgent_save_coordinator";

describe.current.tags("headless");

test("a throwing bus trigger leaves urgent saving idle and usable", async () => {
    let notifications = 0;
    const coord = new UrgentSaveCoordinator({
        trigger: (_event, payload) => {
            if (++notifications === 1) {
                payload.proms.push(Promise.reject(new Error("registered work failed")));
                throw new Error("notification failed");
            }
        },
    });
    await expect(coord.run(async () => "unreachable")).rejects.toThrow(
        "notification failed",
    );
    makeLogger("web.model.audit").logic("urgent notification failure cleanup", {
        status: coord.status,
    });
    expect(coord.isActive).toBe(false);
    expect(await coord.run(async () => "saved")).toBe("saved");
    expect(notifications).toBe(2);
    expect(coord.isActive).toBe(false);
});

test("new instance starts idle and isActive=false", () => {
    const coord = new UrgentSaveCoordinator();
    expect(coord.status).toBe("idle");
    expect(coord.isActive).toBe(false);
});

test("run() flips status active during fn, idle after", async () => {
    const coord = new UrgentSaveCoordinator();
    /** @type {boolean} */
    let snapshot;
    const result = await coord.run(async () => {
        snapshot = coord.isActive;
        return 42;
    });
    expect(snapshot).toBe(true);
    expect(result).toBe(42);
    expect(coord.isActive).toBe(false);
});

test("run() restores status even when fn throws", async () => {
    const coord = new UrgentSaveCoordinator();
    await expect(
        coord.run(async () => {
            throw new Error("boom");
        }),
    ).rejects.toThrow("boom");
    expect(coord.isActive).toBe(false);
});

test("run() fires WILL_SAVE_URGENTLY on the bus at entry", async () => {
    const events = [];
    const bus = { trigger: (event, payload) => events.push({ event, payload }) };
    const coord = new UrgentSaveCoordinator(bus);
    await coord.run(async () => {});
    expect(events.length).toBe(1);
    expect(events[0].event).toBe("WILL_SAVE_URGENTLY");
});

test("nested run() is re-entrant: joins the active run without throwing", async () => {
    const events = [];
    const bus = { trigger: (event) => events.push(event) };
    const coord = new UrgentSaveCoordinator(bus);
    /** @type {boolean} */
    let innerActive;
    const result = await coord.run(async () => {
        const inner = await coord.run(async () => {
            innerActive = coord.isActive;
            return "inner";
        });
        return `outer+${inner}`;
    });
    expect(result).toBe("outer+inner");
    expect(innerActive).toBe(true);
    expect(coord.isActive).toBe(false);
    expect(events.filter((e) => e === "WILL_SAVE_URGENTLY").length).toBe(1);
});

test("awaitUnlessUrgent resolves promise normally when idle", async () => {
    const coord = new UrgentSaveCoordinator();
    const result = await coord.awaitUnlessUrgent(Promise.resolve("real value"));
    expect(result).toBe("real value");
});

test("awaitUnlessUrgent returns undefined when active (does not await)", async () => {
    const coord = new UrgentSaveCoordinator();
    let resolved = false;
    const slow = new Promise((r) => {
        setTimeout(() => {
            resolved = true;
            r("eventually");
        }, 0);
    });
    await coord.run(async () => {
        const result = await coord.awaitUnlessUrgent(slow);
        expect(result).toBe(undefined);
        expect(resolved).toBe(false);
    });
});

test("awaitUnlessUrgent accepts undefined promise without throwing", async () => {
    const coord = new UrgentSaveCoordinator();
    const result = await coord.awaitUnlessUrgent(undefined);
    expect(result).toBe(undefined);
});

test("unlessUrgent invokes fn when idle and returns its value", async () => {
    const coord = new UrgentSaveCoordinator();
    let called = false;
    const result = coord.unlessUrgent(() => {
        called = true;
        return "fired";
    });
    expect(called).toBe(true);
    expect(result).toBe("fired");
});

test("unlessUrgent does NOT invoke fn when active", async () => {
    const coord = new UrgentSaveCoordinator();
    await coord.run(async () => {
        let called = false;
        const result = coord.unlessUrgent(() => {
            called = true;
            return "should not happen";
        });
        expect(called).toBe(false);
        expect(result).toBe(undefined);
    });
});

test("unlessUrgent propagates promise return when idle", async () => {
    const coord = new UrgentSaveCoordinator();
    const result = await coord.unlessUrgent(async () => "async value");
    expect(result).toBe("async value");
});

describe("the reentrant drain is bounded", () => {
    test("a save that keeps re-entering still returns", async () => {
        const coordinator = new UrgentSaveCoordinator();
        let spawned = 0;
        const reenter = () => {
            spawned++;
            return coordinator.run(async () => {
                await Promise.resolve();
                if (coordinator.isActive && spawned < 400) {
                    reenter();
                }
            });
        };
        const warnings = [];
        const originalWarn = console.warn;
        console.warn = (...args) => warnings.push(args.join(" "));
        try {
            await coordinator.run(async () => {
                reenter();
            });
        } finally {
            console.warn = originalWarn;
        }
        expect(spawned).toBeGreaterThan(100);
        expect(warnings.length).toBe(1);
        expect(warnings[0]).toInclude("did not settle");
    });

    test("a drain that does settle emits no warning and ends idle", async () => {
        const coordinator = new UrgentSaveCoordinator();
        const warnings = [];
        const originalWarn = console.warn;
        console.warn = (...args) => warnings.push(args.join(" "));
        try {
            await coordinator.run(async () => {
                coordinator.run(async () => {
                    await Promise.resolve();
                });
            });
        } finally {
            console.warn = originalWarn;
        }
        expect(warnings.length).toBe(0);
        expect(coordinator.status).toBe("idle");
        expect(coordinator.isActive).toBe(false);
    });
});

test("flushPendingEdits() fires WILL_SAVE_URGENTLY synchronously, in urgent mode", () => {
    /** @type {boolean[]} */
    const seenActive = [];
    const bus = { trigger: () => seenActive.push(coord.isActive) };
    const coord = new UrgentSaveCoordinator(bus);
    const done = coord.flushPendingEdits();
    expect(seenActive).toEqual([true]);
    expect(done).toBeInstanceOf(Promise);
});

test("Owl listener exceptions are reported globally while urgent save continues", async () => {
    expect.errors(1);
    const bus = new EventBus();
    let workSettled = false;
    bus.addEventListener(
        ModelEvent.WILL_SAVE_URGENTLY,
        ({ detail }) => {
            detail.proms.push(
                Promise.resolve().then(() => {
                    workSettled = true;
                }),
            );
            throw new Error("urgent listener failed");
        },
        { once: true },
    );
    const coordinator = new UrgentSaveCoordinator(bus);
    const result = await coordinator.run(async () => "saved");
    await animationFrame();
    makeLogger("web.model.audit").logic("Owl urgent event boundary", {
        result,
        workSettled,
        active: coordinator.isActive,
    });
    expect(result).toBe("saved");
    expect(workSettled).toBe(true);
    expect(coordinator.isActive).toBe(false);
    expect.verifyErrors([/urgent listener failed/]);
});
