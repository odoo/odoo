import { expect, test } from "@odoo/hoot";
import { queryRect } from "@odoo/hoot-dom";
import { animationFrame, mockTouch } from "@odoo/hoot-mock";
import { Component, reactive, useRef, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { useDraggable } from "@web/core/utils/draggable";

test("Parameters error handling", async () => {
    expect.assertions(2);

    const mountList = async (setupList) => {
        class List extends Component {
            static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>`;
            static props = ["*"];
            setup() {
                setupList();
            }
        }
        await mountWithCleanup(List);
    };

    // Incorrect params
    await mountList(() => {
        expect(() => useDraggable({})).toThrow(
            `Error in hook useDraggable: missing required property "ref" in parameter`
        );
    });
    await mountList(() => {
        expect(() =>
            useDraggable({
                elements: ".item",
            })
        ).toThrow(`Error in hook useDraggable: missing required property "ref" in parameter`);
    });

    // Correct params
    await mountList(() => {
        useDraggable({
            ref: useRef("root"),
        });
    });
    await mountList(() => {
        useDraggable({
            ref: {},
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
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
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

    // First item after 2nd item
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
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
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

    // First item before last item
    await contains(".item:first-child").dragAndDrop(".item:last-child");

    // Drag should have occurred
    expect.verifySteps(["start"]);

    state.enableDrag = false;
    await animationFrame();

    // First item before last item
    await contains(".item:first-child").dragAndDrop(".item:last-child");

    // Drag shouldn't have occurred
    expect.verifySteps([]);
});

test("Ignore specified elements", async () => {
    expect.assertions(4);

    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" class="item">
                        <span class="ignored" t-esc="i" />
                        <span class="not-ignored" t-esc="i" />
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

    // Drag root item element
    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps(["start"]);

    // Drag ignored element
    await contains(".item:first-child .not-ignored").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps(["start"]);

    // Drag non-ignored element
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
                        <span t-esc="'parent' + i" />
                        <ul class="list">
                            <li t-foreach="[0, 1]" t-as="j" t-key="j"
                                t-attf-class="item child #{ j % 2 ? 'ignored' : 'not-ignored' }">
                                <span t-esc="'child' + j" />
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

    // Drag ignored under non-ignored -> block
    await contains(".not-ignored.parent .ignored.child").dragAndDrop(
        ".not-ignored.parent .not-ignored.child"
    );
    expect.verifySteps([]);

    // Drag not-ignored-under not-ignored -> succeed
    await contains(".not-ignored.parent .not-ignored.child").dragAndDrop(
        ".not-ignored.parent .ignored.child"
    );
    expect.verifySteps(["start"]);

    // Drag ignored under ignored -> block
    await contains(".ignored.parent .ignored.child").dragAndDrop(
        ".ignored.parent .not-ignored.child"
    );
    expect.verifySteps([]);

    // Drag not-ignored under ignored -> succeed
    await contains(".ignored.parent .not-ignored.child").dragAndDrop(
        ".ignored.parent .ignored.child"
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
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
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

    // Should DnD, if the timing value is higher then the default delay value (300ms)
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
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
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

    // Shouldn't DnD, if the timing value is below then the delay value (1000ms)
    expect.verifySteps([]);

    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)", {
        pointerDownDuration: 1200,
    });

    // Should DnD, if the timing value is higher then the delay value (1000ms)
    expect.verifySteps(["start"]);
});

test.tags("desktop")("Elements are confined within their container", async () => {
    class List extends Component {
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list list-unstyled m-0 d-flex flex-column">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item w-50" />
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
