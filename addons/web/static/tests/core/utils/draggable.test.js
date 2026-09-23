// @ts-check

import { expect, test } from "@odoo/hoot";
import {
    hover,
    pointerDown,
    pointerUp,
    press,
    queryOne,
    queryRect,
} from "@odoo/hoot-dom";
import { advanceTime, animationFrame, mockTouch, mockUserAgent } from "@odoo/hoot-mock";
import { Component, reactive, useRef, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { useDraggable } from "@web/core/utils/dnd/draggable";
import { DEFAULT_DEFAULT_PARAMS } from "@web/core/utils/dnd/draggable_hook_builder_utils";

test("Parameters error handling", async () => {
    expect.assertions(2);

    const mountList = async (setupList) => {
        class List extends Component {
            static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                    </ul>
                </div>`;
            static props = ["*"];
            setup() {
                setupList();
            }
        }
        await mountWithCleanup(List);
    };

    await mountList(() => {
        // @ts-expect-error
        expect(() => useDraggable({})).toThrow(
            `Error in hook useDraggable: missing required property "ref" in parameter`,
        );
    });
    await mountList(() => {
        expect(() =>
            // @ts-expect-error
            useDraggable({
                elements: ".item",
            }),
        ).toThrow(
            `Error in hook useDraggable: missing required property "ref" in parameter`,
        );
    });

    await mountList(() => {
        useDraggable({
            ref: useRef("root"),
        });
    });
    await mountList(() => {
        useDraggable({
            ref: { el: null },
            elements: ".item",
            enable: false,
        });
    });
    await mountList(() => {
        useDraggable({
            ref: useRef("root"),
            elements: ".item",
        });
    });
});

test("Simple dragging in single group", async () => {
    expect.assertions(11);

    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
                onDragStart({ element }) {
                    expect.step("start");
                    expect(element).toHaveText("1");
                },
                onDragEnd({ element }) {
                    expect.step("end");
                    expect(element).toHaveText("1");
                    expect(".item").toHaveCount(3);
                    expect(".item.o_dragged").toHaveCount(1);
                },
                onDrop({ element }) {
                    expect.step("drop");
                    expect(element).toHaveText("1");
                },
            });
        }
    }

    await mountWithCleanup(List);

    expect(".item").toHaveCount(3);
    expect(".o_dragged").toHaveCount(0);
    expect.verifySteps([]);

    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");

    expect(".item").toHaveCount(3);
    expect(".o_dragged").toHaveCount(0);
    expect.verifySteps(["start", "drop", "end"]);
});

test("Dynamically disable draggable feature", async () => {
    expect.assertions(3);

    const state = reactive({ enableDrag: true });
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            this.state = useState(state);
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
                enable: () => this.state.enableDrag,
                onDragStart() {
                    expect.step("start");
                },
            });
        }
    }

    await mountWithCleanup(List);

    expect.verifySteps([]);

    await contains(".item:first-child").dragAndDrop(".item:last-child");

    expect.verifySteps(["start"]);

    state.enableDrag = false;
    await animationFrame();

    await contains(".item:first-child").dragAndDrop(".item:last-child");

    expect.verifySteps([]);
});

test("Ignore specified elements", async () => {
    expect.assertions(4);

    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" class="item">
                        <span class="ignored" t-out="i" />
                        <span class="not-ignored" t-out="i" />
                    </li>
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
                ignore: ".ignored",
                onDragStart() {
                    expect.step("start");
                },
            });
        }
    }

    await mountWithCleanup(List);

    expect.verifySteps([]);

    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps(["start"]);

    await contains(".item:first-child .not-ignored").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps(["start"]);

    await contains(".item:first-child .ignored").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps([]);
});

test("Ignore specific elements in a nested draggable", async () => {
    expect.assertions(5);

    class List extends Component {
        static components = { List };
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[0, 1]" t-as="i" t-key="i"
                        t-attf-class="item parent #{ i % 2 ? 'ignored' : 'not-ignored' }">
                        <span t-out="'parent' + i" />
                        <ul class="list">
                            <li t-foreach="[0, 1]" t-as="j" t-key="j"
                                t-attf-class="item child #{ j % 2 ? 'ignored' : 'not-ignored' }">
                                <span t-out="'child' + j" />
                            </li>
                        </ul>
                    </li>
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
                preventDrag: (el) => el.classList.contains("ignored"),
                onDragStart() {
                    expect.step("start");
                },
            });
        }
    }

    await mountWithCleanup(List);

    expect.verifySteps([]);

    await contains(".not-ignored.parent .ignored.child").dragAndDrop(
        ".not-ignored.parent .not-ignored.child",
    );
    expect.verifySteps([]);

    await contains(".not-ignored.parent .not-ignored.child").dragAndDrop(
        ".not-ignored.parent .ignored.child",
    );
    expect.verifySteps(["start"]);

    await contains(".ignored.parent .ignored.child").dragAndDrop(
        ".ignored.parent .not-ignored.child",
    );
    expect.verifySteps([]);

    await contains(".ignored.parent .not-ignored.child").dragAndDrop(
        ".ignored.parent .ignored.child",
    );
    expect.verifySteps(["start"]);
});

test("Dragging element with touch event", async () => {
    expect.assertions(4);
    mockTouch(true);
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
                onDragStart({ element }) {
                    expect.step("start");
                    expect(".item.o_dragged").toHaveCount(1);
                },
                onDragEnd() {
                    expect.step("end");
                },
                onDrop() {
                    expect.step("drop");
                },
            });
        }
    }

    await mountWithCleanup(List);

    expect.verifySteps([]);

    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");

    expect(".item.o_touch_bounce").toHaveCount(0, {
        message: "element no longer has the animation class applied",
    });
    expect.verifySteps(["start", "drop", "end"]);
});

test("Dragging element with touch event: initiation delay can be overrided", async () => {
    mockTouch(true);
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({
                ref: useRef("root"),
                delay: 1000,
                elements: ".item",
                onDragStart() {
                    expect.step("start");
                },
            });
        }
    }

    await mountWithCleanup(List);
    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)", {
        pointerDownDuration: 700,
    });

    expect.verifySteps([]);

    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)", {
        pointerDownDuration: 1200,
    });

    expect.verifySteps(["start"]);
});

test("Dragging element with touch event: explicit touchDelay wins over delay", async () => {
    mockTouch(true);
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({
                ref: useRef("root"),
                delay: 1000,
                touchDelay: 300,
                elements: ".item",
                onDragStart() {
                    expect.step("start");
                },
            });
        }
    }

    await mountWithCleanup(List);

    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)", {
        pointerDownDuration: 500,
    });
    expect.verifySteps(["start"]);
});

test.tags("desktop");
test("Elements are confined within their container and keep their initial width and height", async () => {
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root" style="width: 800px; height: 600px;">
                <ul class="list list-unstyled m-0 d-flex flex-column">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item w-50 h-100" />
                </ul>
            </div>
        `;
        static props = ["*"];

        setup() {
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
            });
        }
    }

    await mountWithCleanup(List);

    const containerRect = queryRect(".root");
    const { width: initialWidth, height: initialHeight } = queryRect(".item:first");

    const { moveTo, drop } = await contains(".item:first").drag({
        initialPointerMoveDistance: 0,
        position: { x: 0, y: 0 },
    });

    expect(".item:first").toHaveRect({
        x: containerRect.x,
        y: containerRect.y,
        width: containerRect.width / 2,
    });

    await moveTo(".item:last-child", {
        position: { x: 0, y: 9999 },
    });

    expect(".item:first").toHaveRect({
        x: containerRect.x,
        y: containerRect.y + containerRect.height - queryRect(".item:first").height,
    });

    expect(".item:first").toHaveRect({
        width: initialWidth,
        height: initialHeight,
    });

    await moveTo(".item:last-child", {
        position: { x: 9999, y: 9999 },
    });

    expect(".item:first").toHaveRect({
        x: containerRect.x + containerRect.width - queryRect(".item:first").width,
        y: containerRect.y + containerRect.height - queryRect(".item:first").height,
    });

    await moveTo(".item:last-child", {
        position: { x: -9999, y: -9999 },
    });

    expect(".item:first").toHaveRect({
        x: containerRect.x,
        y: containerRect.y,
    });

    await drop();
});

test("Focusing is not lost after clicking", async () => {
    expect.assertions(1);

    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <input type="checkbox" class="item">Something</input>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
            });
        }
    }

    await mountWithCleanup(List);

    await contains(".item").click();
    expect(".item").toBeFocused();
});

test("allowDisconnected option", async () => {
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <button class="handle" t-if="this.state.hasHandle">Handle</button>
                <ul class="list list-unstyled m-0 d-flex flex-column">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item w-50 h-100" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            this.state = useState({ hasHandle: true });
            useDraggable({
                ref: useRef("root"),
                elements: ".handle",
                allowDisconnected: true,
                onDragStart: () => {
                    expect.step("start");
                    this.state.hasHandle = false;
                },
                onDragEnd: () => expect.step("end"),
                onDrop: () => expect.step("drop"),
            });
        }
    }

    await mountWithCleanup(List);
    const { moveTo, drop } = await contains(".handle").drag();
    expect.verifySteps(["start"]);
    await animationFrame();
    expect(".handle").toHaveCount(0);
    await moveTo(".item:nth-child(2)");
    await drop();
    expect.verifySteps(["drop", "end"]);
});

test("willDrag is lowered again when the press never becomes a drag", async () => {
    /** @type {any} */
    let dragState;
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            dragState = useDraggable({ ref: useRef("root"), elements: ".item" });
        }
    }
    await mountWithCleanup(List);
    expect(dragState.willDrag).toBe(false);

    await pointerDown(".item:first-child");
    await advanceTime(DEFAULT_DEFAULT_PARAMS.touchDelay);
    expect(dragState.willDrag).toBe(true);
    await pointerUp(".item:first-child");

    expect(dragState.dragging).toBe(false);
    expect(dragState.willDrag).toBe(false);
});

/** @param {Record<string, any>} [hookParams] */
function makeDraggableList(hookParams = {}) {
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-out="i" class="item" />
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({ ref: useRef("root"), elements: ".item", ...hookParams });
        }
    }
    return List;
}

function expectNoDragResidue() {
    expect(document.body).not.toHaveClass("pe-none");
    expect(document.body).not.toHaveClass("user-select-none");
    expect(".o_dragged").toHaveCount(0);
}

test("a non-whitelisted keydown mid-drag releases the document", async () => {
    await mountWithCleanup(makeDraggableList());

    const { drop, moveTo } = await contains(".item:first-child").drag();
    await moveTo(".item:nth-child(2)");
    expect(document.body).toHaveClass("pe-none");
    expect(".o_dragged").toHaveCount(1);

    await press("Escape");
    await animationFrame();
    expectNoDragResidue();

    await drop();
    expectNoDragResidue();
});

test("pointercancel mid-drag releases the document", async () => {
    await mountWithCleanup(makeDraggableList());

    const { moveTo } = await contains(".item:first-child").drag();
    await moveTo(".item:nth-child(2)");
    expect(document.body).toHaveClass("pe-none");

    window.dispatchEvent(new PointerEvent("pointercancel", { bubbles: true }));
    await animationFrame();
    expectNoDragResidue();
});

test("a throwing drop handler releases the document before rethrowing", async () => {
    expect.errors(1);
    await mountWithCleanup(
        makeDraggableList({
            onDrop() {
                throw new Error("boom from onDrop");
            },
        }),
    );

    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");
    await animationFrame();

    expectNoDragResidue();
    expect.verifyErrors(["Error: boom from onDrop"]);
});

test("unmounting mid-drag releases the document", async () => {
    const state = reactive({ visible: true });
    class Parent extends Component {
        static components = { List: makeDraggableList() };
        static template = xml`<t t-if="this.state.visible"><List/></t>`;
        static props = ["*"];
        setup() {
            this.state = useState(state);
        }
    }
    await mountWithCleanup(Parent);

    const { moveTo } = await contains(".item:first-child").drag();
    await moveTo(".item:nth-child(2)");
    expect(document.body).toHaveClass("pe-none");

    state.visible = false;
    await animationFrame();
    expectNoDragResidue();
});

test("tolerance 0 starts the drag on the first move", async () => {
    await mountWithCleanup(
        makeDraggableList({
            tolerance: 0,
            onDragStart: () => expect.step("start"),
        }),
    );

    const { drop } = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 1,
    });
    expect.verifySteps(["start"]);

    await drop();
    expectNoDragResidue();
});

/**
 * @param {string} selector
 * @param {number} offset
 */
async function pressAndNudge(selector, offset) {
    const helpers = await contains(selector).drag({ initialPointerMoveDistance: 0 });
    const rect = queryRect(selector);
    await hover(selector, {
        position: { x: rect.width / 2 + offset, y: rect.height / 2 + offset },
        relative: true,
    });
    await animationFrame();
    return helpers;
}

test("a pointer move shorter than the tolerance does not start a drag", async () => {
    await mountWithCleanup(
        makeDraggableList({ onDragStart: () => expect.step("start") }),
    );

    const { drop, moveTo } = await pressAndNudge(".item:first-child", 3);
    expect.verifySteps([], { message: "hypot(3, 3) is under the 10px tolerance" });
    expect(".o_dragged").toHaveCount(0);

    await moveTo(".item:nth-child(2)");
    expect.verifySteps(["start"], { message: "crossing the tolerance starts it" });
    expect(".o_dragged").toHaveCount(1);

    await drop();
    expectNoDragResidue();
});

test("a drag released under the tolerance never starts and leaves no residue", async () => {
    await mountWithCleanup(
        makeDraggableList({
            onDragStart: () => expect.step("start"),
            onDrop: () => expect.step("drop"),
            onDragEnd: () => expect.step("end"),
        }),
    );

    const { drop } = await pressAndNudge(".item:first-child", 2);
    await drop();

    expect.verifySteps([], { message: "a click-sized move is not a drag" });
    expectNoDragResidue();
});

/** @param {Record<string, any>} [hookParams] */
function makeScrollableDraggableList(hookParams = {}) {
    class List extends Component {
        static template = xml`
            <div class="scroll" style="height: 100px; overflow-y: auto;">
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="this.items" t-as="i" t-key="i" t-out="i"
                            class="item" style="height: 30px;"/>
                    </ul>
                </div>
            </div>`;
        static props = ["*"];
        setup() {
            this.items = [...Array(20).keys()];
            useDraggable({ ref: useRef("root"), elements: ".item", ...hookParams });
        }
    }
    return List;
}

/** @param {number} y */
async function dragIntoScrollerAt(y) {
    const helpers = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 0,
    });
    await hover(".scroll", { position: { x: 40, y }, relative: true });
    await advanceTime(200);
    return helpers;
}

test("dragging against the bottom edge scrolls the scroll parent", async () => {
    await mountWithCleanup(makeScrollableDraggableList());
    const scroller = queryOne(".scroll");
    expect(scroller.scrollTop).toBe(0);

    const { drop } = await dragIntoScrollerAt(95);
    expect(scroller.scrollTop).toBeGreaterThan(0);

    await drop();
    expectNoDragResidue();
});

test("dragging away from the edges does not scroll", async () => {
    await mountWithCleanup(makeScrollableDraggableList());
    const scroller = queryOne(".scroll");

    const { drop } = await dragIntoScrollerAt(50);
    expect(scroller.scrollTop).toBe(0, {
        message: "50px down a 100px-tall box is outside the 30px threshold",
    });

    await drop();
    expectNoDragResidue();
});

test("edgeScrolling disabled never scrolls", async () => {
    await mountWithCleanup(
        makeScrollableDraggableList({ edgeScrolling: { enabled: false } }),
    );
    const scroller = queryOne(".scroll");

    const { drop } = await dragIntoScrollerAt(95);
    expect(scroller.scrollTop).toBe(0);

    await drop();
    expectNoDragResidue();
});

test("a right-click never starts a drag", async () => {
    await mountWithCleanup(
        makeDraggableList({ onDragStart: () => expect.step("start") }),
    );

    await pointerDown(".item:first-child", { button: 2 });
    await hover(".item:nth-child(3)");
    await animationFrame();

    expect.verifySteps([]);
    expect(".o_dragged").toHaveCount(0);

    await pointerUp(".item:nth-child(3)");
    expectNoDragResidue();
});

test("starting a drag blurs what was focused outside the dragged element", async () => {
    class Parent extends Component {
        static components = { List: makeDraggableList() };
        static template = xml`<div><input class="outside"/><List/></div>`;
        static props = ["*"];
    }
    await mountWithCleanup(Parent);

    const outside = queryOne(".outside");
    outside.focus();
    expect(document.activeElement).toBe(outside);

    const { drop } = await contains(".item:first-child").drag();
    expect(document.activeElement).not.toBe(outside);

    await drop();
    expectNoDragResidue();
});

test.tags("desktop");
test("a delayed drag is cancelled when the pointer left the element before it fires", async () => {
    await mountWithCleanup(
        makeDraggableList({ delay: 100, onDragStart: () => expect.step("start") }),
    );

    const { drop, moveTo } = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 0,
        pointerDownDuration: 0,
    });
    await hover(".item:last-child");
    await advanceTime(200);

    expect.verifySteps([], { message: "the press was abandoned before it armed" });
    expect(".o_dragged").toHaveCount(0);

    await moveTo(".item:nth-child(2)");
    expect.verifySteps([], { message: "and it stays abandoned" });

    await drop();
    expectNoDragResidue();
});

test("a delayed press that drifted off the element never arms the drag", async () => {
    await mountWithCleanup(
        makeDraggableList({
            delay: 100,
            onWillStartDrag: () => expect.step("willStart"),
            onDragStart: () => expect.step("start"),
        }),
    );

    const { drop } = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 0,
        pointerDownDuration: 0,
    });
    await hover(".item:last-child");
    await advanceTime(200);

    expect.verifySteps([], {
        message: "the press is abandoned before it arms, so nothing is torn down after",
    });

    await drop();
    expectNoDragResidue();
});

test.tags("mobile");
test("a delayed touch drag is cancelled when the finger left the element too", async () => {
    await mountWithCleanup(
        makeDraggableList({ delay: 100, onDragStart: () => expect.step("start") }),
    );

    await pointerDown(".item:first-child");
    await hover(".item:last-child");
    await advanceTime(200);

    expect.verifySteps([], { message: "the press was abandoned before it armed" });
    expect(".o_dragged").toHaveCount(0);

    await hover(".item:nth-child(2)");
    expect.verifySteps([], { message: "and it stays abandoned" });

    await pointerUp(".item:nth-child(2)");
    expectNoDragResidue();
});

test("a delayed drag starts when the pointer stayed on the element", async () => {
    await mountWithCleanup(
        makeDraggableList({ delay: 100, onDragStart: () => expect.step("start") }),
    );

    const { drop, moveTo } = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 0,
    });
    await advanceTime(200);
    expect.verifySteps([], {
        message: "the delay arms the drag, it does not start it",
    });

    await moveTo(".item:nth-child(2)");
    expect.verifySteps(["start"]);
    expect(".o_dragged").toHaveCount(1);

    await drop();
    expectNoDragResidue();
});

/** @param {string} itemInner */
function makeTouchDraggableList(itemInner = "") {
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" class="item"
                        t-att-href="'#item-' + i">${itemInner}</li>
                </ul>
            </div>`;
        static props = ["*"];
        setup() {
            useDraggable({ ref: useRef("root"), elements: ".item" });
        }
    }
    return List;
}

test("a touch press marks the element while the delay runs", async () => {
    mockTouch(true);
    await mountWithCleanup(makeTouchDraggableList());

    const { drop } = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 0,
    });
    expect(".item:first-child").toHaveClass("o_touch_bounce");

    await drop();
    expect(".o_touch_bounce").toHaveCount(0);
});

test("a touch press strips hrefs on firefox so the link cannot navigate", async () => {
    mockTouch(true);
    mockUserAgent(/** @type {any} */ ("Firefox/130.0"));
    await mountWithCleanup(makeTouchDraggableList());
    expect(".item:first-child").toHaveAttribute("href");

    const { drop } = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 0,
    });
    expect(".item:first-child").not.toHaveAttribute("href");

    await drop();
    expect(".item:first-child").toHaveAttribute("href");
});

test("a touch press un-draggables images on iOS", async () => {
    mockTouch(true);
    mockUserAgent("ios");
    await mountWithCleanup(makeTouchDraggableList(`<img src="#"/>`));

    const { drop } = await contains(".item:first-child").drag({
        initialPointerMoveDistance: 0,
    });
    expect(".item:first-child img").toHaveAttribute("draggable", "false");

    await drop();
});
