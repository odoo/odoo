import { expect, getFixture, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { Component, useRef, xml } from "@odoo/owl";
import { useTimedPress } from "@point_of_sale/app/utils/use_timed_press";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

test("unmount cancels a pending long press", async () => {
    class Button extends Component {
        static props = {};
        static template = xml`<button t-ref="button">Press</button>`;
        setup() {
            useTimedPress(useRef("button"), [
                {
                    type: "hold",
                    delay: 500,
                    callback: () => expect.step("long press"),
                },
            ]);
        }
    }
    const component = await mountWithCleanup(Button);
    getFixture()
        .querySelector("button")
        .dispatchEvent(new PointerEvent("pointerdown", { button: 0 }));
    component.__owl__.app.destroy();
    await advanceTime(600);
    expect.verifySteps([]);
});

for (const otherEvent of ["pointerup", "pointerleave", "pointercancel"]) {
    test(`another finger's ${otherEvent} does not end the active press`, async () => {
        class Button extends Component {
            static props = {};
            static template = xml`<button t-ref="button">Press</button>`;
            setup() {
                useTimedPress(useRef("button"), [
                    {
                        type: "hold",
                        delay: 500,
                        callback: (event) => expect.step(`hold ${event.pointerId}`),
                    },
                ]);
            }
        }
        await mountWithCleanup(Button);
        const button = getFixture().querySelector("button");
        button.dispatchEvent(
            new PointerEvent("pointerdown", { button: 0, pointerId: 1 }),
        );
        await advanceTime(100);
        button.dispatchEvent(
            new PointerEvent("pointerdown", { button: 0, pointerId: 2 }),
        );
        button.dispatchEvent(new PointerEvent(otherEvent, { button: 0, pointerId: 2 }));
        await advanceTime(500);
        expect.verifySteps(["hold 1"]);
    });
}
