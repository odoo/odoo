/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { usePosition } from "@web/core/position_hook";
import { registerCleanup } from "../helpers/cleanup";
import {
    destroy,
    getFixture,
    makeDeferred,
    mockAnimationFrame,
    mount,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "../helpers/utils";
import { localization } from "@web/core/l10n/localization";
import { Component, useRef, xml } from "@odoo/owl";

const FLEXBOX_STYLE = {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
};
const CONTAINER_STYLE = {
    ...FLEXBOX_STYLE,
    backgroundColor: "salmon",
    height: "450px",
    width: "450px",
    margin: "25px",
};
const TARGET_STYLE = {
    backgroundColor: "tomato",
    height: "50px",
    width: "50px",
};
let container;

/**
 * @param {import("@web/core/position_hook").Options} popperOptions
 * @returns {Component}
 */
function getTestComponent(popperOptions = {}, target = document.createElement("div")) {
    popperOptions.container = popperOptions.container || container;

    target.id = "target";
    Object.assign(target.style, TARGET_STYLE);
    if (!target.isConnected) {
        // If the target is not in any DOM, we append it to the container by default
        popperOptions.container.appendChild(target);
    }

    class TestComp extends Component {
        setup() {
            usePosition("popper", () => target, popperOptions);
        }
    }
    TestComp.template = xml`<div id="popper" t-ref="popper" />`;
    return TestComp;
}

QUnit.module("usePosition Hook", {
    async beforeEach() {
        // Force container style, to make these tests independent of screen size
        container = document.createElement("div");
        container.id = "container";
        Object.assign(container.style, CONTAINER_STYLE);
        getFixture().prepend(container);
        registerCleanup(() => {
            getFixture().removeChild(container);
        });

        const sheet = document.createElement("style");
        sheet.textContent = `
            #popper {
                background-color: plum;
                height: 100px;
                width: 100px;
            }
        `;
        document.head.appendChild(sheet);
        registerCleanup(() => {
            sheet.remove();
        });
        patchWithCleanup(browser, { setTimeout: (func) => func() });
    },
});

QUnit.test("default position is bottom-middle", async (assert) => {
    assert.expect(1);
    const TestComp = getTestComponent({
        onPositioned: (el, { direction, variant }) => {
            assert.equal(`${direction}-${variant}`, "bottom-middle");
        },
    });
    await mount(TestComp, container);
});

QUnit.test("can add margin", async (assert) => {
    // Add a sheet to set a margin on the popper
    const SHEET_MARGINS = {
        top: 11,
        right: 12,
        bottom: 13,
        left: 14,
    };
    const sheet = document.createElement("style");
    sheet.textContent = `
        #popper {
            margin-top: ${SHEET_MARGINS.top}px;
            margin-right: ${SHEET_MARGINS.right}px;
            margin-bottom: ${SHEET_MARGINS.bottom}px;
            margin-left: ${SHEET_MARGINS.left}px;
        }
    `;
    document.head.appendChild(sheet);
    registerCleanup(() => sheet.remove());

    // Local helper
    async function _mountTestComponentAndDestroy(popperOptions) {
        const TestComp = getTestComponent(popperOptions);
        const popper = await mount(TestComp, container);
        const popBox = document.getElementById("popper").getBoundingClientRect();
        const targetBox = document.getElementById("target").getBoundingClientRect();
        destroy(popper);
        container.removeChild(document.getElementById("target"));
        return [popBox, targetBox];
    }

    // With/without additional margin (default direction is bottom)
    let [popBox, targetBox] = await _mountTestComponentAndDestroy();
    assert.strictEqual(popBox.top, targetBox.bottom + SHEET_MARGINS.top);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ margin: 10 });
    assert.strictEqual(popBox.top, targetBox.bottom + SHEET_MARGINS.top + 10);

    // With/without additional margin, direction is top
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "top" });
    assert.strictEqual(popBox.top, targetBox.top - popBox.height - SHEET_MARGINS.bottom);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "top", margin: 10 });
    assert.strictEqual(popBox.top, targetBox.top - popBox.height - SHEET_MARGINS.bottom - 10);

    // With/without additional margin, direction is left
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "left" });
    assert.strictEqual(popBox.left, targetBox.left - popBox.width - SHEET_MARGINS.right);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "left", margin: 10 });
    assert.strictEqual(popBox.left, targetBox.left - popBox.width - SHEET_MARGINS.right - 10);

    // With/without additional margin, direction is right
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "right" });
    assert.strictEqual(popBox.left, targetBox.right + SHEET_MARGINS.left);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "right", margin: 10 });
    assert.strictEqual(popBox.left, targetBox.right + SHEET_MARGINS.left + 10);
});

QUnit.test("is restricted to its container, even with margins", async (assert) => {
    // Add a sheet to set a margin on the popper
    const SHEET_MARGIN = 11;
    const sheet = document.createElement("style");
    sheet.textContent = `#popper { margin: ${SHEET_MARGIN}px; }`;
    document.head.appendChild(sheet);
    registerCleanup(() => sheet.remove());

    // Local helper
    async function _mountTestComponentAndDestroy(popperOptions) {
        const TestComp = getTestComponent({
            ...popperOptions,
            onPositioned: (el, { direction, variant }) => {
                assert.step(`${direction}-${variant}`);
            },
        });
        const popper = await mount(TestComp, container);
        destroy(popper);
        container.removeChild(document.getElementById("target"));
    }

    const minSize = 150; // => popper is 100px, target is 50px
    const margin = 10; // will serve as additional margin

    // === DIRECTION: BOTTOM ===
    // Container style changes: push target to top
    Object.assign(container.style, { alignItems: "flex-start" });

    // --> Without additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { height: `${minSize + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "bottom" });
    assert.verifySteps(["bottom-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, { height: `${minSize + SHEET_MARGIN - 1}px` });
    await _mountTestComponentAndDestroy({ position: "bottom" });
    assert.verifySteps(["right-start"]);

    // --> With additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { height: `${minSize + margin + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "bottom", margin });
    assert.verifySteps(["bottom-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, { height: `${minSize + margin + SHEET_MARGIN - 1}px` });
    await _mountTestComponentAndDestroy({ position: "bottom", margin });
    assert.verifySteps(["right-start"]);

    // === DIRECTION: TOP ===
    // Container style changes: push target to bottom
    Object.assign(container.style, { alignItems: "flex-end" });

    // --> Without additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { height: `${minSize + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "top" });
    assert.verifySteps(["top-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, { height: `${minSize + SHEET_MARGIN - 1}px` });
    await _mountTestComponentAndDestroy({ position: "top" });
    assert.verifySteps(["right-end"]);

    // --> With additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { height: `${minSize + margin + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "top", margin });
    assert.verifySteps(["top-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, {
        height: `${minSize + margin + SHEET_MARGIN - 1}px`,
    });
    await _mountTestComponentAndDestroy({ position: "top", margin });
    assert.verifySteps(["right-end"]);

    // === DIRECTION: LEFT ===
    // Container style changes: reset previous changes
    Object.assign(container.style, { alignItems: "center", height: "450px" });
    // Container style changes: push target to right
    Object.assign(container.style, { justifyContent: "flex-end" });

    // --> Without additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { width: `${minSize + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "left" });
    assert.verifySteps(["left-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, { width: `${minSize + SHEET_MARGIN - 1}px` });
    await _mountTestComponentAndDestroy({ position: "left" });
    assert.verifySteps(["bottom-end"]);

    // --> With additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { width: `${minSize + margin + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "left", margin });
    assert.verifySteps(["left-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, {
        width: `${minSize + margin + SHEET_MARGIN - 1}px`,
    });
    await _mountTestComponentAndDestroy({ position: "left", margin });
    assert.verifySteps(["bottom-end"]);

    // === DIRECTION: RIGHT ===
    // Container style changes: push target to left
    Object.assign(container.style, { justifyContent: "flex-start" });

    // --> Without additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { width: `${minSize + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "right" });
    assert.verifySteps(["right-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, { width: `${minSize + SHEET_MARGIN - 1}px` });
    await _mountTestComponentAndDestroy({ position: "right" });
    assert.verifySteps(["top-start"]);

    // --> With additional margin
    // Leave just enough space for the popper to be contained
    Object.assign(container.style, { width: `${minSize + margin + SHEET_MARGIN}px` });
    await _mountTestComponentAndDestroy({ position: "right", margin });
    assert.verifySteps(["right-middle"]);
    // Remove 1px => popper should switch direction as it can't be contained
    Object.assign(container.style, { width: `${minSize + margin + SHEET_MARGIN - 1}px` });
    await _mountTestComponentAndDestroy({ position: "right", margin });
    assert.verifySteps(["top-start"]);
});

QUnit.test("popper is an inner element", async (assert) => {
    assert.expect(2);
    const TestComp = getTestComponent({
        onPositioned: (el) => {
            assert.notOk(document.getElementById("not-popper") === el);
            assert.ok(document.getElementById("popper") === el);
        },
    });
    TestComp.template = xml`
        <div id="not-popper">
            <div id="popper" t-ref="popper"/>
        </div>
    `;
    await mount(TestComp, container);
});

QUnit.test("has no effect when component is destroyed", async (assert) => {
    mockAnimationFrame();
    const TestComp = getTestComponent({
        onPositioned: () => {
            assert.step("onPositioned called");
        },
    });
    const comp = await mount(TestComp, container);
    assert.verifySteps(["onPositioned called"], "onPositioned called when component mounted");

    await triggerEvent(document, null, "scroll");
    assert.verifySteps(["onPositioned called"], "onPositioned called when document scrolled");

    triggerEvent(document, null, "scroll");
    destroy(comp);
    await nextTick();
    assert.verifySteps(
        [],
        "onPositioned not called even if scroll happened right before the component destroys"
    );
});

QUnit.test("reposition popper when a load event occurs", async (assert) => {
    const TestComp = getTestComponent({
        onPositioned: () => {
            assert.step("onPositioned called");
        },
    });
    await mount(TestComp, container);
    assert.verifySteps(["onPositioned called"], "onPositioned called when component mounted");
    await document.querySelector('[id="popper"]').dispatchEvent(new Event("load"));
    assert.verifySteps(["onPositioned called"], "onPositioned called when load event is triggered");
});

QUnit.test("reposition popper when a scroll event occurs", async (assert) => {
    const TestComp = getTestComponent({
        onPositioned: () => {
            assert.step("onPositioned called");
        },
    });
    await mount(TestComp, container);
    assert.verifySteps(["onPositioned called"]);
    await document.querySelector("#popper").dispatchEvent(new Event("scroll"));
    assert.verifySteps([], "onPositioned not called when scroll event is triggered inside popper");
    await document.querySelector("#popper").parentElement.dispatchEvent(new Event("scroll"));
    assert.verifySteps(["onPositioned called"]);
});

QUnit.test("is positioned relative to its containing block", async (assert) => {
    const fixtureBox = getFixture().getBoundingClientRect();
    // offset the container
    const margin = 15;
    container.style.margin = `${margin}px`;
    let pos1, pos2;
    let TestComp = getTestComponent({
        onPositioned: (el, pos) => {
            pos1 = pos;
        },
    });
    let popper = await mount(TestComp, container);

    const popBox1 = document.getElementById("popper").getBoundingClientRect();
    destroy(popper);
    document.getElementById("target").remove();

    // make container the containing block instead of the viewport
    container.style.contain = "layout";

    TestComp = getTestComponent({
        onPositioned: (el, pos) => {
            pos2 = pos;
        },
    });
    popper = await mount(TestComp, container);
    const popBox2 = document.getElementById("popper").getBoundingClientRect();
    destroy(popper);

    // best positions are not the same relative to their containing block
    assert.equal(pos1.top, pos2.top + margin + fixtureBox.top);
    assert.equal(pos1.left, pos2.left + margin + fixtureBox.left);
    // best positions are the same relative to the viewport
    assert.equal(popBox1.top, popBox2.top);
    assert.equal(popBox1.left, popBox2.left);
});

QUnit.test("iframe: popper is outside, target inside", async (assert) => {
    // Prepare target inside iframe
    const IFRAME_STYLE = {
        margin: "25px",
        height: "200px",
        width: "400px",
    };
    const iframe = document.createElement("iframe");
    Object.assign(iframe.style, IFRAME_STYLE);
    iframe.srcdoc = `<div id="target" />`;
    const def = makeDeferred();
    iframe.onload = def.resolve;
    container.appendChild(iframe);
    await def;
    const iframeBody = iframe.contentDocument.body;
    Object.assign(iframeBody.style, {
        ...FLEXBOX_STYLE,
        backgroundColor: "papayawhip",
        height: "300px",
        width: "400px",
        overflowX: "hidden",
    });

    // Prepare popper outside iframe
    const popperTarget = iframe.contentDocument.getElementById("target");
    let onPositionedArgs;
    const Popper = getTestComponent(
        {
            onPositioned: (el, solution) => {
                onPositionedArgs = { el, solution };
                assert.step(`${solution.direction}-${solution.variant}`);
            },
        },
        popperTarget
    );
    await mount(Popper, container);
    assert.verifySteps(["bottom-middle"]);

    // Check everything is rendered where it should be
    assert.containsOnce(container, "#popper");
    assert.containsNone(container, "#target");

    assert.strictEqual(iframeBody.querySelectorAll("#target").length, 1);
    assert.strictEqual(iframeBody.querySelectorAll("#popper").length, 0);

    // Check the expected position
    const { top: iframeTop, left: iframeLeft } = iframe.getBoundingClientRect();
    let targetBox = popperTarget.getBoundingClientRect();
    let popperBox = onPositionedArgs.el.getBoundingClientRect();
    let expectedTop = iframeTop + targetBox.top + popperTarget.offsetHeight;
    let expectedLeft =
        iframeLeft + targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    assert.strictEqual(popperBox.top, expectedTop);
    assert.strictEqual(popperBox.top, onPositionedArgs.solution.top);

    assert.strictEqual(popperBox.left, expectedLeft);
    assert.strictEqual(popperBox.left, onPositionedArgs.solution.left);

    // Scrolling inside the iframe should reposition the popover accordingly
    const previousPositionSolution = onPositionedArgs.solution;
    const scrollOffset = 100;
    const scrollable = iframe.contentDocument.documentElement;
    scrollable.scrollTop = scrollOffset;
    await nextTick();
    assert.verifySteps(["bottom-middle"]);
    assert.strictEqual(previousPositionSolution.top, onPositionedArgs.solution.top + scrollOffset);

    // Check the expected position
    targetBox = popperTarget.getBoundingClientRect();
    popperBox = onPositionedArgs.el.getBoundingClientRect();
    expectedTop = iframeTop + targetBox.top + popperTarget.offsetHeight;
    expectedLeft = iframeLeft + targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    assert.strictEqual(popperBox.top, expectedTop);
    assert.strictEqual(popperBox.top, onPositionedArgs.solution.top);

    assert.strictEqual(popperBox.left, expectedLeft);
    assert.strictEqual(popperBox.left, onPositionedArgs.solution.left);
});

QUnit.test("iframe: both popper and target inside", async (assert) => {
    // Prepare target inside iframe
    const IFRAME_STYLE = {
        height: "300px",
        width: "400px",
    };
    const iframe = document.createElement("iframe");
    Object.assign(iframe.style, IFRAME_STYLE);
    iframe.srcdoc = `<div id="inner-container" />`;
    let def = makeDeferred();
    iframe.onload = def.resolve;
    container.appendChild(iframe);
    await def; // wait for the iframe to be loaded
    const iframeBody = iframe.contentDocument.body;
    Object.assign(iframeBody.style, {
        ...FLEXBOX_STYLE,
        backgroundColor: "papayawhip",
        margin: "25px",
        overflowX: "hidden",
    });

    def = makeDeferred();
    const iframeSheet = iframe.contentDocument.createElement("style");
    iframeSheet.onload = def.resolve;
    iframeSheet.textContent = `
            #popper {
                background-color: plum;
                height: 100px;
                width: 100px;
            }
        `;
    iframe.contentDocument.head.appendChild(iframeSheet);
    await def; // wait for the iframe's stylesheet to be loaded

    const innerContainer = iframe.contentDocument.getElementById("inner-container");
    Object.assign(innerContainer.style, {
        ...CONTAINER_STYLE,
        backgroundColor: "khaki",
    });

    // Prepare popper inside iframe
    let onPositionedArgs;
    const Popper = getTestComponent({
        container: innerContainer,
        onPositioned: (el, solution) => {
            onPositionedArgs = { el, solution };
            assert.step(`${solution.direction}-${solution.variant}`);
        },
    });
    await mount(Popper, innerContainer);
    assert.verifySteps(["bottom-middle"]);

    // Check everything is rendered where it should be
    assert.strictEqual(innerContainer.ownerDocument, iframe.contentDocument);
    assert.strictEqual(innerContainer.querySelectorAll("#target").length, 1);
    assert.strictEqual(innerContainer.querySelectorAll("#popper").length, 1);
    assert.strictEqual(iframeBody.querySelectorAll("#target").length, 1);
    assert.strictEqual(iframeBody.querySelectorAll("#popper").length, 1);

    // Check the expected position
    const popperTarget = innerContainer.querySelector("#target");
    // const { top: iframeTop, left: iframeLeft } = iframe.getBoundingClientRect();
    let targetBox = popperTarget.getBoundingClientRect();
    let popperBox = onPositionedArgs.el.getBoundingClientRect();
    let expectedTop = targetBox.top + popperTarget.offsetHeight;
    let expectedLeft = targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    assert.strictEqual(popperBox.top, expectedTop);
    assert.strictEqual(popperBox.top, onPositionedArgs.solution.top);

    assert.strictEqual(popperBox.left, expectedLeft);
    assert.strictEqual(popperBox.left, onPositionedArgs.solution.left);

    // Scrolling inside the iframe should reposition the popover accordingly
    const previousPositionSolution = onPositionedArgs.solution;
    const scrollOffset = 100;
    const scrollable = iframe.contentDocument.documentElement;
    scrollable.scrollTop = scrollOffset;
    await nextTick();
    assert.verifySteps(["bottom-middle"]);
    assert.strictEqual(previousPositionSolution.top, onPositionedArgs.solution.top + scrollOffset);

    // Check the expected position
    targetBox = popperTarget.getBoundingClientRect();
    popperBox = onPositionedArgs.el.getBoundingClientRect();
    expectedTop = targetBox.top + popperTarget.offsetHeight;
    expectedLeft = targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    assert.strictEqual(popperBox.top, expectedTop);
    assert.strictEqual(popperBox.top, onPositionedArgs.solution.top);

    assert.strictEqual(popperBox.left, expectedLeft);
    assert.strictEqual(popperBox.left, onPositionedArgs.solution.left);
});

QUnit.test("popper as child of another", async (assert) => {
    class Child extends Component {
        static template = /* xml */ xml`
            <div id="child">
                <div class="target" t-ref="ref" />
                <div class="popper" t-ref="popper" />
            </div>
        `;
        setup() {
            const ref = useRef("ref");
            usePosition("popper", () => ref.el, { position: "left" });
        }
    }
    const target = document.createElement("div");
    target.id = "target";
    Object.assign(target.style, TARGET_STYLE);
    container.appendChild(target);
    class Parent extends Component {
        static components = { Child };
        static template = /* xml */ xml`<div id="popper" t-ref="popper"><Child/></div>`;
        setup() {
            usePosition("popper", () => target);
        }
    }

    const sheet = document.createElement("style");
    sheet.textContent = `
        #child .target {
            background-color: peachpuff;
            height: 100px;
            width: 10px;
        }
        #child .popper {
            background-color: olive;
            height: 100px;
            width: 100px;
        }
    `;
    document.head.appendChild(sheet);
    registerCleanup(() => sheet.remove());

    await mount(Parent, container);
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

function getPositionTest(position, positionToCheck) {
    return async (assert) => {
        assert.expect(2);
        positionToCheck = positionToCheck || position;
        const [d, v = "middle"] = positionToCheck.split("-");
        const TestComp = getTestComponent({
            position,
            onPositioned: (el, { direction, variant }) => {
                assert.equal(d, direction);
                assert.equal(v, variant);
            },
        });
        await mount(TestComp, container);
    };
}

function getPositionTestRTL(position, positionToCheck) {
    return async (assert) => {
        patchWithCleanup(localization, {
            direction: "rtl",
        });
        await getPositionTest(position, positionToCheck)(assert);
    };
}

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
// RTL
QUnit.test("position RTL top-start", getPositionTestRTL("top-start", "top-end"));
QUnit.test("position RTL top-middle", getPositionTestRTL("top-middle"));
QUnit.test("position RTL top-end", getPositionTestRTL("top-end", "top-start"));
QUnit.test("position RTL bottom-start", getPositionTestRTL("bottom-start", "bottom-end"));
QUnit.test("position RTL bottom-middle", getPositionTestRTL("bottom-middle"));
QUnit.test("position RTL bottom-end", getPositionTestRTL("bottom-end", "bottom-start"));
QUnit.test("position RTL right-start", getPositionTestRTL("right-start", "left-start"));
QUnit.test("position RTL right-middle", getPositionTestRTL("right-middle", "left-middle"));
QUnit.test("position RTL right-end", getPositionTestRTL("right-end", "left-end"));
QUnit.test("position RTL left-start", getPositionTestRTL("left-start", "right-start"));
QUnit.test("position RTL left-middle", getPositionTestRTL("left-middle", "right-middle"));
QUnit.test("position RTL left-end", getPositionTestRTL("left-end", "right-end"));

const CONTAINER_STYLE_MAP = {
    top: { alignItems: "flex-start" },
    bottom: { alignItems: "flex-end" },
    left: { justifyContent: "flex-start" },
    right: { justifyContent: "flex-end" },
    slimfit: { height: "100px", width: "100px" }, // height and width of popper
    h125: { height: "125px" }, // height of popper + 1/2 target
    w125: { width: "125px" }, // width of popper + 1/2 target
};

function getRepositionTest(from, to, containerStyleChanges) {
    return async (assert) => {
        assert.expect(4);
        const TestComp = getTestComponent({
            position: from,
            onPositioned: (el, { direction, variant }) => {
                assert.step(`${direction}-${variant}`);
            },
        });
        await mount(TestComp, container);
        let [d, v = "middle"] = from.split("-");
        assert.verifySteps([`${d}-${v}`], `has ${from} position`);

        // Change container style and force update
        for (const styleToApply of containerStyleChanges.split(" ")) {
            Object.assign(container.style, CONTAINER_STYLE_MAP[styleToApply]);
        }
        triggerEvent(document, null, "scroll");
        await nextTick();
        [d, v = "middle"] = to.split("-");
        assert.verifySteps([`${d}-${v}`], `has ${to} position`);
    };
}

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

function getFittingTest(position, styleAttribute) {
    return async (assert) => {
        const TestComp = getTestComponent({ position });
        await mount(TestComp, container);
        assert.strictEqual(container.querySelector("#popper").style[styleAttribute], "50px");
    };
}

QUnit.test(
    "reposition from bottom-fit to top-fit",
    getRepositionTest("bottom-fit", "top-fit", "bottom")
);
QUnit.test(
    "reposition from top-fit to bottom-fit",
    getRepositionTest("top-fit", "bottom-fit", "top")
);
QUnit.test(
    "reposition from right-fit to left-fit",
    getRepositionTest("right-fit", "left-fit", "right")
);
QUnit.test(
    "reposition from left-fit to right-fit",
    getRepositionTest("left-fit", "right-fit", "left")
);
QUnit.test("bottom-fit has the same width as the target", getFittingTest("bottom-fit", "width"));
QUnit.test("top-fit has the same width as the target", getFittingTest("top-fit", "width"));
QUnit.test("left-fit has the same height as the target", getFittingTest("left-fit", "height"));
QUnit.test("right-fit has the same height as the target", getFittingTest("right-fit", "height"));
