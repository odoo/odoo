/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { computePositioning, DEFAULTS, usePosition } from "@web/core/position/position_hook";
import { registerCleanup } from "../helpers/cleanup";
import {
    getFixture,
    mockAnimationFrame,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "../helpers/utils";

const { Component, hooks, mount, tags } = owl;
const { useRef } = hooks;
const { css, xml } = tags;
let container;
let reference;

/**
 * @param {HTMLElement} popper
 * @param {import("@web/core/position/position_hook").Position} [position="bottom"]
 * @returns {boolean}
 */
function isWellPositioned(popper, position = "bottom") {
    /** @type {import("@web/core/position/position_hook").Options} */
    const options = {
        ...DEFAULTS,
        container,
        position,
    };
    const [direction, variant = "middle"] = position.split("-");
    const d = /** @type {import("@web/core/position/position_hook").DirectionsDataKey} */ (
        direction[0]
    );
    const v = /** @type {import("@web/core/position/position_hook").VariantsDataKey} */ (
        variant[0]
    );
    const posSolution = computePositioning(reference, popper, options).get(d, v);
    const hasCorrectClass = popper.classList.contains(posSolution.className);
    const correctLeft = parseFloat(popper.style.left) === posSolution.left;
    const correctTop = parseFloat(popper.style.top) === posSolution.top;
    return hasCorrectClass && correctLeft && correctTop;
}

class TestComp extends Component {
    setup() {
        usePosition(reference, this.constructor.popperOptions);
    }
}
TestComp.style = css`
    #popper {
        background-color: cyan;
        height: 100px;
        width: 100px;
    }
`;
TestComp.template = xml`<div id="popper"/>`;
/** @type {import("@web/core/position/position_hook").Options} */
TestComp.popperOptions = {};

QUnit.module("usePosition Hook", {
    async beforeEach() {
        reference = document.createElement("div");
        reference.id = "reference";
        reference.style.backgroundColor = "yellow";
        reference.style.height = "50px";
        reference.style.width = "50px";

        // Force container style, to make these tests independent of screen size
        container = document.createElement("div");
        container.id = "container";
        container.style.backgroundColor = "pink";
        container.style.height = "450px";
        container.style.width = "450px";
        container.style.display = "flex";
        container.style.alignItems = "center";
        container.style.justifyContent = "center";
        container.appendChild(reference);
        getFixture().prepend(container);
        registerCleanup(() => {
            getFixture().removeChild(container);
        });
        TestComp.popperOptions = { container };

        patchWithCleanup(browser, { setTimeout: (func) => func() });
    },
});

QUnit.test("default position is bottom", async (assert) => {
    const popper = await mount(TestComp, { target: container });
    assert.ok(isWellPositioned(popper.el, "bottom"));
});

QUnit.test("can add margin", async (assert) => {
    let margin = 0;
    Object.assign(TestComp.popperOptions, { margin });
    let popper = await mount(TestComp, { target: container });
    const popBox1 = popper.el.getBoundingClientRect();
    popper.destroy();

    margin = 20;
    Object.assign(TestComp.popperOptions, { margin });
    popper = await mount(TestComp, { target: container });
    const popBox2 = popper.el.getBoundingClientRect();
    popper.destroy();

    assert.strictEqual(popBox1.top + margin, popBox2.top);
});

QUnit.test("can use a t-ref as popper", async (assert) => {
    patchWithCleanup(TestComp, {
        popperOptions: { ...TestComp.popperOptions, popper: "popperRef" },
        template: xml`
            <div id="not-popper">
                <div id="popper" t-ref="popperRef"/>
            </div>
        `,
    });
    const comp = await mount(TestComp, { target: container });
    assert.notOk(isWellPositioned(comp.el));
    assert.ok(isWellPositioned(comp.el.querySelector("#popper")));
});

QUnit.test("has no effect when component is destroyed", async (assert) => {
    const execRegisteredCallbacks = mockAnimationFrame();
    const originalReference = reference;
    reference = () => {
        assert.step("reference called");
        return originalReference;
    };

    const popper = await mount(TestComp, { target: container });
    assert.verifySteps(["reference called"], "reference called when component mounted");

    triggerEvent(document, null, "scroll");
    await nextTick();
    assert.verifySteps([]);
    execRegisteredCallbacks();
    assert.verifySteps(["reference called"], "reference called when document scrolled");

    triggerEvent(document, null, "scroll");
    await nextTick();
    popper.destroy();
    execRegisteredCallbacks();
    assert.verifySteps(
        [],
        "reference not called even if scroll happened right before the component destroys"
    );
});

QUnit.test("popper as child of another", async (assert) => {
    class Child extends Component {
        setup() {
            const ref = useRef("ref");
            usePosition(() => ref.el, { popper: "popper", container, position: "left" });
        }
    }
    Child.template = /* xml */ xml`
        <div id="child">
            <div class="ref" t-ref="ref" />
            <div class="popper" t-ref="popper" />
        </div>
    `;
    Child.style = /* css */ css`
        #child .ref {
            background-color: salmon;
            height: 100px;
            width: 10px;
        }
        #child .popper {
            background-color: olive;
            height: 100px;
            width: 100px;
        }
    `;
    class Parent extends Component {
        setup() {
            usePosition(reference, { container });
        }
    }
    Parent.components = { Child };
    Parent.template = /* xml */ xml`
        <div id="popper">
            <Child/>
        </div>
    `;
    Parent.style = /* css */ css`
        #popper {
            background-color: khaki;
            height: 100px;
            width: 100px;
        }
    `;
    await mount(Parent, { target: container });
    const parentPopBox1 = container.querySelector("#popper").getBoundingClientRect();
    const childPopBox1 = container.querySelector("#child .popper").getBoundingClientRect();

    const spacer = document.createElement("div");
    spacer.id = "foo";
    spacer.style.height = "1px";
    spacer.style.width = "100px";
    container.prepend(spacer);
    await triggerEvent(document, null, "scroll");

    const parentPopBox2 = container.querySelector("#popper").getBoundingClientRect();
    const childPopBox2 = container.querySelector("#child .popper").getBoundingClientRect();

    assert.strictEqual(parentPopBox1.top, parentPopBox2.top);
    assert.strictEqual(childPopBox1.top, childPopBox2.top);
    assert.strictEqual(parentPopBox2.left, parentPopBox1.left + spacer.offsetWidth * 0.5);
    assert.strictEqual(childPopBox2.left, childPopBox1.left + spacer.offsetWidth * 0.5);
});

const getPositionTest = (position, positionToCheck) => {
    return async (assert) => {
        Object.assign(TestComp.popperOptions, { position });
        const popper = await mount(TestComp, { target: container });
        positionToCheck = positionToCheck || position;
        assert.ok(isWellPositioned(popper.el, positionToCheck));
    };
};
QUnit.test("position top", getPositionTest("top"));
QUnit.test("position left", getPositionTest("left"));
QUnit.test("position bottom", getPositionTest("bottom"));
QUnit.test("position right", getPositionTest("right"));
QUnit.test("position top-start", getPositionTest("top-start"));
QUnit.test("position top-middle", getPositionTest("top-middle"));
QUnit.test("position top-end", getPositionTest("top-end"));
QUnit.test("position left-start", getPositionTest("left-start"));
QUnit.test("position left-middle", getPositionTest("left-middle"));
QUnit.test("position left-end", getPositionTest("left-end"));
QUnit.test("position bottom-start", getPositionTest("bottom-start"));
QUnit.test("position bottom-middle", getPositionTest("bottom-middle"));
QUnit.test("position bottom-end", getPositionTest("bottom-end"));
QUnit.test("position right-start", getPositionTest("right-start"));
QUnit.test("position right-middle", getPositionTest("right-middle"));
QUnit.test("position right-end", getPositionTest("right-end"));
QUnit.test("position top === top-middle", getPositionTest("top", "top-middle"));
QUnit.test("position left === left-middle", getPositionTest("left", "left-middle"));
QUnit.test("position bottom === bottom-middle", getPositionTest("bottom", "bottom-middle"));
QUnit.test("position right === right-middle", getPositionTest("right", "right-middle"));

const CONTAINER_STYLE_MAP = {
    top: { alignItems: "flex-start" },
    bottom: { alignItems: "flex-end" },
    left: { justifyContent: "flex-start" },
    right: { justifyContent: "flex-end" },
    slimfit: { height: "100px", width: "100px" }, // height and width of popper
    h125: { height: "125px" }, // height of popper + 1/2 reference
    w125: { width: "125px" }, // width of popper + 1/2 reference
};
const getRepositionTest = (from, to, containerStyleChanges) => {
    return async (assert) => {
        Object.assign(TestComp.popperOptions, { position: from });
        const popper = await mount(TestComp, { target: container });
        assert.ok(isWellPositioned(popper.el, from), `points to ${from} direction`);

        // Change container style and force update
        for (const styleToApply of containerStyleChanges.split(" ")) {
            Object.assign(container.style, CONTAINER_STYLE_MAP[styleToApply]);
        }
        triggerEvent(document, null, "scroll");
        await nextTick();
        assert.ok(isWellPositioned(popper.el, to), `points to ${to} direction`);
    };
};
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from top-start to bottom-start",
    getRepositionTest("top-start", "bottom-start", "top")
);
QUnit.test(
    "reposition from top-start to bottom-middle",
    getRepositionTest("top-start", "bottom-middle", "top w125")
);
QUnit.test(
    "reposition from top-start to bottom-end",
    getRepositionTest("top-start", "bottom-end", "top right")
);
QUnit.test(
    "reposition from top-start to right-start",
    getRepositionTest("top-start", "right-start", "h125 top")
);
QUnit.test(
    "reposition from top-start to right-middle",
    getRepositionTest("top-start", "right-middle", "h125")
);
QUnit.test(
    "reposition from top-start to right-end",
    getRepositionTest("top-start", "right-end", "h125 bottom")
);
QUnit.test(
    "reposition from top-start to left-start",
    getRepositionTest("top-start", "left-start", "h125 right top")
);
QUnit.test(
    "reposition from top-start to left-middle",
    getRepositionTest("top-start", "left-middle", "h125 right")
);
QUnit.test(
    "reposition from top-start to left-end",
    getRepositionTest("top-start", "left-end", "h125 right bottom")
);
QUnit.test(
    "reposition from top-start to top-start",
    getRepositionTest("top-start", "top-start", "slimfit")
);
QUnit.test(
    "reposition from top-start to top-middle",
    getRepositionTest("top-start", "top-middle", "w125")
);
QUnit.test(
    "reposition from top-start to top-end",
    getRepositionTest("top-start", "top-end", "right")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from top-middle to bottom-start",
    getRepositionTest("top-middle", "bottom-start", "top left")
);
QUnit.test(
    "reposition from top-middle to bottom-middle",
    getRepositionTest("top-middle", "bottom-middle", "top")
);
QUnit.test(
    "reposition from top-middle to bottom-end",
    getRepositionTest("top-middle", "bottom-end", "top right")
);
QUnit.test(
    "reposition from top-middle to right-start",
    getRepositionTest("top-middle", "right-start", "h125 top")
);
QUnit.test(
    "reposition from top-middle to right-middle",
    getRepositionTest("top-middle", "right-middle", "h125")
);
QUnit.test(
    "reposition from top-middle to right-end",
    getRepositionTest("top-middle", "right-end", "h125 bottom")
);
QUnit.test(
    "reposition from top-middle to left-start",
    getRepositionTest("top-middle", "left-start", "h125 right top")
);
QUnit.test(
    "reposition from top-middle to left-middle",
    getRepositionTest("top-middle", "left-middle", "h125 right")
);
QUnit.test(
    "reposition from top-middle to left-end",
    getRepositionTest("top-middle", "left-end", "h125 right bottom")
);
QUnit.test(
    "reposition from top-middle to top-start",
    getRepositionTest("top-middle", "top-start", "left")
);
QUnit.test(
    "reposition from top-middle to top-middle",
    getRepositionTest("top-middle", "top-middle", "slimfit")
);
QUnit.test(
    "reposition from top-middle to top-end",
    getRepositionTest("top-middle", "top-end", "right")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from top-end to bottom-start",
    getRepositionTest("top-end", "bottom-start", "top left")
);
QUnit.test(
    "reposition from top-end to bottom-middle",
    getRepositionTest("top-end", "bottom-middle", "top w125")
);
QUnit.test(
    "reposition from top-end to bottom-end",
    getRepositionTest("top-end", "bottom-end", "top")
);
QUnit.test(
    "reposition from top-end to right-start",
    getRepositionTest("top-end", "right-start", "h125 top")
);
QUnit.test(
    "reposition from top-end to right-middle",
    getRepositionTest("top-end", "right-middle", "h125")
);
QUnit.test(
    "reposition from top-end to right-end",
    getRepositionTest("top-end", "right-end", "h125 bottom")
);
QUnit.test(
    "reposition from top-end to left-start",
    getRepositionTest("top-end", "left-start", "h125 right top")
);
QUnit.test(
    "reposition from top-end to left-middle",
    getRepositionTest("top-end", "left-middle", "h125 right")
);
QUnit.test(
    "reposition from top-end to left-end",
    getRepositionTest("top-end", "left-end", "h125 right bottom")
);
QUnit.test(
    "reposition from top-end to top-start",
    getRepositionTest("top-end", "top-start", "left")
);
QUnit.test(
    "reposition from top-end to top-middle",
    getRepositionTest("top-end", "top-middle", "w125")
);
QUnit.test(
    "reposition from top-end to top-end",
    getRepositionTest("top-end", "top-end", "slimfit")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from left-start to bottom-start",
    getRepositionTest("left-start", "bottom-start", "w125 left")
);
QUnit.test(
    "reposition from left-start to bottom-middle",
    getRepositionTest("left-start", "bottom-middle", "w125")
);
QUnit.test(
    "reposition from left-start to bottom-end",
    getRepositionTest("left-start", "bottom-end", "w125 right")
);
QUnit.test(
    "reposition from left-start to right-start",
    getRepositionTest("left-start", "right-start", "left")
);
QUnit.test(
    "reposition from left-start to right-middle",
    getRepositionTest("left-start", "right-middle", "left h125")
);
QUnit.test(
    "reposition from left-start to right-end",
    getRepositionTest("left-start", "right-end", "left bottom")
);
QUnit.test(
    "reposition from left-start to left-start",
    getRepositionTest("left-start", "left-start", "slimfit")
);
QUnit.test(
    "reposition from left-start to left-middle",
    getRepositionTest("left-start", "left-middle", "h125")
);
QUnit.test(
    "reposition from left-start to left-end",
    getRepositionTest("left-start", "left-end", "bottom")
);
QUnit.test(
    "reposition from left-start to top-start",
    getRepositionTest("left-start", "top-start", "w125 bottom left")
);
QUnit.test(
    "reposition from left-start to top-middle",
    getRepositionTest("left-start", "top-middle", "w125 bottom")
);
QUnit.test(
    "reposition from left-start to top-end",
    getRepositionTest("left-start", "top-end", "w125 bottom right")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from left-middle to bottom-start",
    getRepositionTest("left-middle", "bottom-start", "w125 left")
);
QUnit.test(
    "reposition from left-middle to bottom-middle",
    getRepositionTest("left-middle", "bottom-middle", "w125")
);
QUnit.test(
    "reposition from left-middle to bottom-end",
    getRepositionTest("left-middle", "bottom-end", "w125 right")
);
QUnit.test(
    "reposition from left-middle to right-start",
    getRepositionTest("left-middle", "right-start", "left top")
);
QUnit.test(
    "reposition from left-middle to right-middle",
    getRepositionTest("left-middle", "right-middle", "left")
);
QUnit.test(
    "reposition from left-middle to right-end",
    getRepositionTest("left-middle", "right-end", "left bottom")
);
QUnit.test(
    "reposition from left-middle to top-start",
    getRepositionTest("left-middle", "top-start", "w125 bottom left")
);
QUnit.test(
    "reposition from left-middle to top-middle",
    getRepositionTest("left-middle", "top-middle", "w125 bottom")
);
QUnit.test(
    "reposition from left-middle to top-end",
    getRepositionTest("left-middle", "top-end", "w125 bottom right")
);
QUnit.test(
    "reposition from left-middle to left-start",
    getRepositionTest("left-middle", "left-start", "top")
);
QUnit.test(
    "reposition from left-middle to left-middle",
    getRepositionTest("left-middle", "left-middle", "slimfit")
);
QUnit.test(
    "reposition from left-middle to left-end",
    getRepositionTest("left-middle", "left-end", "bottom")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from left-end to bottom-start",
    getRepositionTest("left-end", "bottom-start", "w125 left")
);
QUnit.test(
    "reposition from left-end to bottom-middle",
    getRepositionTest("left-end", "bottom-middle", "w125")
);
QUnit.test(
    "reposition from left-end to bottom-end",
    getRepositionTest("left-end", "bottom-end", "w125 right")
);
QUnit.test(
    "reposition from left-end to right-start",
    getRepositionTest("left-end", "right-start", "left top")
);
QUnit.test(
    "reposition from left-end to right-middle",
    getRepositionTest("left-end", "right-middle", "left h125")
);
QUnit.test(
    "reposition from left-end to right-end",
    getRepositionTest("left-end", "right-end", "left")
);
QUnit.test(
    "reposition from left-end to top-start",
    getRepositionTest("left-end", "top-start", "w125 bottom left")
);
QUnit.test(
    "reposition from left-end to top-middle",
    getRepositionTest("left-end", "top-middle", "w125 bottom")
);
QUnit.test(
    "reposition from left-end to top-end",
    getRepositionTest("left-end", "top-end", "w125 bottom right")
);
QUnit.test(
    "reposition from left-end to left-start",
    getRepositionTest("left-end", "left-start", "top")
);
QUnit.test(
    "reposition from left-end to left-middle",
    getRepositionTest("left-end", "left-middle", "h125")
);
QUnit.test(
    "reposition from left-end to left-end",
    getRepositionTest("left-end", "left-end", "slimfit")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from bottom-start to bottom-start",
    getRepositionTest("bottom-start", "bottom-start", "slimfit")
);
QUnit.test(
    "reposition from bottom-start to bottom-middle",
    getRepositionTest("bottom-start", "bottom-middle", "w125")
);
QUnit.test(
    "reposition from bottom-start to bottom-end",
    getRepositionTest("bottom-start", "bottom-end", "right")
);
QUnit.test(
    "reposition from bottom-start to right-start",
    getRepositionTest("bottom-start", "right-start", "h125 top")
);
QUnit.test(
    "reposition from bottom-start to right-middle",
    getRepositionTest("bottom-start", "right-middle", "h125")
);
QUnit.test(
    "reposition from bottom-start to right-end",
    getRepositionTest("bottom-start", "right-end", "h125 bottom")
);
QUnit.test(
    "reposition from bottom-start to top-start",
    getRepositionTest("bottom-start", "top-start", "bottom")
);
QUnit.test(
    "reposition from bottom-start to top-middle",
    getRepositionTest("bottom-start", "top-middle", "bottom w125")
);
QUnit.test(
    "reposition from bottom-start to top-end",
    getRepositionTest("bottom-start", "top-end", "bottom right")
);
QUnit.test(
    "reposition from bottom-start to left-start",
    getRepositionTest("bottom-start", "left-start", "h125 right top")
);
QUnit.test(
    "reposition from bottom-start to left-middle",
    getRepositionTest("bottom-start", "left-middle", "h125 right")
);
QUnit.test(
    "reposition from bottom-start to left-end",
    getRepositionTest("bottom-start", "left-end", "h125 right bottom")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from bottom-middle to bottom-start",
    getRepositionTest("bottom-middle", "bottom-start", "left")
);
QUnit.test(
    "reposition from bottom-middle to bottom-middle",
    getRepositionTest("bottom-middle", "bottom-middle", "slimfit")
);
QUnit.test(
    "reposition from bottom-middle to bottom-end",
    getRepositionTest("bottom-middle", "bottom-end", "right")
);
QUnit.test(
    "reposition from bottom-middle to right-start",
    getRepositionTest("bottom-middle", "right-start", "h125 top")
);
QUnit.test(
    "reposition from bottom-middle to right-middle",
    getRepositionTest("bottom-middle", "right-middle", "h125")
);
QUnit.test(
    "reposition from bottom-middle to right-end",
    getRepositionTest("bottom-middle", "right-end", "h125 bottom")
);
QUnit.test(
    "reposition from bottom-middle to top-start",
    getRepositionTest("bottom-middle", "top-start", "bottom left")
);
QUnit.test(
    "reposition from bottom-middle to top-middle",
    getRepositionTest("bottom-middle", "top-middle", "bottom")
);
QUnit.test(
    "reposition from bottom-middle to top-end",
    getRepositionTest("bottom-middle", "top-end", "bottom right")
);
QUnit.test(
    "reposition from bottom-middle to left-start",
    getRepositionTest("bottom-middle", "left-start", "h125 right top")
);
QUnit.test(
    "reposition from bottom-middle to left-middle",
    getRepositionTest("bottom-middle", "left-middle", "h125 right")
);
QUnit.test(
    "reposition from bottom-middle to left-end",
    getRepositionTest("bottom-middle", "left-end", "h125 right bottom")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from bottom-end to bottom-start",
    getRepositionTest("bottom-end", "bottom-start", "left")
);
QUnit.test(
    "reposition from bottom-end to bottom-middle",
    getRepositionTest("bottom-end", "bottom-middle", "w125")
);
QUnit.test(
    "reposition from bottom-end to bottom-end",
    getRepositionTest("bottom-end", "bottom-end", "slimfit")
);
QUnit.test(
    "reposition from bottom-end to right-start",
    getRepositionTest("bottom-end", "right-start", "h125 top")
);
QUnit.test(
    "reposition from bottom-end to right-middle",
    getRepositionTest("bottom-end", "right-middle", "h125")
);
QUnit.test(
    "reposition from bottom-end to right-end",
    getRepositionTest("bottom-end", "right-end", "h125 bottom")
);
QUnit.test(
    "reposition from bottom-end to top-start",
    getRepositionTest("bottom-end", "top-start", "bottom left")
);
QUnit.test(
    "reposition from bottom-end to top-middle",
    getRepositionTest("bottom-end", "top-middle", "bottom w125")
);
QUnit.test(
    "reposition from bottom-end to top-end",
    getRepositionTest("bottom-end", "top-end", "bottom")
);
QUnit.test(
    "reposition from bottom-end to left-start",
    getRepositionTest("bottom-end", "left-start", "h125 right top")
);
QUnit.test(
    "reposition from bottom-end to left-middle",
    getRepositionTest("bottom-end", "left-middle", "h125 right")
);
QUnit.test(
    "reposition from bottom-end to left-end",
    getRepositionTest("bottom-end", "left-end", "h125 right bottom")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from right-start to bottom-start",
    getRepositionTest("right-start", "bottom-start", "w125 top left")
);
QUnit.test(
    "reposition from right-start to bottom-middle",
    getRepositionTest("right-start", "bottom-middle", "w125 top")
);
QUnit.test(
    "reposition from right-start to bottom-end",
    getRepositionTest("right-start", "bottom-end", "w125 top right")
);
QUnit.test(
    "reposition from right-start to right-start",
    getRepositionTest("right-start", "right-start", "slimfit")
);
QUnit.test(
    "reposition from right-start to right-middle",
    getRepositionTest("right-start", "right-middle", "h125")
);
QUnit.test(
    "reposition from right-start to right-end",
    getRepositionTest("right-start", "right-end", "bottom")
);
QUnit.test(
    "reposition from right-start to top-start",
    getRepositionTest("right-start", "top-start", "w125 left")
);
QUnit.test(
    "reposition from right-start to top-middle",
    getRepositionTest("right-start", "top-middle", "w125")
);
QUnit.test(
    "reposition from right-start to top-end",
    getRepositionTest("right-start", "top-end", "w125 right")
);
QUnit.test(
    "reposition from right-start to left-start",
    getRepositionTest("right-start", "left-start", "right")
);
QUnit.test(
    "reposition from right-start to left-middle",
    getRepositionTest("right-start", "left-middle", "right h125")
);
QUnit.test(
    "reposition from right-start to left-end",
    getRepositionTest("right-start", "left-end", "right bottom")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from right-middle to bottom-start",
    getRepositionTest("right-middle", "bottom-start", "w125 top left")
);
QUnit.test(
    "reposition from right-middle to bottom-middle",
    getRepositionTest("right-middle", "bottom-middle", "w125 top")
);
QUnit.test(
    "reposition from right-middle to bottom-end",
    getRepositionTest("right-middle", "bottom-end", "w125 top right")
);
QUnit.test(
    "reposition from right-middle to right-start",
    getRepositionTest("right-middle", "right-start", "top")
);
QUnit.test(
    "reposition from right-middle to right-middle",
    getRepositionTest("right-middle", "right-middle", "slimfit")
);
QUnit.test(
    "reposition from right-middle to right-end",
    getRepositionTest("right-middle", "right-end", "bottom")
);
QUnit.test(
    "reposition from right-middle to left-start",
    getRepositionTest("right-middle", "left-start", "right top")
);
QUnit.test(
    "reposition from right-middle to left-middle",
    getRepositionTest("right-middle", "left-middle", "right")
);
QUnit.test(
    "reposition from right-middle to left-end",
    getRepositionTest("right-middle", "left-end", "right bottom")
);
QUnit.test(
    "reposition from right-middle to top-start",
    getRepositionTest("right-middle", "top-start", "w125 left")
);
QUnit.test(
    "reposition from right-middle to top-middle",
    getRepositionTest("right-middle", "top-middle", "w125")
);
QUnit.test(
    "reposition from right-middle to top-end",
    getRepositionTest("right-middle", "top-end", "w125 right")
);
// -----------------------------------------------------------------------------
QUnit.test(
    "reposition from right-end to bottom-start",
    getRepositionTest("right-end", "bottom-start", "w125 top left")
);
QUnit.test(
    "reposition from right-end to bottom-middle",
    getRepositionTest("right-end", "bottom-middle", "w125 top")
);
QUnit.test(
    "reposition from right-end to bottom-end",
    getRepositionTest("right-end", "bottom-end", "w125 top right")
);
QUnit.test(
    "reposition from right-end to right-start",
    getRepositionTest("right-end", "right-start", "top")
);
QUnit.test(
    "reposition from right-end to right-middle",
    getRepositionTest("right-end", "right-middle", "h125")
);
QUnit.test(
    "reposition from right-end to right-end",
    getRepositionTest("right-end", "right-end", "slimfit")
);
QUnit.test(
    "reposition from right-end to left-start",
    getRepositionTest("right-end", "left-start", "right top")
);
QUnit.test(
    "reposition from right-end to left-middle",
    getRepositionTest("right-end", "left-middle", "right h125")
);
QUnit.test(
    "reposition from right-end to left-end",
    getRepositionTest("right-end", "left-end", "right")
);
QUnit.test(
    "reposition from right-end to top-start",
    getRepositionTest("right-end", "top-start", "w125 left")
);
QUnit.test(
    "reposition from right-end to top-middle",
    getRepositionTest("right-end", "top-middle", "w125")
);
QUnit.test(
    "reposition from right-end to top-end",
    getRepositionTest("right-end", "top-end", "w125 right")
);
