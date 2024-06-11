/** @odoo-module **/

import {
    drag,
    dragAndDrop,
    getFixture,
    mockAnimationFrame,
    mount,
    nextTick,
} from "@web/../tests/helpers/utils";
import { useSortable } from "@web/core/utils/sortable_owl";

import { Component, reactive, useRef, useState, xml } from "@odoo/owl";

let target;
QUnit.module("Draggable", ({ beforeEach }) => {
    beforeEach(() => (target = getFixture()));

    QUnit.module("Sortable hook");

    QUnit.test("Parameters error handling", async (assert) => {
        assert.expect(6);

        const mountListAndAssert = async (setupList, shouldThrow) => {
            class List extends Component {
                setup() {
                    setupList();
                }
            }

            List.template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>`;

            let err;
            await mount(List, target).catch((e) => (err = e));

            assert.ok(
                shouldThrow ? err : !err,
                `An error should${shouldThrow ? "" : "n't"} have been thrown when mounting.`
            );
        };

        // Incorrect params
        await mountListAndAssert(() => {
            useSortable({});
        }, true);
        await mountListAndAssert(() => {
            useSortable({
                elements: ".item",
            });
        }, true);
        await mountListAndAssert(() => {
            useSortable({
                elements: ".item",
                groups: ".list",
            });
        }, true);

        // Correct params
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
            });
        }, false);
        await mountListAndAssert(() => {
            useSortable({
                ref: {},
                elements: ".item",
                enable: false,
            });
        }, false);
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                connectGroups: () => true,
            });
        }, false);
    });

    QUnit.test("Simple sorting in single group", async (assert) => {
        assert.expect(22);

        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    onDragStart({ element, group }) {
                        assert.step("start");
                        assert.notOk(group);
                        assert.strictEqual(element.innerText, "1");
                    },
                    onElementEnter({ element }) {
                        assert.step("elemententer");
                        assert.strictEqual(element.innerText, "2");
                    },
                    onDragEnd({ element, group }) {
                        assert.step("end");
                        assert.notOk(group);
                        assert.strictEqual(element.innerText, "1");
                        assert.containsN(target, ".item", 4);
                    },
                    onDrop({ element, group, previous, next, parent }) {
                        assert.step("drop");
                        assert.notOk(group);
                        assert.strictEqual(element.innerText, "1");
                        assert.strictEqual(previous.innerText, "2");
                        assert.strictEqual(next.innerText, "3");
                        assert.notOk(parent);
                    },
                });
            }
        }

        List.template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                </ul>
            </div>`;

        await mount(List, target);

        assert.containsN(target, ".item", 3);
        assert.containsNone(target, ".o_dragged");
        assert.verifySteps([]);

        // First item after 2nd item
        const { drop, moveTo } = await drag(".item:first-child");
        await moveTo(".item:nth-child(2)");

        assert.hasClass(target.querySelector(".item"), "o_dragged");

        await drop();

        assert.containsN(target, ".item", 3);
        assert.containsNone(target, ".o_dragged");
        assert.verifySteps(["start", "elemententer", "drop", "end"]);
    });

    QUnit.test("Simple sorting in multiple groups", async (assert) => {
        assert.expect(20);

        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    groups: ".list",
                    connectGroups: true,
                    onDragStart({ element, group }) {
                        assert.step("start");
                        assert.hasClass(group, "list2");
                        assert.strictEqual(element.innerText, "2 1");
                    },
                    onGroupEnter({ group }) {
                        assert.step("groupenter");
                        assert.hasClass(group, "list1");
                    },
                    onDragEnd({ element, group }) {
                        assert.step("end");
                        assert.hasClass(group, "list2");
                        assert.strictEqual(element.innerText, "2 1");
                    },
                    onDrop({ element, group, previous, next, parent }) {
                        assert.step("drop");
                        assert.hasClass(group, "list2");
                        assert.strictEqual(element.innerText, "2 1");
                        assert.strictEqual(previous.innerText, "1 3");
                        assert.notOk(next);
                        assert.hasClass(parent, "list1");
                    },
                });
            }
        }

        List.template = xml`
            <div t-ref="root" class="root">
                <ul t-foreach="[1, 2, 3]" t-as="l" t-key="l" t-attf-class="list p-3 list{{ l }}">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="l + ' ' + i" class="item" />
                </ul>
            </div>`;

        await mount(List, target);

        assert.containsN(target, ".list", 3);
        assert.containsN(target, ".item", 9);
        assert.verifySteps([]);

        // First item of 2nd list appended to first list
        await dragAndDrop(".list2 .item:first-child", ".list1");

        assert.containsN(target, ".list", 3);
        assert.containsN(target, ".item", 9);
        assert.verifySteps(["start", "groupenter", "drop", "end"]);
    });

    QUnit.test("Sorting in groups with distinct per-axis scrolling", async (assert) => {
        const { advanceFrame } = mockAnimationFrame();
        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    groups: ".list",
                    connectGroups: true,
                    edgeScrolling: { speed: 16, threshold: 25 },
                });
            }
        }

        List.template = xml`
            <div class="scroll_parent_y" style="max-width: 150px; max-height: 200px; overflow-y: scroll; overflow-x: hidden;">
                <div class="spacer_before" style="min-height: 50px;"></div>
                <div class="spacer_horizontal" style="min-height: 50px;"></div>
                <div t-ref="root" class="root d-flex align-items-end" style="overflow-x: scroll;">
                    <div class="d-flex">
                        <div style="padding-left: 20px;"
                            t-foreach="[1, 2, 3]" t-as="c" t-key="c" t-attf-class="list m-0 list{{ c }}">
                            <div style="min-width: 50px; min-height: 50px; padding-top: 20px;"
                                t-foreach="[1, 2, 3]" t-as="l" t-key="l" t-esc="'item' + l + '' + c" t-attf-class="item item{{ l + '' + c }}"/>
                        </div>
                    </div>
                </div>
                <div class="spacer_after" style="min-height: 150px;"></div>
            </div>
        `;
        await mount(List, target);

        assert.containsN(target, ".list", 3);
        assert.containsN(target, ".item", 9);

        const scrollParentX = target.querySelector(".root");
        const scrollParentY = target.querySelector(".scroll_parent_y");
        const assertScrolling = (top, left) => {
            assert.strictEqual(scrollParentY.scrollTop, top);
            assert.strictEqual(scrollParentX.scrollLeft, left);
        };
        const cancelDrag = async (cancel) => {
            await cancel();
            await nextTick();
            scrollParentY.scrollTop = 0;
            scrollParentX.scrollLeft = 0;
            await nextTick();
            assert.containsNone(target, ".o_dragged");
        };
        assert.containsNone(target, ".o_dragged");

        // Negative horizontal scrolling.
        target.querySelector(".spacer_horizontal").scrollIntoView();
        scrollParentX.scrollLeft = 16;
        await nextTick();
        assertScrolling(50, 16);
        let dragHelpers = await drag(".item12");
        await dragHelpers.moveTo(".item11", "left");
        await advanceFrame();
        assertScrolling(50, 0);
        await cancelDrag(dragHelpers.cancel);

        // Positive horizontal scrolling.
        target.querySelector(".spacer_horizontal").scrollIntoView();
        await nextTick();
        assertScrolling(50, 0);
        dragHelpers = await drag(".item11");
        await dragHelpers.moveTo(".item12", "right");
        await advanceFrame();
        assertScrolling(50, 16);
        await cancelDrag(dragHelpers.cancel);

        // Negative vertical scrolling.
        target.querySelector(".root").scrollIntoView();
        await nextTick();
        assertScrolling(100, 0);
        dragHelpers = await drag(".item11");
        await dragHelpers.moveTo(".item11", "top");
        await advanceFrame();
        assertScrolling(84, 0);
        await cancelDrag(dragHelpers.cancel);

        // Positive vertical scrolling.
        target.querySelector(".spacer_before").scrollIntoView();
        await nextTick();
        assertScrolling(0, 0);
        dragHelpers = await drag(".item21");
        await dragHelpers.moveTo(".item21", "bottom");
        await advanceFrame();
        assertScrolling(16, 0);
        await cancelDrag(dragHelpers.cancel);
    });

    QUnit.test("draggable area contains overflowing visible elements", async (assert) => {
        const { advanceFrame } = mockAnimationFrame();
        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("renderer"),
                    elements: ".item",
                    groups: ".list",
                    connectGroups: true,
                });
            }
        }
        List.template = xml`
            <div class="controller" style="max-width: 900px; min-width: 900px;">
                <div class="content" style="max-width: 600px;">
                    <div t-ref="renderer" class="renderer d-flex" style="overflow: visible;">
                        <div t-foreach="[1, 2, 3]" t-as="c" t-key="c" t-attf-class="list m-0 list{{ c }}">
                            <div style="min-width: 300px; min-height: 50px;"
                                t-foreach="[1, 2, 3]" t-as="l" t-key="l" t-esc="'item' + l + '' + c" t-attf-class="item item{{ l + '' + c }}"/>
                        </div>
                    </div>
                </div>
            </div>
        `;
        await mount(List, target);

        const controller = target.querySelector(".controller");
        const content = target.querySelector(".content");
        const renderer = target.querySelector(".renderer");

        assert.strictEqual(content.scrollLeft, 0);
        assert.strictEqual(controller.getBoundingClientRect().width, 900);
        assert.strictEqual(content.getBoundingClientRect().width, 600);
        assert.strictEqual(renderer.getBoundingClientRect().width, 600);
        assert.strictEqual(renderer.scrollWidth, 900);
        assert.containsNone(target, ".item.o_dragged");

        const dragHelpers = await drag(".item11");

        // Drag first record of first group to the right
        await dragHelpers.moveTo(".list3 .item");

        // Next frame (normal time delta)
        await advanceFrame();

        // Verify that there is no scrolling
        assert.strictEqual(content.scrollLeft, 0);
        assert.containsOnce(target, ".item.o_dragged");

        const dragged = target.querySelector(".item.o_dragged");
        const sibling = target.querySelector(".list3 .item");
        // Verify that the dragged element is allowed to go inside the
        // overflowing part of the draggable container.
        assert.strictEqual(
            dragged.getBoundingClientRect().right,
            900 + target.getBoundingClientRect().x
        );
        assert.strictEqual(
            sibling.getBoundingClientRect().right,
            900 + target.getBoundingClientRect().x
        );

        // Cancel drag: press "Escape"
        await dragHelpers.cancel();
        await nextTick();

        assert.containsNone(target, ".item.o_dragged");
    });

    QUnit.test("Dynamically disable sortable feature", async (assert) => {
        assert.expect(4);

        const state = reactive({ enableSortable: true });
        class List extends Component {
            setup() {
                this.state = useState(state);
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    enable: () => this.state.enableSortable,
                    onDragStart() {
                        assert.step("start");
                    },
                });
            }
        }

        List.template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                </ul>
            </div>`;

        await mount(List, target);

        assert.verifySteps([]);

        // First item before last item
        await dragAndDrop(".item:first-child", ".item:last-child");

        // Drag should have occurred
        assert.verifySteps(["start"]);

        state.enableSortable = false;
        await nextTick();

        // First item before last item
        await dragAndDrop(".item:first-child", ".item:last-child");

        // Drag shouldn't have occurred
        assert.verifySteps([]);
    });

    QUnit.test(
        "Drag has a default tolerance of 10 pixels before initiating the dragging",
        async (assert) => {
            assert.expect(3);

            class List extends Component {
                setup() {
                    useSortable({
                        ref: useRef("root"),
                        elements: ".item",
                        onDragStart() {
                            assert.step("Initiation of the drag sequence");
                        },
                    });
                }
            }

            List.template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                </ul>
            </div>`;

            await mount(List, target);

            // Move the element from only 5 pixels
            const listItem = target.querySelector(".item:first-child");
            await dragAndDrop(listItem, listItem, {
                x: listItem.getBoundingClientRect().width / 2,
                y: listItem.getBoundingClientRect().height / 2 + 5,
            });
            assert.verifySteps([], "No drag sequence should have been initiated");

            // Move the element from more than 10 pixels
            await dragAndDrop(".item:first-child", ".item:first-child", {
                x: listItem.getBoundingClientRect().width / 2 + 10,
                y: listItem.getBoundingClientRect().height / 2 + 10,
            });
            assert.verifySteps(
                ["Initiation of the drag sequence"],
                "A drag sequence should have been initiated"
            );
        }
    );

    QUnit.test("Ignore specified elements", async (assert) => {
        assert.expect(6);

        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    ignore: ".ignored",
                    onDragStart() {
                        assert.step("drag");
                    },
                });
            }
        }

        List.template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" class="item">
                        <span class="ignored" t-esc="i" />
                        <span class="not-ignored" t-esc="i" />
                    </li>
                </ul>
            </div>`;

        await mount(List, target);

        assert.verifySteps([]);

        // Drag root item element
        await dragAndDrop(".item:first-child", ".item:nth-child(2)");

        assert.verifySteps(["drag"]);

        // Drag ignored element
        await dragAndDrop(".item:first-child .not-ignored", ".item:nth-child(2)");

        assert.verifySteps(["drag"]);

        // Drag non-ignored element
        await dragAndDrop(".item:first-child .ignored", ".item:nth-child(2)");

        assert.verifySteps([]);
    });

    QUnit.test("the classes parameters (placeholderElement, helpElement)", async (assert) => {
        assert.expect(7);

        let dragElement;

        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    placeholderClasses: ["placeholder-t1", "placeholder-t2"],
                    followingElementClasses: ["add-1", "add-2"],
                    onDragStart({ element }) {
                        dragElement = element;
                        assert.hasClass(dragElement, "add-1");
                        assert.hasClass(dragElement, "add-2");
                        // the placeholder is added in onDragStart after the current element
                        const children = [...dragElement.parentElement.children];
                        const placeholder = children[children.indexOf(dragElement) + 1];
                        assert.hasClass(placeholder, "placeholder-t1");
                        assert.hasClass(placeholder, "placeholder-t2");
                    },
                });
            }
        }

        List.template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                </ul>
            </div>`;

        await mount(List, target);
        // First item after 2nd item
        const { drop, moveTo } = await drag(".item:first-child");
        await moveTo(".item:nth-child(2)");
        await drop();
        assert.doesNotHaveClass(dragElement, "add-1");
        assert.doesNotHaveClass(dragElement, "add-2");
        assert.containsNone(target, ".item.placeholder-t1.placeholder-t2");
    });

    QUnit.test("applyChangeOnDrop option", async (assert) => {
        assert.expect(2);

        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    placeholderClasses: ["placeholder"],
                    applyChangeOnDrop: true,
                    onDragStart({ element }) {
                        const items = [...target.querySelectorAll(".item:not(.placeholder)")];
                        assert.strictEqual(items.map((el) => el.innerText).toString(), "1,2,3");
                    },
                    onDragEnd({ element, group }) {
                        const items = [...target.querySelectorAll(".item:not(.placeholder)")];
                        assert.strictEqual(items.map((el) => el.innerText).toString(), "2,1,3");
                    },
                });
            }
        }

        List.template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                </ul>
            </div>`;

        await mount(List, target);
        // First item after 2nd item
        const { drop, moveTo } = await drag(".item:first-child");
        await moveTo(".item:nth-child(2)");
        await drop();
    });

    QUnit.test("clone option", async (assert) => {
        assert.expect(2);

        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    placeholderClasses: ["placeholder"],
                    clone: false,
                    onDragStart({ element }) {
                        assert.containsOnce(target, ".placeholder:not(.item)");
                    },
                });
            }
        }

        List.template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                </ul>
            </div>`;

        await mount(List, target);
        // First item after 2nd item
        const { drop, moveTo } = await drag(".item:first-child");
        await moveTo(".item:nth-child(2)");
        await drop();
        assert.containsNone(target, ".placeholder:not(.item)");
    });
});
