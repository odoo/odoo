import { Component, onWillStart, xml } from "@odoo/owl";
import { test, expect, beforeEach, getFixture } from "@odoo/hoot";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-mock";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { click, press } from "@odoo/hoot-dom";
import { Deferred } from "@web/core/utils/concurrency";

let target;

beforeEach(async () => {
    await mountWithCleanup(MainComponentsContainer);
    target = getFixture();
});

test("simple use", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    expect(".o_popover").toHaveCount(0);

    const remove = getService("popover").add(target, Comp);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    remove();
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);
});

test("close on click away", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    getService("popover").add(target, Comp);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    click(document.body);
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);
});

test("close on click away when loading", async () => {
    const def = new Deferred();
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
        setup() {
            onWillStart(async () => {
                await def;
            });
        }
    }

    getService("popover").add(target, Comp);
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);

    click(document.body);
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);

    def.resolve();
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);
});

test.tags("desktop")("close on 'Escape' keydown", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    getService("popover").add(target, Comp);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    press("Escape");
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);
});

test("do not close on click away", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    const remove = getService("popover").add(target, Comp, {}, { closeOnClickAway: false });
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    click(document.body);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    remove();
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);
});

test("close callback", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    function onClose() {
        expect.step("close");
    }

    getService("popover").add(target, Comp, {}, { onClose });
    await animationFrame();

    click(document.body);
    await animationFrame();

    expect.verifySteps(["close"]);
});

test("sub component triggers close", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp" t-on-click="() => this.props.close()">in popover</div>`;
        static props = ["*"];
    }

    getService("popover").add(target, Comp);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    click("#comp");
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);
});

test("close popover if target is removed", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    getService("popover").add(target, Comp);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    target.remove();
    await animationFrame();

    expect(".o_popover").toHaveCount(0);
    expect(".o_popover #comp").toHaveCount(0);
});

test("close and do not crash if target parent does not exist", async () => {
    // This target does not have any parent, it simulates the case where the element disappeared
    // from the DOM before the setup of the component
    const dissapearedTarget = document.createElement("div");

    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    function onClose() {
        expect.step("close");
    }

    getService("popover").add(dissapearedTarget, Comp, {}, { onClose });
    await animationFrame();

    expect.verifySteps(["close"]);
});

test("keep popover if target sibling is removed", async () => {
    class Comp extends Component {
        static template = xml`<div id="comp">in popover</div>`;
        static props = ["*"];
    }

    class Sibling extends Component {
        static template = xml`<div id="sibling">Sibling</div>`;
        static props = ["*"];
    }

    await mountWithCleanup(Sibling, { noMainContainer: true });

    getService("popover").add(target, Comp);
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);

    target.querySelector("#sibling").remove();
    await animationFrame();

    expect(".o_popover").toHaveCount(1);
    expect(".o_popover #comp").toHaveCount(1);
});
