// @ts-check

import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useRenderCounter } from "@web/core/utils/render_instrumentation";

describe.current.tags("headless");

beforeEach(() => {
    globalThis.__renderReset();
});

afterEach(() => {
    globalThis.__renderTrace = false;
    globalThis.__renderReset();
});

test("globals are installed", () => {
    expect(typeof globalThis.__renderStats).toBe("function");
    expect(typeof globalThis.__renderReset).toBe("function");
    expect(Boolean(globalThis.__renderTrace)).toBe(false);
});

test("counter increments per render when trace is on", async () => {
    class Probe extends Component {
        static template = xml`<span><t t-out="this.state.tick"/></span>`;
        static props = {};
        setup() {
            useRenderCounter("probe");
            this.state = useState({ tick: 0 });
        }
    }
    globalThis.__renderTrace = true;
    const probe = await mountWithCleanup(Probe);
    expect(globalThis.__renderStats().probe).toBe(1);

    probe.state.tick = 1;
    await animationFrame();
    expect(globalThis.__renderStats().probe).toBe(2);

    probe.state.tick = 2;
    await animationFrame();
    expect(globalThis.__renderStats().probe).toBe(3);
});

test("counter is a no-op when trace is off", async () => {
    class Probe extends Component {
        static template = xml`<span><t t-out="this.state.tick"/></span>`;
        static props = {};
        setup() {
            useRenderCounter("probe");
            this.state = useState({ tick: 0 });
        }
    }
    const probe = await mountWithCleanup(Probe);
    expect(globalThis.__renderStats().probe).toBe(undefined);
    probe.state.tick = 1;
    await animationFrame();
    expect(globalThis.__renderStats().probe).toBe(undefined);
});

test("__renderReset clears all counters", async () => {
    class Probe extends Component {
        static template = xml`<span/>`;
        static props = {};
        setup() {
            useRenderCounter("probe");
        }
    }
    globalThis.__renderTrace = true;
    await mountWithCleanup(Probe);
    expect(globalThis.__renderStats().probe).toBe(1);
    globalThis.__renderReset();
    expect(globalThis.__renderStats().probe).toBe(undefined);
});

test("multiple labels are tracked independently", async () => {
    class A extends Component {
        static template = xml`<span/>`;
        static props = {};
        setup() {
            useRenderCounter("A");
        }
    }
    class B extends Component {
        static template = xml`<span/>`;
        static props = {};
        setup() {
            useRenderCounter("B");
        }
    }
    globalThis.__renderTrace = true;
    await mountWithCleanup(A);
    await mountWithCleanup(B);
    await mountWithCleanup(B);
    const stats = globalThis.__renderStats();
    expect(stats.A).toBe(1);
    expect(stats.B).toBe(2);
});
