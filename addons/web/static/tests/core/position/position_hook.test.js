import { before, destroy, expect, getFixture, test } from "@odoo/hoot";
import {
    manuallyDispatchProgrammaticEvent,
    queryOne,
    queryRect,
    resize,
    scroll,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, useRef, xml } from "@odoo/owl";
import { defineParams, defineStyle, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { usePosition } from "@web/core/position/position_hook";

before(
    () =>
        document.readyState === "complete" ||
        new Promise((resolve) => window.addEventListener("load", resolve, { once: true }))
);

function getTestComponent(popperOptions, styles = {}, target = false) {
    class TestComp extends Component {
        static template = xml`
            <div id="scroll-container" style="overflow: auto; height: 450px">
                <div id="container" t-ref="container" style="background-color: salmon; display: flex; align-items: center; justify-content: center; width: 450px; height: 450px; margin: 25px">
                    <div id="target" t-ref="target" style="background-color: royalblue; width: 50px; height: 50px"/>
                    <div id="popper" t-ref="popper" style="background-color: maroon; height: 100px; width: 100px">
                        <div id="popper-content" t-ref="content" style="background-color: seagreen; height: 50px; width: 50px"/>
                    </div>
                </div>
            </div>
        `;
        static props = ["*"];
        setup() {
            if (!target) {
                target = useRef("target");
            }
            const container = useRef("container");
            const popper = useRef("popper");
            const content = useRef("content");
            onMounted(() => {
                Object.assign(container.el.style, styles.container);
                Object.assign(popper.el.style, styles.popper);
                Object.assign(content.el.style, styles.content);
            });
            usePosition("popper", () => target?.el || target, {
                ...popperOptions,
                container: () => popperOptions?.container || container.el,
            });
        }
    }
    return TestComp;
}

test("default position is bottom-middle", async () => {
    expect.assertions(1);

    const TestComp = getTestComponent({
        onPositioned: (el, { direction, variant }) => {
            expect(`${direction}-${variant}`).toBe("bottom-middle");
        },
    });

    await mountWithCleanup(TestComp);
});

test("can add margin", async () => {
    // Add a sheet to set a margin on the popper
    const SHEET_MARGINS = {
        top: 11,
        right: 12,
        bottom: 13,
        left: 14,
    };

    async function _mountTestComponentAndDestroy(popperOptions) {
        const TestComp = getTestComponent(popperOptions, {
            popper: {
                marginTop: `${SHEET_MARGINS.top}px`,
                marginRight: `${SHEET_MARGINS.right}px`,
                marginBottom: `${SHEET_MARGINS.bottom}px`,
                marginLeft: `${SHEET_MARGINS.left}px`,
            },
        });
        const comp = await mountWithCleanup(TestComp);
        const popBox = queryOne("#popper").getBoundingClientRect();
        const targetBox = queryOne("#target").getBoundingClientRect();
        destroy(comp);
        return [popBox, targetBox];
    }

    // With/without additional margin (default direction is bottom)
    let [popBox, targetBox] = await _mountTestComponentAndDestroy();
    expect(popBox.top).toBe(targetBox.bottom + SHEET_MARGINS.top);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ margin: 10 });
    expect(popBox.top).toBe(targetBox.bottom + SHEET_MARGINS.top + 10);

    // With/without additional margin, direction is top
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "top" });
    expect(popBox.top).toBe(targetBox.top - popBox.height - SHEET_MARGINS.bottom);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "top", margin: 10 });
    expect(popBox.top).toBe(targetBox.top - popBox.height - SHEET_MARGINS.bottom - 10);

    // With/without additional margin, direction is left
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "left" });
    expect(popBox.left).toBe(targetBox.left - popBox.width - SHEET_MARGINS.right);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "left", margin: 10 });
    expect(popBox.left).toBe(targetBox.left - popBox.width - SHEET_MARGINS.right - 10);

    // With/without additional margin, direction is right
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "right" });
    expect(popBox.left).toBe(targetBox.right + SHEET_MARGINS.left);
    [popBox, targetBox] = await _mountTestComponentAndDestroy({ position: "right", margin: 10 });
    expect(popBox.left).toBe(targetBox.right + SHEET_MARGINS.left + 10);
});

test("should flip direction and store it", async () => {
    const TestComp = getTestComponent({
        onPositioned: (el, { direction, variant }) => {
            expect.step(`${direction}-${variant}`);
        },
    });

    // Initial: the test styling allows the popper to be on the bottom
    await mountWithCleanup(TestComp);
    expect.verifySteps(["bottom-middle"]);

    // Move the target down in order to leave not enough space for the popper to be at its bottom
    defineStyle(/* css*/ `#target { margin-top: 50%; }`);
    await scroll(queryOne("#scroll-container"));
    await animationFrame();
    expect.verifySteps(["top-middle"]);

    // Move the target back, popper will still be on top (last direction stored)
    defineStyle(/* css*/ `#target { margin-top: unset !important; }`);
    await scroll(queryOne("#scroll-container"));
    await animationFrame();
    expect.verifySteps(["top-middle"]);
});

test("can disable auto-flipping", async () => {
    const TestComp = getTestComponent({
        flip: false,
        onPositioned: (el, { direction, variant }) => {
            expect.step(`${direction}-${variant}`);
        },
    });

    // Initial: the test styling allows the popper to be on the bottom
    await mountWithCleanup(TestComp);
    expect.verifySteps(["bottom-middle"]);

    // Move the target down in order to leave not enough space for the popper to be at its bottom
    defineStyle(/* css*/ `#target { margin-top: 50%; }`);
    await scroll(queryOne("#scroll-container"));
    await animationFrame();
    // Popper is still on the bottom, because auto-flipping is disabled
    expect.verifySteps(["bottom-middle"]);
});

test("can offset", async () => {
    const expected = {
        direction: "bottom",
        variant: "middle",
        variantOffset: 0,
    };
    const TestComp = getTestComponent({
        onPositioned: (el, { direction, variant, variantOffset }) => {
            expect(direction).toBe(expected.direction);
            expect(variant).toBe(expected.variant);
            expect(variantOffset).toBe(expected.variantOffset);
        },
    });

    await mountWithCleanup(TestComp);

    // Move the target left in order to leave not enough space for the popper to be at its middle
    expected.variantOffset = 25; // 25px offset, which is half the width of the popper minus the width of its target
    queryOne("#container").style.justifyContent = "flex-start";
    await scroll(queryOne("#scroll-container"));
    await animationFrame();
});

test("popper is an inner element", async () => {
    expect.assertions(2);
    class TestComp extends Component {
        static template = xml`
            <div id="not-popper">
                <div id="popper" t-ref="popper"/>
            </div>
        `;
        static props = ["*"];
        setup() {
            usePosition("popper", () => getFixture(), {
                onPositioned: (el) => {
                    expect(queryOne("#not-popper")).not.toBe(el);
                    expect(queryOne("#popper")).toBe(el);
                },
            });
        }
    }

    await mountWithCleanup(TestComp);
});

test("has no effect when component is destroyed", async () => {
    const TestComp = getTestComponent({
        onPositioned: () => {
            expect.step("onPositioned called");
        },
    });

    const comp = await mountWithCleanup(TestComp);
    // onPositioned called when component mounted
    expect.verifySteps(["onPositioned called"]);

    await scroll(queryOne("#scroll-container"), { y: 100 });
    await animationFrame();
    // onPositioned called when container scroll
    expect.verifySteps(["onPositioned called"]);

    await scroll(queryOne("#scroll-container"), { y: 100 });
    destroy(comp);
    await animationFrame();
    // onPositioned not called even if scroll happened right before the component destroys
    expect.verifySteps([]);
});

test("reposition popper when a load event occurs", async () => {
    const TestComp = getTestComponent({
        onPositioned: () => {
            expect.step("onPositioned called");
        },
    });

    await mountWithCleanup(TestComp);
    // onPositioned called when component mounted
    expect.verifySteps(["onPositioned called"]);
    manuallyDispatchProgrammaticEvent(queryOne("#popper"), "load");
    await animationFrame();
    // onPositioned called when load event is triggered
    expect.verifySteps(["onPositioned called"]);
});

test("reposition popper when a scroll event occurs", async () => {
    const TestComp = getTestComponent(
        {
            onPositioned: () => {
                expect.step("onPositioned called");
            },
        },
        {
            popper: {
                overflow: "auto",
                maxHeight: "40px",
            },
        }
    );

    await mountWithCleanup(TestComp);
    // onPositioned called when component mounted
    expect.verifySteps(["onPositioned called"]);
    await scroll(queryOne("#popper"), { y: 10 });
    await animationFrame();
    // onPositioned not called when scroll event is triggered inside popper
    expect.verifySteps([]);
    await scroll(queryOne("#scroll-container"), { y: 10 });
    await animationFrame();
    // onPositioned called when container scroll (parent of popper)
    expect.verifySteps(["onPositioned called"]);
});

test("is positioned relative to its containing block", async () => {
    const fixtureBox = getFixture().getBoundingClientRect();
    // offset the container
    const margin = 15;
    let pos1, pos2;
    let TestComp = getTestComponent(
        {
            onPositioned: (el, pos) => {
                pos1 = pos;
            },
        },
        {
            container: {
                margin: `${margin}px`,
            },
        }
    );

    let popper = await mountWithCleanup(TestComp);

    const popBox1 = queryOne("#popper").getBoundingClientRect();
    destroy(popper);

    TestComp = getTestComponent(
        {
            onPositioned: (el, pos) => {
                pos2 = pos;
            },
        },
        {
            container: {
                margin: `${margin}px`,
                contain: "layout",
            },
        }
    );

    popper = await mountWithCleanup(TestComp);
    const popBox2 = queryOne("#popper").getBoundingClientRect();
    destroy(popper);

    // best positions are not the same relative to their containing block
    expect(pos1.top).toBe(pos2.top + margin + fixtureBox.top);
    expect(pos1.left).toBe(pos2.left + margin + fixtureBox.left);
    // best positions are the same relative to the viewport
    expect(popBox1.top).toBe(popBox2.top);
    expect(popBox1.left).toBe(popBox2.left);
});

function getPopperComponent(popperOptions, target) {
    class PopperComp extends Component {
        static template = xml`
            <div id="popper" t-ref="popper" style="background-color: plum; height: 100px; width: 100px">
                <div id="popper-content" style="background-color: coral; height: 50px; width: 50px"/>
            </div>
        `;
        static props = ["*"];
        setup() {
            usePosition("popper", () => target?.el || target, {
                ...popperOptions,
                container: () => popperOptions?.container,
            });
        }
    }
    return PopperComp;
}

test("iframe: popper is outside, target inside", async () => {
    await mountWithCleanup(
        `<div id="container" style="background-color: salmon; display: flex; align-items: center; justify-content: center; width: 450px; height: 450px; margin: 25px"/>`
    );

    const iframe = document.createElement("iframe");
    Object.assign(iframe.style, {
        height: "200px",
        width: "400px",
        margin: "25px",
    });
    iframe.srcdoc = `<div id="target" style="background-color: tomato; width: 50px; height: 50px"/>`;
    const def = new Deferred();
    iframe.onload = () => def.resolve();
    const container = queryOne("#container");
    container.appendChild(iframe);
    await def;

    const iframeBody = iframe.contentDocument.body;
    Object.assign(iframeBody.style, {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "papayawhip",
        height: "300px",
        width: "400px",
        overflowX: "hidden",
    });

    // Prepare popper outside iframe
    const popperTarget = iframe.contentDocument.getElementById("target");
    let onPositionedArgs;
    const Popper = getPopperComponent(
        {
            container,
            onPositioned: (el, solution) => {
                onPositionedArgs = { el, solution };
                expect.step(`${solution.direction}-${solution.variant}`);
            },
        },
        popperTarget
    );
    await mountWithCleanup(Popper, { target: container, noMainContainer: true });

    expect.verifySteps(["bottom-middle"]);

    expect("#popper").toHaveCount(1);
    expect("#target").toHaveCount(0);

    expect(":iframe #popper").toHaveCount(0);
    expect(":iframe #target").toHaveCount(1);

    // Check the expected position
    const { top: iframeTop, left: iframeLeft } = iframe.getBoundingClientRect();
    let targetBox = popperTarget.getBoundingClientRect();
    let popperBox = onPositionedArgs.el.getBoundingClientRect();
    let expectedTop = iframeTop + targetBox.top + popperTarget.offsetHeight;
    let expectedLeft =
        iframeLeft + targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    expect(popperBox.top).toBe(expectedTop);
    expect(popperBox.top).toBe(onPositionedArgs.solution.top);

    expect(popperBox.left).toBe(expectedLeft);
    expect(popperBox.left).toBe(onPositionedArgs.solution.left);

    // Scrolling inside the iframe should reposition the popover accordingly
    const previousPositionSolution = onPositionedArgs.solution;
    const scrollOffset = 100;
    await scroll(":iframe html", { y: scrollOffset }, { scrollable: false });
    await animationFrame();
    expect.verifySteps(["bottom-middle"]);
    expect(previousPositionSolution.top).toBe(onPositionedArgs.solution.top + scrollOffset);

    // Check the expected position
    targetBox = popperTarget.getBoundingClientRect();
    popperBox = onPositionedArgs.el.getBoundingClientRect();
    expectedTop = iframeTop + targetBox.top + popperTarget.offsetHeight;
    expectedLeft = iframeLeft + targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    expect(popperBox.top).toBe(expectedTop);
    expect(popperBox.top).toBe(onPositionedArgs.solution.top);

    expect(popperBox.left).toBe(expectedLeft);
    expect(popperBox.left).toBe(onPositionedArgs.solution.left);
});

test("iframe: popper is outside, target and container inside", async () => {
    await mountWithCleanup(
        `<div id="container" style="background-color: salmon; display: flex; align-items: center; justify-content: center; width: 700px; height: 700px; margin: 25px"/>`
    );

    const iframe = document.createElement("iframe");
    Object.assign(iframe.style, {
        top: "50px",
        height: "500px",
        width: "325px",
        margin: "100px",
    });
    iframe.srcdoc = `<div id="inner-container"><div id="target" style="background-color: green; width: 50px; height: 500px; top: 50px"/></div>`;
    const def = new Deferred();
    iframe.onload = () => def.resolve();
    const container = queryOne("#container");
    container.appendChild(iframe);
    await def;

    const innerContainer = queryOne(":iframe #inner-container");
    Object.assign(innerContainer.style, {
        display: "flex",
        justifyContent: "center",
        height: "300px",
        width: "300px",
        margin: "10px",
        backgroundColor: "yellow",
        overflowY: "auto",
    });

    const popperTarget = iframe.contentDocument.getElementById("target");
    let onPositionedArgs;
    const Popper = getPopperComponent(
        {
            container,
            onPositioned: (el, solution) => {
                onPositionedArgs = { el, solution };
            },
        },
        popperTarget
    );
    await mountWithCleanup(Popper, { target: container, noMainContainer: true });

    expect("#popper").toHaveCount(1);
    expect("#target").toHaveCount(0);

    expect(":iframe #popper").toHaveCount(0);
    expect(":iframe #target").toHaveCount(1);

    const { top: iframeTop, left: iframeLeft } = iframe.getBoundingClientRect();
    const targetBox = popperTarget.getBoundingClientRect();
    const popperBox = onPositionedArgs.el.getBoundingClientRect();
    const expectedTop = iframeTop + targetBox.top;
    const expectedLeft =
        iframeLeft + targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    expect(popperBox.bottom).toBe(expectedTop);
    expect(popperBox.top).toBe(onPositionedArgs.solution.top);

    expect(popperBox.left).toBe(expectedLeft);
    expect(popperBox.left).toBe(onPositionedArgs.solution.left);
});

test("iframe: both popper and target inside", async () => {
    await mountWithCleanup(`<div id="container"/>`);

    const iframe = document.createElement("iframe");
    Object.assign(iframe.style, {
        height: "200px",
        width: "400px",
        margin: "25px",
    });
    iframe.srcdoc = `<div id="inner-container" />`;
    const def = new Deferred();
    iframe.onload = () => def.resolve();
    queryOne("#container").appendChild(iframe);
    await def;

    const iframeBody = iframe.contentDocument.body;
    Object.assign(iframeBody.style, {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "papayawhip",
        margin: "25px",
        overflowX: "hidden",
    });

    const innerContainer = queryOne(":iframe #inner-container");
    Object.assign(innerContainer.style, {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "450px",
        width: "450px",
        margin: "25px",
        backgroundColor: "khaki",
    });

    let onPositionedArgs;
    const Popper = getTestComponent({
        container: innerContainer,
        onPositioned: (el, solution) => {
            onPositionedArgs = { el, solution };
            expect.step(`${solution.direction}-${solution.variant}`);
        },
    });

    await mountWithCleanup(Popper, { noMainContainer: true, target: innerContainer });
    expect.verifySteps(["bottom-middle"]);

    // Check everything is rendered where it should be
    expect(innerContainer.ownerDocument).toBe(iframe.contentDocument);
    expect(":iframe #inner-container #target").toHaveCount(1);
    expect(":iframe #inner-container #popper").toHaveCount(1);

    // Check the expected position
    const popperTarget = queryOne(":iframe #target");
    let targetBox = popperTarget.getBoundingClientRect();
    let popperBox = onPositionedArgs.el.getBoundingClientRect();
    let expectedTop = targetBox.top + popperTarget.offsetHeight;
    let expectedLeft = targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    expect(popperBox.top).toBe(expectedTop);
    expect(popperBox.top).toBe(onPositionedArgs.solution.top);

    expect(popperBox.left).toBe(expectedLeft);
    expect(popperBox.left).toBe(onPositionedArgs.solution.left);

    // Scrolling inside the iframe should reposition the popover accordingly
    const previousPositionSolution = onPositionedArgs.solution;
    const scrollOffset = 100;
    await scroll(":iframe html", { y: scrollOffset }, { scrollable: false });
    await animationFrame();
    expect.verifySteps(["bottom-middle"]);
    expect(previousPositionSolution.top).toBe(onPositionedArgs.solution.top + scrollOffset);

    // Check the expected position
    targetBox = popperTarget.getBoundingClientRect();
    popperBox = onPositionedArgs.el.getBoundingClientRect();
    expectedTop = targetBox.top + popperTarget.offsetHeight;
    expectedLeft = targetBox.left + popperTarget.offsetWidth / 2 - popperBox.width / 2;

    expect(popperBox.top).toBe(expectedTop);
    expect(popperBox.top).toBe(onPositionedArgs.solution.top);

    expect(popperBox.left).toBe(expectedLeft);
    expect(popperBox.left).toBe(onPositionedArgs.solution.left);
});

test("iframe: default container is the popper owner's document", async () => {
    expect.assertions(1);
    // Prepare an outer iframe, that will hold the popper element
    let def = new Deferred();
    const outerIframe = document.createElement("iframe");
    Object.assign(outerIframe.style, { height: "450px", width: "450px" });
    outerIframe.onload = () => def.resolve();
    getFixture().prepend(outerIframe);
    // registerCleanup(() => outerIframe.remove());
    await def;
    Object.assign(outerIframe.contentDocument.body.style, {
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-start",
        backgroundColor: "salmon",
        height: "450px",
        width: "450px",
        margin: "0",
    });

    def = new Deferred();
    const iframeSheet = outerIframe.contentDocument.createElement("style");
    iframeSheet.onload = () => def.resolve();
    iframeSheet.textContent = `
            #popper {
                background-color: plum;
                height: 100px;
                width: 100px;
            }
        `;
    outerIframe.contentDocument.head.appendChild(iframeSheet);
    await def; // wait for the iframe's stylesheet to be loaded

    // Prepare the inner iframe, that will hold the target element
    def = new Deferred();
    const innerIframe = document.createElement("iframe");
    innerIframe.srcdoc = `<div id="target" />`;
    Object.assign(innerIframe.style, {
        height: "300px",
        width: "120px",
        marginLeft: "10px",
    });
    innerIframe.onload = () => def.resolve();
    outerIframe.contentDocument.body.appendChild(innerIframe);
    await def;
    Object.assign(innerIframe.contentDocument.body.style, {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        height: "300px",
        width: "120px",
        margin: "0",
    });

    // Prepare the target element
    const target = innerIframe.contentDocument.getElementById("target");
    Object.assign(target.style, {
        backgroundColor: "tomato",
        height: "50px",
        width: "50px",
    });

    // Mount the popper component and check its position
    class Popper extends Component {
        static props = ["*"];
        static template = xml`<div id="popper" t-ref="popper" />`;
        setup() {
            usePosition("popper", () => target, {
                position: "top-start",
                onPositioned: (_, { direction, variant }) => {
                    expect(`${direction}-${variant}`).toBe("top-start");
                    // the style setup in this test leaves enough space in the inner iframe
                    // for the popper to be positioned at top-middle, but this is exactly
                    // what we want to avoid: the popper's base container should not be the
                    // inner iframe, but the outer iframe, so the popper should be positioned
                    // at top-start.
                },
            });
        }
    }
    await mountWithCleanup(Popper, { target: outerIframe.contentDocument.body });
});

test("popper as child of another", async () => {
    class Child extends Component {
        static template = /* xml */ xml`
            <div id="child">
                <div class="target" t-ref="ref" style="background-color: peachpuff; height: 100px; width: 10px"/>
                <div class="popper" t-ref="popper" style="background-color: olive; height: 100px; width: 10px"/>
            </div>
        `;
        static props = ["*"];
        setup() {
            const ref = useRef("ref");
            usePosition("popper", () => ref.el, { position: "left" });
        }
    }
    class Parent extends Component {
        static components = { Child };
        static template = /* xml */ xml`
            <div id="container" t-ref="container" style="background-color: salmon; display: flex; align-items: center; justify-content: center; width: 450px; height: 450px; margin: 25px; overflow: auto">
                <div id="target" t-ref="target" style="background-color: tomato; width: 200px; height: 600px"/>
                <div id="popper" t-ref="popper"><Child/></div>
            </div>
        `;
        static props = ["*"];
        setup() {
            const target = useRef("target");
            usePosition("popper", () => target.el);
        }
    }

    await mountWithCleanup(Parent);

    // TODO: needed in mobile for initial positionning, probably a bug to investigate
    await resize();
    await animationFrame();

    const container = queryOne("#container");
    const parentRect = queryRect("#popper");
    const childRect = queryRect("#child .popper");
    const scrollTop = container.scrollHeight - container.offsetHeight;

    await scroll("#container", { top: scrollTop });

    expect("#popper").toHaveRect({
        x: parentRect.x,
        y: parentRect.y - scrollTop,
    });
    expect("#child .popper").toHaveRect({
        x: childRect.x,
        y: childRect.y - scrollTop,
    });
});

test("batch update call", async () => {
    let position = null;
    class TestComponent extends Component {
        static template = xml`
            <div id="container" t-ref="container" style="background-color: salmon; display: flex; align-items: center; justify-content: center; width: 450px; height: 450px; margin: 25px; overflow: auto">
                <div id="target" t-ref="target" style="background-color: tomato; width: 200px; height: 600px"/>
                <div id="popper" t-ref="popper" style="background-color: olive; height: 50px; width: 50px"/>
            </div>
        `;
        static props = ["*"];
        setup() {
            const target = useRef("target");
            position = usePosition("popper", () => target.el, {
                onPositioned: () => {
                    expect.step("positioned");
                },
            });
        }
    }

    await mountWithCleanup(TestComponent);
    expect.verifySteps(["positioned"]);

    position.unlock();
    position.unlock();
    position.unlock();
    await animationFrame();
    expect.verifySteps(["positioned"]);
});

test("not positioned if target not connected", async () => {
    const target = document.createElement("div");
    class TestComponent extends Component {
        static template = xml`
            <div t-ref="container"><div t-ref="popper"/></div>
        `;
        static props = ["*"];
        setup() {
            this.container = useRef("container");
            this.position = usePosition("popper", () => target, {
                onPositioned: () => {
                    expect.step("positioned");
                },
            });
        }
    }

    const comp = await mountWithCleanup(TestComponent);
    expect.verifySteps([]);

    comp.container.el.appendChild(target);
    comp.position.unlock();
    await animationFrame();
    expect.verifySteps(["positioned"]);

    comp.container.el.removeChild(target);
    comp.position.unlock();
    await animationFrame();
    expect.verifySteps([]);
});

function shrinkPopperTest(position, offset, onPositioned, popperStyle = {}) {
    return async () => {
        class TestComp extends Component {
            static template = xml`
                <div id="container" t-ref="container" style="background-color: salmon; display: flex; align-items: center; justify-content: center; width: 450px; height: 450px; margin: 25px;">
                    <div id="target" t-ref="target" style="background-color: royalblue; width: 50px; height: 50px; margin-top: ${offset}px;"/>
                    <div id="popper" t-ref="popper" t-att-style="popperStyle">
                        <div id="popper-content" style="background-color: seagreen; height: 500px; width: 50px;"/>
                    </div>
                </div>
            `;
            static props = ["*"];
            setup() {
                const target = useRef("target");
                const container = useRef("container");
                usePosition("popper", () => target.el, {
                    position,
                    container: () => container.el,
                    onPositioned(el) {
                        expect.step("onPositioned");
                        onPositioned({
                            c: container.el.getBoundingClientRect(),
                            p: el.getBoundingClientRect(),
                            t: target.el.getBoundingClientRect(),
                        });
                    },
                    shrink: true,
                });
            }
            get popperStyle() {
                return Object.entries({
                    "background-color": "maroon",
                    width: "100px",
                    overflow: "auto",
                    ...popperStyle,
                })
                    .map(([k, v]) => `${k}: ${v}`)
                    .join("; ");
            }
        }
        await mountWithCleanup(TestComp);
        expect.verifySteps(["onPositioned"]);
    };
}

test(
    "max height to prevent container overflow - top",
    shrinkPopperTest("top", 10, ({ c, p, t }) => {
        expect(p.top).toBe(c.top);
        expect(p.bottom).toBe(t.top);
    })
);
test(
    "max height to prevent container overflow - bottom",
    shrinkPopperTest("bottom", -10, ({ c, p, t }) => {
        expect(p.top).toBe(t.bottom);
        expect(p.bottom).toBe(c.bottom);
    })
);
test(
    "max height to prevent container overflow - right-start",
    shrinkPopperTest("right-start", 0, ({ c, p, t }) => {
        expect(p.top).toBe(t.top);
        expect(p.bottom).toBe(c.bottom);
    })
);
test(
    "max height to prevent container overflow - right-middle",
    shrinkPopperTest("right-middle", 0, ({ c, p }) => {
        expect(p.top).toBe(c.top);
        expect(p.bottom).toBe(c.bottom);
    })
);
test(
    "max height to prevent container overflow - right-end",
    shrinkPopperTest("right-end", 0, ({ c, p, t }) => {
        expect(p.bottom).toBe(t.bottom);
        expect(p.top).toBe(c.top);
    })
);
test(
    "max height to prevent container overflow - smaller max-height set on element",
    shrinkPopperTest(
        "top",
        10,
        ({ c, p, t }) => {
            expect(p.height).toBe(100);
            expect(p.top).toBe(t.top - 100);
            expect(p.bottom).toBe(t.top);
        },
        { "max-height": "100px" }
    )
);

test(
    "max height to prevent container overflow - greater max-height set on element",
    shrinkPopperTest(
        "top",
        10,
        ({ c, p, t }) => {
            expect(p.height).not.toBe(900);
            expect(p.top).toBe(c.top);
            expect(p.bottom).toBe(t.top);
        },
        { "max-height": "900px" }
    )
);

function getPositionTest(position, positionToCheck) {
    return async () => {
        expect.assertions(2);
        positionToCheck = positionToCheck || position;
        const [d, v = "middle"] = positionToCheck.split("-");
        const TestComp = getTestComponent({
            position,
            onPositioned: (el, { direction, variant }) => {
                expect(d).toBe(direction);
                expect(v).toBe(variant);
            },
        });
        await mountWithCleanup(TestComp);
    };
}

function getPositionTestRTL(position, positionToCheck) {
    return async () => {
        defineParams({
            lang_parameters: {
                direction: "rtl",
            },
        });
        await getPositionTest(position, positionToCheck)();
    };
}

test("position top", getPositionTest("top"));
test("position left", getPositionTest("left"));
test("position bottom", getPositionTest("bottom"));
test("position right", getPositionTest("right"));
test("position top-start", getPositionTest("top-start"));
test("position top-middle", getPositionTest("top-middle"));
test("position top-end", getPositionTest("top-end"));
test("position left-start", getPositionTest("left-start"));
test("position left-middle", getPositionTest("left-middle"));
test("position left-end", getPositionTest("left-end"));
test("position bottom-start", getPositionTest("bottom-start"));
test("position bottom-middle", getPositionTest("bottom-middle"));
test("position bottom-end", getPositionTest("bottom-end"));
test("position right-start", getPositionTest("right-start"));
test("position right-middle", getPositionTest("right-middle"));
test("position right-end", getPositionTest("right-end"));
test("position top === top-middle", getPositionTest("top", "top-middle"));
test("position left === left-middle", getPositionTest("left", "left-middle"));
test("position bottom === bottom-middle", getPositionTest("bottom", "bottom-middle"));
test("position right === right-middle", getPositionTest("right", "right-middle"));
// RTL
test("position RTL top-start", getPositionTestRTL("top-start"));
test("position RTL top-middle", getPositionTestRTL("top-middle"));
test("position RTL top-end", getPositionTestRTL("top-end"));
test("position RTL bottom-start", getPositionTestRTL("bottom-start"));
test("position RTL bottom-middle", getPositionTestRTL("bottom-middle"));
test("position RTL bottom-end", getPositionTestRTL("bottom-end"));
test("position RTL right-start", getPositionTestRTL("right-start"));
test("position RTL right-middle", getPositionTestRTL("right-middle"));
test("position RTL right-end", getPositionTestRTL("right-end"));
test("position RTL left-start", getPositionTestRTL("left-start"));
test("position RTL left-middle", getPositionTestRTL("left-middle"));
test("position RTL left-end", getPositionTestRTL("left-end"));

const CONTAINER_STYLE_MAP = {
    top: { alignItems: "flex-start" },
    bottom: { alignItems: "flex-end" },
    left: { justifyContent: "flex-start" },
    right: { justifyContent: "flex-end" },
    slimfit: { height: "100px", width: "100px" }, // height and width of popper
    h125: { height: "125px" }, // height of popper + 1/2 target
    w125: { width: "125px" }, // width of popper + 1/2 target
};

function getRepositionTest(from, to, containerStyleChanges, extendedFlipping = false) {
    return async () => {
        const TestComp = getTestComponent({
            extendedFlipping,
            position: from,
            onPositioned: (el, { direction, variant }) => {
                expect.step(`${direction}-${variant}`);
            },
        });
        await mountWithCleanup(TestComp);
        let [d, v = "middle"] = from.split("-");
        expect.verifySteps([`${d}-${v}`]);

        // Change container style and force update
        for (const styleToApply of containerStyleChanges.split(" ")) {
            Object.assign(queryOne("#container").style, CONTAINER_STYLE_MAP[styleToApply]);
            Object.assign(queryOne("#scroll-container").style, CONTAINER_STYLE_MAP[styleToApply]);
        }
        await scroll("#scroll-container", { y: 1 });
        await animationFrame();

        [d, v = "middle"] = to.split("-");
        expect.verifySteps([`${d}-${v}`]);
    };
}

// -----------------------------------------------------------------------------
test("reposition from top-start to top", getRepositionTest("top-start", "bottom-start", "top"));
test(
    "reposition from top-start to top right",
    getRepositionTest("top-start", "bottom-end", "top right")
);
test(
    "reposition from top-start to slimfit bottom",
    getRepositionTest("top-start", "top-start", "slimfit bottom")
);
test("reposition from top-start to right", getRepositionTest("top-start", "top-end", "right"));
// -----------------------------------------------------------------------------
test("reposition from top-middle to top", getRepositionTest("top-middle", "bottom-middle", "top"));
test(
    "reposition from top-middle to slimfit bottom",
    getRepositionTest("top-middle", "top-middle", "slimfit bottom")
);
// -----------------------------------------------------------------------------
test(
    "reposition from top-end to top left",
    getRepositionTest("top-end", "bottom-start", "top left")
);
test("reposition from top-end to top", getRepositionTest("top-end", "bottom-end", "top"));
test("reposition from top-end to left", getRepositionTest("top-end", "top-start", "left"));
test(
    "reposition from top-end to slimfit bottom",
    getRepositionTest("top-end", "top-end", "slimfit bottom")
);
// -----------------------------------------------------------------------------
test("reposition from left-start to left", getRepositionTest("left-start", "right-start", "left"));
test(
    "reposition from left-start to left bottom",
    getRepositionTest("left-start", "right-end", "left bottom")
);
test(
    "reposition from left-start to slimfit top",
    getRepositionTest("left-start", "left-start", "slimfit top")
);
test("reposition from left-start to bottom", getRepositionTest("left-start", "left-end", "bottom"));
// -----------------------------------------------------------------------------
test(
    "reposition from left-middle to left",
    getRepositionTest("left-middle", "right-middle", "left")
);
test(
    "reposition from left-middle to slimfit bottom",
    getRepositionTest("left-middle", "left-middle", "slimfit bottom")
);
// -----------------------------------------------------------------------------
test(
    "reposition from left-end to left top",
    getRepositionTest("left-end", "right-start", "left top")
);
test("reposition from left-end to left", getRepositionTest("left-end", "right-end", "left"));
test("reposition from left-end to top", getRepositionTest("left-end", "left-start", "top"));
test(
    "reposition from left-end to slimfit bottom",
    getRepositionTest("left-end", "left-end", "slimfit bottom")
);
// -----------------------------------------------------------------------------
test(
    "reposition from bottom-start to slimfit top",
    getRepositionTest("bottom-start", "bottom-start", "slimfit top")
);
test(
    "reposition from bottom-start to right",
    getRepositionTest("bottom-start", "bottom-end", "right")
);
test(
    "reposition from bottom-start to bottom",
    getRepositionTest("bottom-start", "top-start", "bottom")
);
test(
    "reposition from bottom-start to bottom right",
    getRepositionTest("bottom-start", "top-end", "bottom right")
);
// -----------------------------------------------------------------------------
test(
    "reposition from bottom-middle to slimfit top",
    getRepositionTest("bottom-middle", "bottom-middle", "slimfit top")
);
test(
    "reposition from bottom-middle to bottom",
    getRepositionTest("bottom-middle", "top-middle", "bottom")
);
// -----------------------------------------------------------------------------
test("reposition from bottom-end to left", getRepositionTest("bottom-end", "bottom-start", "left"));
test(
    "reposition from bottom-end to slimfit top",
    getRepositionTest("bottom-end", "bottom-end", "slimfit top")
);
test(
    "reposition from bottom-end to bottom left",
    getRepositionTest("bottom-end", "top-start", "bottom left")
);
test("reposition from bottom-end to bottom", getRepositionTest("bottom-end", "top-end", "bottom"));
// -----------------------------------------------------------------------------
test(
    "reposition from right-start to slimfit top",
    getRepositionTest("right-start", "right-start", "slimfit top")
);
test(
    "reposition from right-start to bottom",
    getRepositionTest("right-start", "right-end", "bottom")
);
test(
    "reposition from right-start to right",
    getRepositionTest("right-start", "left-start", "right")
);
test(
    "reposition from right-start to right bottom",
    getRepositionTest("right-start", "left-end", "right bottom")
);
// -----------------------------------------------------------------------------
test(
    "reposition from right-middle to slimfit bottom",
    getRepositionTest("right-middle", "right-middle", "slimfit bottom")
);
test(
    "reposition from right-middle to right",
    getRepositionTest("right-middle", "left-middle", "right")
);
// -----------------------------------------------------------------------------
test("reposition from right-end to top", getRepositionTest("right-end", "right-start", "top"));
test(
    "reposition from right-end to slimfit bottom",
    getRepositionTest("right-end", "right-end", "slimfit bottom")
);
test(
    "reposition from right-end to right top",
    getRepositionTest("right-end", "left-start", "right top")
);
test("reposition from right-end to right", getRepositionTest("right-end", "left-end", "right"));
// Reposition with all flipping directions allowed
test(
    "extended reposition from top-start to slimfit bottom",
    getRepositionTest("top-start", "center-start", "slimfit bottom", true)
);
test(
    "extended reposition from top-start to right",
    getRepositionTest("top-start", "top-end", "right", true)
);
test(
    "extended reposition from top-middle to slimfit bottom",
    getRepositionTest("top-middle", "center-middle", "slimfit bottom", true)
);
test(
    "extended reposition from top-end to left",
    getRepositionTest("top-end", "top-start", "left", true)
);
test(
    "extended reposition from top-end to slimfit bottom",
    getRepositionTest("top-end", "center-end", "slimfit bottom", true)
);
test(
    "extended reposition from left-start to slimfit top",
    getRepositionTest("left-start", "center-start", "slimfit top", true)
);
test(
    "extended reposition from left-start to bottom",
    getRepositionTest("left-start", "left-end", "bottom", true)
);
test(
    "extended reposition from left-middle to slimfit bottom",
    getRepositionTest("left-middle", "center-middle", "slimfit bottom", true)
);
test(
    "extended reposition from left-end to top",
    getRepositionTest("left-end", "left-start", "top", true)
);
test(
    "extended reposition from left-end to slimfit bottom",
    getRepositionTest("left-end", "center-end", "slimfit bottom", true)
);
test(
    "extended reposition from bottom-start to slimfit top",
    getRepositionTest("bottom-start", "center-start", "slimfit top", true)
);
test(
    "extended reposition from bottom-start to right",
    getRepositionTest("bottom-start", "bottom-end", "right", true)
);
test(
    "extended reposition from bottom-middle to slimfit top",
    getRepositionTest("bottom-middle", "center-middle", "slimfit top", true)
);
test(
    "extended reposition from bottom-end to left",
    getRepositionTest("bottom-end", "bottom-start", "left", true)
);
test(
    "extended reposition from bottom-end to slimfit top",
    getRepositionTest("bottom-end", "center-end", "slimfit top", true)
);
test(
    "extended reposition from right-start to slimfit top",
    getRepositionTest("right-start", "center-start", "slimfit top", true)
);
test(
    "extended reposition from right-start to bottom",
    getRepositionTest("right-start", "right-end", "bottom", true)
);
test(
    "extended reposition from right-middle to slimfit bottom",
    getRepositionTest("right-middle", "center-middle", "slimfit bottom", true)
);
test(
    "extended reposition from right-end to top",
    getRepositionTest("right-end", "right-start", "top", true)
);
test(
    "extended reposition from right-end to slimfit bottom",
    getRepositionTest("right-end", "center-end", "slimfit bottom", true)
);

function getFittingTest(position, styleAttribute) {
    return async () => {
        const TestComp = getTestComponent({ position });
        await mountWithCleanup(TestComp);
        expect("#popper").toHaveStyle(`${styleAttribute}: 50px`);
    };
}

test("reposition from bottom-fit to top-fit", getRepositionTest("bottom-fit", "top-fit", "bottom"));
test("reposition from top-fit to bottom-fit", getRepositionTest("top-fit", "bottom-fit", "top"));
test("reposition from right-fit to left-fit", getRepositionTest("right-fit", "left-fit", "right"));
test("reposition from left-fit to right-fit", getRepositionTest("left-fit", "right-fit", "left"));
test("bottom-fit has the same width as the target", getFittingTest("bottom-fit", "width"));
test("top-fit has the same width as the target", getFittingTest("top-fit", "width"));
test("left-fit has the same height as the target", getFittingTest("left-fit", "height"));
test("right-fit has the same height as the target", getFittingTest("right-fit", "height"));

test("popper with the fit variant and a large content inside is resized to match the toggler - horizontally", async () => {
    const TestComp = getTestComponent(
        { position: "bottom-fit" },
        {
            content: {
                width: "500px",
            },
            popper: {
                width: "unset",
            },
        }
    );
    await mountWithCleanup(TestComp);
    expect(queryOne("#target").getBoundingClientRect().left).toBe(225);
    expect("#popper").toHaveStyle({ left: "225px", width: "50px" });
});

test("popper with the fit variant and a large content inside is resized to match the toggler - vertically", async () => {
    const TestComp = getTestComponent(
        { position: "right-fit" },
        {
            content: {
                height: "500px",
            },
            popper: {
                height: "unset",
            },
        }
    );
    await mountWithCleanup(TestComp);
    expect(queryOne("#target").getBoundingClientRect().top).toBe(225);
    expect("#popper").toHaveStyle({ top: "225px", height: "50px" });
});
