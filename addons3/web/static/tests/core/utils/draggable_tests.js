/** @odoo-module **/

import { drag, dragAndDrop, getFixture, mount, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { useDraggable } from "@web/core/utils/draggable";
import { browser } from "@web/core/browser/browser";

import { Component, reactive, useRef, useState, xml } from "@odoo/owl";

let target;
QUnit.module("Draggable", ({ beforeEach }) => {
    beforeEach(() => (target = getFixture()));

    QUnit.module("Draggable hook");

    QUnit.test("Parameters error handling", async (assert) => {
        assert.expect(5);

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
            useDraggable({});
        }, true);
        await mountListAndAssert(() => {
            useDraggable({
                elements: ".item",
            });
        }, true);

        // Correct params
        await mountListAndAssert(() => {
            useDraggable({
                ref: useRef("root"),
            });
        }, false);
        await mountListAndAssert(() => {
            useDraggable({
                ref: {},
                elements: ".item",
                enable: false,
            });
        }, false);
        await mountListAndAssert(() => {
            useDraggable({
                ref: useRef("root"),
                elements: ".item",
            });
        }, false);
    });

    QUnit.test("Simple dragging in single group", async (assert) => {
        assert.expect(16);

        class List extends Component {
            setup() {
                useDraggable({
                    ref: useRef("root"),
                    elements: ".item",
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.strictEqual(element.innerText, "1");
                    },
                    onDrag({ element }) {
                        assert.step("drag");
                        assert.strictEqual(element.innerText, "1");
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.innerText, "1");
                        assert.containsN(target, ".item", 3);
                    },
                    onDrop({ element }) {
                        assert.step("drop");
                        assert.strictEqual(element.innerText, "1");
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
        assert.verifySteps(["start", "drag", "drop", "end"]);
    });

    QUnit.test("Dynamically disable draggable feature", async (assert) => {
        assert.expect(4);

        const state = reactive({ enableDrag: true });
        class List extends Component {
            setup() {
                this.state = useState(state);
                useDraggable({
                    ref: useRef("root"),
                    elements: ".item",
                    enable: () => this.state.enableDrag,
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

        state.enableDrag = false;
        await nextTick();

        // First item before last item
        await dragAndDrop(".item:first-child", ".item:last-child");

        // Drag shouldn't have occurred
        assert.verifySteps([]);
    });

    QUnit.test("Ignore specified elements", async (assert) => {
        assert.expect(6);

        class List extends Component {
            setup() {
                useDraggable({
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

    QUnit.test("Ignore specific elements in a nested draggable", async (assert) => {
        assert.expect(7);

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
            setup() {
                useDraggable({
                    ref: useRef("root"),
                    elements: ".item",
                    preventDrag: (el) => el.classList.contains('ignored'),
                    onDragStart() {
                        assert.step("drag");
                    },
                });
            }
        }

        await mount(List, target);

        assert.verifySteps([]);

        // Drag ignored under non-ignored -> block
        await dragAndDrop(
            ".not-ignored.parent .ignored.child",
            ".not-ignored.parent .not-ignored.child"
        );
        assert.verifySteps([]);

        // Drag not-ignored-under not-ignored -> succeed
        await dragAndDrop(
            ".not-ignored.parent .not-ignored.child",
            ".not-ignored.parent .ignored.child"
        );
        assert.verifySteps(["drag"]);

        // Drag ignored under ignored -> block
        await dragAndDrop(
            ".ignored.parent .ignored.child",
            ".ignored.parent .not-ignored.child"
        );
        assert.verifySteps([]);

        // Drag not-ignored under ignored -> succeed
        await dragAndDrop(
            ".ignored.parent .not-ignored.child",
            ".ignored.parent .ignored.child"
        );
        assert.verifySteps(["drag"]);
    });

    QUnit.test("Dragging element with touch event", async (assert) => {
        assert.expect(10);

        patchWithCleanup(browser, {
            matchMedia: (media) => {
                if (media === "(pointer:coarse)") {
                    return { matches: true };
                } else {
                    this._super();
                }
            },
            setTimeout: (fn, delay) => {
                assert.strictEqual(delay, 300, "touch drag has a default 300ms initiation delay");
                fn();
            }
        });

        class List extends Component {
            setup() {
                useDraggable({
                    ref: useRef("root"),
                    elements: ".item",
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.hasClass(element, "o_touch_bounce", "element has the animation class applied");
                    },
                    onDrag() {
                        assert.step("drag");
                    },
                    onDragEnd() {
                        assert.step("end");
                    },
                    async onDrop({ element }) {
                        assert.step("drop");
                        await nextTick();
                        assert.doesNotHaveClass(element, "o_touch_bounce", "element no longer has the animation class applied");
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

        const { drop, moveTo } = await drag(".item:first-child", "touch");
        await moveTo(".item:nth-child(2)");
        assert.hasClass(target.querySelector(".item"), "o_dragged");

        await drop();
        assert.verifySteps(["start", "drag", "drop", "end"]);
    });

    QUnit.test("Dragging element with touch event: initiation delay can be overrided", async (assert) => {
        patchWithCleanup(browser, {
            matchMedia: (media) => {
                if (media === "(pointer:coarse)") {
                    return { matches: true };
                } else {
                    this._super();
                }
            },
            setTimeout: (fn, delay) => {
                assert.strictEqual(delay, 1000, "touch drag has the custom initiation delay");
                fn();
            }
        });

        class List extends Component {
            setup() {
                useDraggable({
                    ref: useRef("root"),
                    delay: 1000,
                    elements: ".item",
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
        const { drop, moveTo } = await drag(".item:first-child", "touch");
        await moveTo(".item:nth-child(2)");
        await drop();
    });
});
