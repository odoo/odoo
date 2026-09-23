import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, reactive, useState, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useComputed } from "@web/core/utils/computed";

describe.current.tags("headless");

function makeProbe(source) {
    class Probe extends Component {
        static template = xml`<span><t t-out="this.total()"/>|<t t-out="this.total()"/></span>`;
        static props = {};
        setup() {
            this.state = useState({ factor: 1 });
            this.total = useComputed(
                (track) => {
                    expect.step("compute");
                    const tracked = track(source);
                    return tracked.a + tracked.b * this.state.factor;
                },
                () => [this.state.factor],
            );
        }
    }
    return Probe;
}

test("computes once however often the render reads it", async () => {
    const source = reactive({ a: 1, b: 2, unrelated: 0 });
    await mountWithCleanup(makeProbe(source));
    expect("span").toHaveText("3|3");
    expect.verifySteps(["compute"]);
});

test("a change to what it read re-renders with the new value", async () => {
    const source = reactive({ a: 1, b: 2, unrelated: 0 });
    await mountWithCleanup(makeProbe(source));
    expect.verifySteps(["compute"]);
    source.a = 10;
    await animationFrame();
    expect("span").toHaveText("12|12");
    expect.verifySteps(["compute"]);
});

test("a change to something it did not read does not recompute", async () => {
    const source = reactive({ a: 1, b: 2, unrelated: 0 });
    await mountWithCleanup(makeProbe(source));
    expect.verifySteps(["compute"]);
    source.unrelated = 5;
    await animationFrame();
    expect.verifySteps([]);
});

test("a changed key recomputes", async () => {
    const source = reactive({ a: 1, b: 2, unrelated: 0 });
    const probe = await mountWithCleanup(makeProbe(source));
    expect.verifySteps(["compute"]);
    probe.state.factor = 3;
    await animationFrame();
    expect("span").toHaveText("7|7");
    expect.verifySteps(["compute"]);
});
