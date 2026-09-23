// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryOne, queryRect } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useRef, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useDraggable } from "@web/core/utils/dnd/draggable";

/**
 * @param {EventTarget} target
 * @param {string} type
 * @param {{x: number, y: number}} pos
 */
function dispatchPointer(target, type, pos) {
    target.dispatchEvent(
        new PointerEvent(type, {
            bubbles: true,
            cancelable: true,
            button: 0,
            pointerId: 1,
            clientX: pos.x,
            clientY: pos.y,
        }),
    );
}

/** @param {Record<string, any>} [hookParams] */
function makeDraggableList(hookParams = {}) {
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i"
                        class="item" style="height: 30px;"/>
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({ ref: useRef("root"), elements: ".item", ...hookParams });
        }
    }
    return List;
}

async function setup() {
    await mountWithCleanup(
        makeDraggableList({
            onDragStart: () => expect.step("start"),
            onDrop: () => expect.step("drop"),
        }),
    );
    const firstRect = queryRect(".item:first-child");
    const secondRect = queryRect(".item:nth-child(2)");
    return {
        first: queryOne(".item:first-child"),
        second: queryOne(".item:nth-child(2)"),
        origin: { x: firstRect.x + 5, y: firstRect.y + 5 },
        secondOrigin: { x: secondRect.x + 5, y: secondRect.y + 5 },
    };
}

test("MAIN: a throttled pointermove leaks into the next drag", async () => {
    const { first, second, origin, secondOrigin } = await setup();

    dispatchPointer(first, "pointerdown", origin);
    dispatchPointer(window, "pointermove", { x: origin.x + 200, y: origin.y + 200 });
    dispatchPointer(window, "pointermove", { x: origin.x + 400, y: origin.y + 400 });
    expect.verifySteps(["start"]);
    dispatchPointer(window, "pointerup", { x: origin.x + 400, y: origin.y + 400 });
    expect.verifySteps(["drop"]);

    dispatchPointer(second, "pointerdown", secondOrigin);
    await animationFrame();

    expect.verifySteps([], {
        message: "no drag may start without a move after press B",
    });
});

test("CONTROL A: one move in drag A parks no trailing call, so press B is inert", async () => {
    const { first, second, origin, secondOrigin } = await setup();

    dispatchPointer(first, "pointerdown", origin);
    dispatchPointer(window, "pointermove", { x: origin.x + 400, y: origin.y + 400 });
    expect.verifySteps(["start"]);
    dispatchPointer(window, "pointerup", { x: origin.x + 400, y: origin.y + 400 });
    expect.verifySteps(["drop"]);

    dispatchPointer(second, "pointerdown", secondOrigin);
    await animationFrame();

    expect.verifySteps([], {
        message: "with nothing parked, press B alone never starts a drag",
    });
});

test("CONTROL B: the parked call alone is harmless without a second press", async () => {
    const { first, origin } = await setup();

    dispatchPointer(first, "pointerdown", origin);
    dispatchPointer(window, "pointermove", { x: origin.x + 200, y: origin.y + 200 });
    dispatchPointer(window, "pointermove", { x: origin.x + 400, y: origin.y + 400 });
    expect.verifySteps(["start"]);
    dispatchPointer(window, "pointerup", { x: origin.x + 400, y: origin.y + 400 });
    expect.verifySteps(["drop"]);

    await animationFrame();

    expect.verifySteps([], {
        message: "ctx.current was reset, so the stale call no-ops",
    });
});

test("CONTROL C: a parked call near press B's origin stays under the tolerance", async () => {
    const { first, second, origin, secondOrigin } = await setup();

    dispatchPointer(first, "pointerdown", origin);
    dispatchPointer(window, "pointermove", { x: origin.x + 400, y: origin.y + 400 });
    dispatchPointer(window, "pointermove", {
        x: secondOrigin.x + 2,
        y: secondOrigin.y + 1,
    });
    expect.verifySteps(["start"]);
    dispatchPointer(window, "pointerup", {
        x: secondOrigin.x + 2,
        y: secondOrigin.y + 1,
    });
    expect.verifySteps(["drop"]);

    dispatchPointer(second, "pointerdown", secondOrigin);
    await animationFrame();

    expect.verifySteps([], {
        message: "stale coords within tolerance of press B cannot start a drag",
    });
});
