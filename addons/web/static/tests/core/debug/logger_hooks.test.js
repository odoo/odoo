// @ts-check

import { after, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { isolateLogging } from "@web/../tests/core/debug/logging_helpers";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import {
    disableLogging,
    enableLogging,
    getStats,
    makeLogger,
} from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";

describe.current.tags("headless");

/** @param {() => unknown} body */
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

function makeProbe() {
    const log = makeLogger("test.hooks");
    class Probe extends Component {
        static template = xml`<span><t t-esc="state.tick"/></span>`;
        static props = {};
        setup() {
            useLifecycleLog(log);
            this.state = useState({ tick: 0 });
        }
    }
    return Probe;
}

test("registers no willStart and no willUpdateProps: a mount awaits nothing extra", async () => {
    expect.assertions(2);
    cleanLogging();
    /** @type {any} */
    let node;
    const log = makeLogger("test.hooks");
    class Probe extends Component {
        static template = xml`<span/>`;
        static props = {};
        setup() {
            useLifecycleLog(log);
            node = /** @type {any} */ (this).__owl__;
        }
    }
    await mountWithCleanup(Probe);
    expect(node.willStart).toHaveLength(0);
    expect(node.willUpdateProps).toHaveLength(0);
});

test("logs nothing and records nothing when the namespace is off", async () => {
    expect.assertions(2);
    cleanLogging();
    disableLogging({ persist: false });
    const Probe = makeProbe();
    const captured = await captureConsoleDebug(async () => {
        const probe = await mountWithCleanup(Probe);
        probe.state.tick = 1;
        await animationFrame();
    });
    expect(captured).toHaveLength(0);
    expect(getStats()).toHaveLength(0);
});

test("logs setup, mounted, a patch pair and a render span per render", async () => {
    expect.assertions(4);
    cleanLogging();
    enableLogging("test.hooks", { persist: false });
    const Probe = makeProbe();
    const captured = await captureConsoleDebug(async () => {
        const probe = await mountWithCleanup(Probe);
        probe.state.tick = 1;
        await animationFrame();
    });
    const seen = labels(captured);
    expect(seen[0]).toBe("[test.hooks] lifecycle Probe setup");
    expect(seen[1]).toMatch(/^\[test\.hooks\] perf Probe render \d+\.\d\dms$/);
    expect(seen).toInclude("[test.hooks] lifecycle Probe mounted");
    expect(seen.filter((label) => /willPatch#1|patched#1/.test(label))).toHaveLength(2);
});

test("render and patch spans are measured, so the stats table can rank them", async () => {
    expect.assertions(3);
    cleanLogging();
    enableLogging("test.hooks:perf", { persist: false });
    const Probe = makeProbe();
    const captured = await captureConsoleDebug(async () => {
        const probe = await mountWithCleanup(Probe);
        probe.state.tick = 1;
        await animationFrame();
    });
    const rows = Object.fromEntries(getStats().map((row) => [row.label, row]));
    expect(rows["Probe render"].count).toBe(2);
    expect(rows["Probe patch"].count).toBe(1);
    expect(
        labels(captured).map((label) =>
            label.replace(/^\[test\.hooks\] perf Probe (\w+) \d+\.\d\dms$/, "$1"),
        ),
    ).toEqual(["render", "render", "patch"]);
});
