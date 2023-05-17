/** @odoo-module **/

import {
    drag,
    dragAndDrop,
    getFixture,
    makeDeferred,
    mount,
    nextTick,
    patchWithCleanup,
    triggerHotkey
} from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { useSortable } from "@web/core/utils/sortable";

import { Component, reactive, useRef, useState, xml } from "@odoo/owl";

let target;
QUnit.module("UI", ({ beforeEach }) => {
    beforeEach(() => (target = getFixture()));

    QUnit.module("Sortable hook");

    QUnit.test("Parameters error handling", async (assert) => {
        assert.expect(8);

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
                ref: useRef("root"),
            });
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
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
                setup: () => ({ elements: ".item" }),
            });
        }, true);
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
                elements: () => ".item",
            });
        }, true);

        // Correct params
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
        assert.expect(19);

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
                        assert.step("stop");
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
        assert.verifySteps([]);

        // First item after 2nd item
        await dragAndDrop(".item:first-child", ".item:nth-child(2)");

        assert.containsN(target, ".item", 3);
        assert.verifySteps(["start", "elemententer", "stop", "drop"]);
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
                        assert.step("stop");
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
        assert.verifySteps(["start", "groupenter", "stop", "drop"]);
    });

    QUnit.test("Sorting in groups with distinct per-axis scrolling", async (assert) => {
        const nextAnimationFrame = async (timeDelta) => {
            timeStamp += timeDelta;
            animationFrameDef.resolve();
            animationFrameDef = makeDeferred();
            await Promise.resolve();
        };

        let animationFrameDef = makeDeferred();
        let timeStamp = 0;
        let handlers = new Set();

        patchWithCleanup(browser, {
            async requestAnimationFrame(handler) {
                await animationFrameDef;
                // Prevent setRecurringAnimationFrame from being recursive
                // for better test control (only the first iteration/movement
                // is needed to check that the scrolling works).
                if (!handlers.has(handler)) {
                    handler(timeStamp);
                    handlers.add(handler);
                }
            },
            performance: { now: () => timeStamp },
        });

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
        }
        const cancelDrag = async () => {
            triggerHotkey("Escape");
            await nextTick();
            scrollParentY.scrollTop = 0;
            scrollParentX.scrollLeft = 0;
            await nextTick();
            assert.containsNone(target, ".o_dragged");
        }
        assert.containsNone(target, ".o_dragged");

        // Negative horizontal scrolling.
        target.querySelector(".spacer_horizontal").scrollIntoView();
        scrollParentX.scrollLeft = 16;
        await nextTick();
        assertScrolling(50, 16);
        await drag(".item12", ".item11", "left");
        await nextAnimationFrame(16);
        assertScrolling(50, 0);
        await cancelDrag();

        // Positive horizontal scrolling.
        target.querySelector(".spacer_horizontal").scrollIntoView();
        await nextTick();
        assertScrolling(50, 0);
        await drag(".item11", ".item12", "right");
        await nextAnimationFrame(16);
        assertScrolling(50, 16);
        await cancelDrag();

        // Negative vertical scrolling.
        target.querySelector(".root").scrollIntoView();
        await nextTick();
        assertScrolling(100, 0);
        await drag(".item11", ".item11", "top");
        await nextAnimationFrame(16);
        assertScrolling(84, 0);
        await cancelDrag();

        // Positive vertical scrolling.
        target.querySelector(".spacer_before").scrollIntoView();
        await nextTick();
        assertScrolling(0, 0);
        await drag(".item21", ".item21", "bottom");
        await nextAnimationFrame(16);
        assertScrolling(16, 0);
        await cancelDrag();
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

    QUnit.test("Disabled in small environment", async (assert) => {
        assert.expect(2);

        class List extends Component {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    onDragStart() {
                        throw new Error("Shouldn't start the sortable feature.");
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

        await mount(List, target, { env: { isSmall: true } });

        assert.containsN(target, ".item", 3);

        // First item after 2nd item
        await dragAndDrop(".item:first-child", ".item:nth-child(2)");

        assert.ok(true, "No drag sequence should have been initiated");
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
                            assert.step("Initation of the drag sequence");
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
            await dragAndDrop(".item:first-child", ".item:first-child", { x: 5, y: 5 });
            assert.verifySteps([], "No drag sequence should have been initiated");

            // Move the element from more than 10 pixels
            await dragAndDrop(".item:first-child", ".item:first-child", { x: 10, y: 10 });
            assert.verifySteps(
                ["Initation of the drag sequence"],
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
});
