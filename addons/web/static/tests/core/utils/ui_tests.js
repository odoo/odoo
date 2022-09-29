/** @odoo-module **/

import { dragAndDrop, getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { useSortable } from "@web/core/utils/sortable";

const { Component, reactive, useRef, useState, xml } = owl;

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
