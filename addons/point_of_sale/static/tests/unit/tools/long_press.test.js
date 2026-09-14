import { expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { useLongPress } from "@point_of_sale/app/hooks/long_press_hook";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

async function mountPress() {
    class Press extends Component {
        static props = {};
        static template = xml`<div/>`;
        setup() {
            this.press = useLongPress((product) => expect.step(product), 500);
        }
    }
    return mountWithCleanup(Press);
}

test("a new press replaces the pending product and restarts its deadline", async () => {
    const { press } = await mountPress();
    press.onTouchStart("first");
    await advanceTime(300);
    press.onTouchStart("second");
    await advanceTime(200);
    expect.verifySteps([]);
    await advanceTime(300);
    expect.verifySteps(["second"]);
});

for (const cancel of [
    "onMouseUp",
    "onMouseLeave",
    "onTouchEnd",
    "onTouchCancel",
    "onScroll",
]) {
    test(`${cancel} cancels overlapping press starts`, async () => {
        const { press } = await mountPress();
        press.onTouchStart("touch");
        press.onMouseDown({ button: 0 }, "mouse");
        press[cancel]();
        await advanceTime(600);
        expect.verifySteps([]);
    });
}

test("destroy cancels every press started by the component", async () => {
    const component = await mountPress();
    component.press.onTouchStart("first");
    component.press.onTouchStart("second");
    component.__owl__.app.destroy();
    await advanceTime(600);
    expect.verifySteps([]);
});
