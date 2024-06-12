/** @odoo-module **/

import { drag, getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { useNestedSortable } from "@web/core/utils/nested_sortable";

import { Component, reactive, useRef, useState, xml } from "@odoo/owl";

/**
 * Dragging methods taking into account the fact that it's the top of the
 * dragged element that triggers the moves (not the position of the cursor),
 * and the fact that during the first move, the dragged element is replaced by
 * a placeholder that does not have the same height. The moves are done with
 * the same x position to prevent triggering horizontal moves.
 * @param {string} from
 */
export const sortableDrag = async (from) => {
    const fixture = getFixture();
    const fromEl = fixture.querySelector(from);
    const fromRect = fromEl.getBoundingClientRect();
    const { drop, moveTo } = await drag(from);
    let isFirstMove = true;

    /**
     * @param {string} [targetSelector]
     */
    const moveAbove = async (targetSelector) => {
        const el = fixture.querySelector(targetSelector);
        await moveTo(el, {
            x: fromRect.x - el.getBoundingClientRect().x + fromRect.width / 2,
            y: fromRect.height / 2 + 5,
        });
        isFirstMove = false;
    };

    /**
     * @param {string} [targetSelector]
     */
    const moveUnder = async (targetSelector) => {
        const el = fixture.querySelector(targetSelector);
        const elRect = el.getBoundingClientRect();
        let firstMoveBelow = false;
        if (isFirstMove && elRect.y > fromRect.y) {
            // Need to consider that the moved element will be replaced by a
            // placeholder with a height of 5px
            firstMoveBelow = true;
        }
        await moveTo(el, {
            x: fromRect.x - elRect.x + fromRect.width / 2,
            y:
                ((firstMoveBelow ? -1 : 1) * fromRect.height) / 2 +
                elRect.height +
                (firstMoveBelow ? 4 : -1),
        });
        isFirstMove = false;
    };

    return { moveAbove, moveUnder, drop };
};

const dragAndDrop = async (from, to) => {
    const { drop, moveUnder } = await sortableDrag(from);
    await moveUnder(to);
    await drop();
};

let target;
QUnit.module("Draggable", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
        // make fixture in visible range, so that document.elementFromPoint
        // work as expected
        target.style.position = "absolute";
        target.style.top = "0";
        target.style.left = "0";
        target.style.height = "100%";
        target.style.opacity = QUnit.config.debug ? "" : "0";
        registerCleanup(async () => {
            target.style.position = "";
            target.style.top = "";
            target.style.left = "";
            target.style.height = "";
            target.style.opacity = "";
        });
    });

    QUnit.module("NestedSortable hook");

    QUnit.test("Parameters error handling", async (assert) => {
        assert.expect(9);

        const mountNestedSortableAndAssert = async (setupList, shouldThrow) => {
            class NestedSortable extends Component {
                static template = xml`
                    <div t-ref="root">
                        <ul class="sortable_list">
                            <li t-foreach="[1,2,3]" t-as="i" t-key="i" class="item">
                                <span t-out="i"/>
                                <ul class="sub_list">
                                    <li t-foreach="[1,2,3]" t-as="j" t-key="j" class="item">
                                        <span t-out="j"/>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                `;

                setup() {
                    setupList();
                }
            }

            await mount(NestedSortable, target).catch(() => assert.step("thrown"));

            assert.verifySteps(shouldThrow ? ["thrown"] : []);
        };

        // Incorrect params
        await mountNestedSortableAndAssert(() => {
            useNestedSortable({});
        }, true);
        await mountNestedSortableAndAssert(() => {
            useNestedSortable({
                elements: ".item",
            });
        }, true);
        await mountNestedSortableAndAssert(() => {
            useNestedSortable({
                elements: ".item",
                groups: ".list",
            });
        }, true);

        // Correct params
        await mountNestedSortableAndAssert(() => {
            useNestedSortable({
                ref: useRef("root"),
            });
        }, false);
        await mountNestedSortableAndAssert(() => {
            useNestedSortable({
                ref: {},
                elements: ".item",
                groups: ".list",
                enable: false,
            });
        }, false);
        await mountNestedSortableAndAssert(() => {
            useNestedSortable({
                ref: useRef("root"),
                groups: ".list",
                connectGroups: true,
                nest: true,
                listTagName: "ol",
                nestIndent: 20,
            });
        }, false);
    });

    QUnit.test("Sorting in a single group without nesting", async (assert) => {
        assert.expect(34);

        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <ul class="sortable_list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" class="item" t-att-id="i">
                            <span t-out="i"/>
                            <ul class="sub_list">
                                <li t-foreach="[1, 2]" t-as="j" t-key="j" class="item" t-attf-id="{i},{j}">
                                    <span t-out="i + '.' + j"/>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".sortable_list > li",
                    onDragStart({ element, group }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "1");
                        assert.notOk(group);
                    },
                    onMove({
                        element,
                        previous,
                        next,
                        parent,
                        group,
                        newGroup,
                        prevPos,
                        placeholder,
                    }) {
                        assert.step("move");
                        assert.strictEqual(element.id, "1");
                        assert.strictEqual(previous.id, "2");
                        assert.strictEqual(next.id, "3");
                        assert.notOk(parent);
                        assert.notOk(group);
                        assert.notOk(newGroup);
                        assert.strictEqual(prevPos.previous.id, "1");
                        assert.strictEqual(prevPos.next.id, "2");
                        assert.notOk(prevPos.parent);
                        assert.notOk(prevPos.group);
                        assert.strictEqual(placeholder.previousElementSibling.id, "2");
                    },
                    onDrop({ element, previous, next, parent, group, newGroup, placeholder }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "1");
                        assert.strictEqual(previous.id, "2");
                        assert.strictEqual(next.id, "3");
                        assert.notOk(parent);
                        assert.notOk(group);
                        assert.notOk(newGroup);
                        assert.strictEqual(placeholder.previousElementSibling.id, "2");
                    },
                    onDragEnd({ element, group }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "1");
                        assert.notOk(group);
                        assert.containsN(target, ".sortable_list > .item", 4);
                    },
                });
            }
        }

        await mount(NestedSortable, target);

        assert.containsN(target, ".sortable_list > .item", 3);
        assert.containsNone(target, ".o_dragged");
        assert.verifySteps([]);

        // Move first item after second item
        const { drop, moveUnder } = await sortableDrag(".sortable_list > .item:first-child");
        await moveUnder(".sortable_list > .item:nth-child(2)");

        assert.hasClass(target.querySelector(".sortable_list > .item"), "o_dragged");

        await drop();

        assert.containsN(target, ".sortable_list > .item", 3);
        assert.containsNone(target, ".o_dragged");
        assert.verifySteps(["start", "move", "drop", "end"]);
    });

    QUnit.test("Sorting in groups without nesting", async (assert) => {
        assert.expect(38);
        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <section t-foreach="[1,2,3]" t-as="l" t-key="l" t-att-id="l" class="pb-1">
                        <ul class="sortable_list">
                            <li t-foreach="[1,2]" t-as="i" t-key="i" class="item" t-attf-id="#{l}.#{i}">
                                <span t-out="l + '.' + i"/>
                                <ul class="sub_list">
                                    <li t-foreach="[1,2]" t-as="j" t-key="j" class="item" t-attf-id="#{l}.#{i}.#{j}">
                                        <span t-out="l + '.' + i + '.' + j"/>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </section>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".sortable_list > li",
                    groups: "section",
                    connectGroups: true,
                    onDragStart({ element, group }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "2.2");
                        assert.strictEqual(group.id, "2");
                    },
                    onMove({
                        element,
                        previous,
                        next,
                        parent,
                        group,
                        newGroup,
                        prevPos,
                        placeholder,
                    }) {
                        assert.step("move");
                        assert.strictEqual(element.id, "2.2");
                        assert.strictEqual(previous.id, "1.2");
                        assert.notOk(next);
                        assert.notOk(parent);
                        assert.strictEqual(group.id, "2");
                        assert.strictEqual(newGroup.id, "1");
                        assert.strictEqual(prevPos.previous.id, "2.2");
                        assert.notOk(prevPos.next);
                        assert.notOk(prevPos.parent);
                        assert.strictEqual(prevPos.group.id, "2");
                        assert.strictEqual(placeholder.previousElementSibling.id, "1.2");
                    },
                    onGroupEnter({ element, group }) {
                        assert.step("enter");
                        assert.strictEqual(element.id, "2.2");
                        assert.strictEqual(group.id, "1");
                    },
                    onGroupLeave({ element, group }) {
                        assert.step("leave");
                        assert.strictEqual(element.id, "2.2");
                        assert.strictEqual(group.id, "2");
                    },
                    onDrop({ element, previous, next, parent, group, newGroup, placeholder }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "2.2");
                        assert.strictEqual(previous.id, "1.2");
                        assert.notOk(next);
                        assert.notOk(parent);
                        assert.strictEqual(group.id, "2");
                        assert.strictEqual(newGroup.id, "1");
                        assert.strictEqual(placeholder.previousElementSibling.id, "1.2");
                    },
                    onDragEnd({ element, group }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "2.2");
                        assert.strictEqual(group.id, "2");
                    },
                });
            }
        }

        await mount(NestedSortable, target);

        assert.containsN(target, ".sortable_list", 3);
        assert.containsN(target, ".item", 18);
        assert.verifySteps([]);

        // Append second item of second list to first list
        await dragAndDrop("section:nth-child(2) > ul > .item:nth-child(2)", "section:first-child");

        assert.containsN(target, ".sortable_list", 3);
        assert.containsN(target, ".item", 18);
        assert.verifySteps(["start", "move", "enter", "leave", "drop", "end"]);
    });

    QUnit.test("Sorting with nesting - move right", async (assert) => {
        assert.expect(29);
        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <ul class="sortable_list">
                        <li t-foreach="[1,2,3]" t-as="i" t-key="i" class="item" t-att-id="i">
                            <span t-out="i"/>
                            <ul class="sub_list">
                                <li t-attf-id="sub#{i}" class="item">
                                    <span t-out="'sub' + i"/>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    nest: true,
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "2");
                        this.firstMove = true;
                    },
                    onMove({ element, previous, next, parent, prevPos }) {
                        if (this.firstMove) {
                            assert.step("move 1");
                            assert.strictEqual(element.id, "2");
                            assert.strictEqual(previous.id, "sub1");
                            assert.notOk(next);
                            assert.strictEqual(parent.id, "1");
                            assert.strictEqual(prevPos.previous.id, "2");
                            assert.strictEqual(prevPos.next.id, "3");
                            assert.notOk(prevPos.parent);
                            this.firstMove = false;
                        } else {
                            assert.step("move 2");
                            assert.strictEqual(element.id, "2");
                            assert.notOk(previous);
                            assert.notOk(next);
                            assert.strictEqual(parent.id, "sub1");
                            assert.strictEqual(prevPos.previous.id, "sub1");
                            assert.notOk(prevPos.next);
                            assert.strictEqual(prevPos.parent.id, "1");
                        }
                    },
                    onDrop({ element, previous, next, parent }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "2");
                        assert.notOk(previous);
                        assert.notOk(next);
                        assert.strictEqual(parent.id, "sub1");
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "2");
                    },
                });
            }
        }

        await mount(NestedSortable, target);

        assert.containsN(target, ".item", 6);
        assert.verifySteps([]);

        const movedEl = target.querySelector(".sortable_list > .item:nth-child(2)");
        const { drop, moveTo } = await drag(movedEl);
        await moveTo(movedEl, { x: movedEl.getBoundingClientRect().width / 2 + 15 });
        await moveTo(movedEl, { x: movedEl.getBoundingClientRect().width / 2 + 30 });
        // No move if row is already child
        await drop(movedEl, { x: movedEl.getBoundingClientRect().width / 2 + 45 });

        assert.containsN(target, ".item", 6);
        assert.verifySteps(["start", "move 1", "move 2", "drop", "end"]);
    });

    QUnit.test("Sorting with nesting - move left", async (assert) => {
        assert.expect(21);

        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <ul class="sortable_list">
                        <li class="item" id="parent">
                            <span>parent</span>
                            <ul>
                                <li class="item" id="sub1">
                                    <span>sub1</span>
                                    <ul>
                                        <li class="item" id="dragged">
                                            <span>dragged</span>
                                        </li>
                                    </ul>
                                </li>
                                <li class="item" id="sub2">
                                    <span>sub2</span>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    nest: true,
                    nestInterval: 20,
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "dragged");
                    },
                    onMove({ element, previous, next, parent, prevPos }) {
                        assert.step("move");
                        assert.strictEqual(element.id, "dragged");
                        assert.strictEqual(previous.id, "sub1");
                        assert.strictEqual(next.id, "sub2");
                        assert.strictEqual(parent.id, "parent");
                        assert.strictEqual(prevPos.previous.id, "dragged");
                        assert.notOk(prevPos.next);
                        assert.strictEqual(prevPos.parent.id, "sub1");
                    },
                    onDrop({ element, previous, next, parent }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "dragged");
                        assert.strictEqual(previous.id, "sub1");
                        assert.strictEqual(next.id, "sub2");
                        assert.strictEqual(parent.id, "parent");
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "dragged");
                    },
                });
            }
        }

        await mount(NestedSortable, target);

        assert.containsN(target, ".item", 4);
        assert.verifySteps([]);

        const movedEl = target.querySelector(".item#dragged");
        const { drop, moveTo } = await drag(movedEl);
        // No move if distance traveled is smaller than the nest interval
        await moveTo(movedEl, { x: movedEl.getBoundingClientRect().width / 2 - 10 });
        await moveTo(movedEl, { x: movedEl.getBoundingClientRect().width / 2 - 20 });
        // No move if there is one element before and one after
        await drop(movedEl, { x: movedEl.getBoundingClientRect().width / 2 - 40 });

        assert.containsN(target, ".item", 4);
        assert.verifySteps(["start", "move", "drop", "end"]);
    });

    QUnit.test("Sorting with nesting - move root down", async (assert) => {
        assert.expect(28);

        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <ul class="sortable_list">
                        <li class="item" id="dragged">
                            <span>dragged</span>
                        </li>
                        <li class="item" id="noChild">
                            <span>noChild</span>
                        </li>
                        <li class="item" id="parent">
                            <span>parent</span>
                            <ul>
                                <li class="item" id="child">
                                    <span>item</span>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    nest: true,
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "dragged");
                        this.firstMove = true;
                    },
                    onMove({ element, previous, next, parent, prevPos }) {
                        if (this.firstMove) {
                            assert.step("move 1");
                            assert.strictEqual(element.id, "dragged");
                            assert.strictEqual(previous.id, "noChild");
                            assert.strictEqual(next.id, "parent");
                            assert.notOk(parent);
                            assert.strictEqual(prevPos.previous.id, "dragged");
                            assert.strictEqual(prevPos.next.id, "noChild");
                            assert.notOk(prevPos.parent);
                            this.firstMove = false;
                        } else {
                            assert.step("move 2");
                            assert.strictEqual(element.id, "dragged");
                            assert.notOk(previous);
                            assert.strictEqual(next.id, "child");
                            assert.strictEqual(parent.id, "parent");
                            assert.strictEqual(prevPos.previous.id, "noChild");
                            assert.strictEqual(prevPos.next.id, "parent");
                            assert.notOk(prevPos.parent);
                        }
                    },
                    onDrop({ element, previous, next, parent }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "dragged");
                        assert.notOk(previous);
                        assert.strictEqual(next.id, "child");
                        assert.strictEqual(parent.id, "parent");
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "dragged");
                    },
                });
            }
        }

        await mount(NestedSortable, target);
        assert.verifySteps([]);

        const { drop, moveUnder } = await sortableDrag(".item#dragged");
        await moveUnder(".item#noChild");
        // Move under the content of the row, not under the rows nested inside the row
        await moveUnder(".item#parent > span");
        await drop();

        assert.containsN(target, ".item", 4);
        assert.verifySteps(["start", "move 1", "move 2", "drop", "end"]);
    });

    QUnit.test("Sorting with nesting - move child down", async (assert) => {
        assert.expect(28);

        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <ul class="sortable_list">
                        <li class="item" id="parent">
                            <span>parent</span>
                            <ul>
                                <li class="item" id="dragged">
                                    <span>dragged</span>
                                </li>
                                <li class="item" id="child">
                                    <span>item</span>
                                </li>
                            </ul>
                        </li>
                        <li class="item" id="noChild">
                            <span>noChild</span>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    nest: true,
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "dragged");
                        this.firstMove = true;
                    },
                    onMove({ element, previous, next, parent, prevPos }) {
                        if (this.firstMove) {
                            assert.step("move 1");
                            assert.strictEqual(element.id, "dragged");
                            assert.strictEqual(previous.id, "child");
                            assert.notOk(next);
                            assert.strictEqual(parent.id, "parent");
                            assert.strictEqual(prevPos.previous.id, "dragged");
                            assert.strictEqual(prevPos.next.id, "child");
                            assert.strictEqual(prevPos.parent.id, "parent");
                            this.firstMove = false;
                        } else {
                            assert.step("move 2");
                            assert.strictEqual(element.id, "dragged");
                            assert.strictEqual(previous.id, "noChild");
                            assert.notOk(next);
                            assert.notOk(parent);
                            assert.strictEqual(prevPos.previous.id, "child");
                            assert.notOk(prevPos.next);
                            assert.strictEqual(prevPos.parent.id, "parent");
                        }
                    },
                    onDrop({ element, previous, next, parent }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "dragged");
                        assert.strictEqual(previous.id, "noChild");
                        assert.notOk(next);
                        assert.notOk(parent);
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "dragged");
                    },
                });
            }
        }

        await mount(NestedSortable, target);
        assert.verifySteps([]);

        const { drop, moveUnder } = await sortableDrag(".item#dragged");
        await moveUnder(".item#child");
        await moveUnder(".item#noChild");
        await drop();

        assert.containsN(target, ".item", 4);
        assert.verifySteps(["start", "move 1", "move 2", "drop", "end"]);
    });

    QUnit.test("Sorting with nesting - move root up", async (assert) => {
        assert.expect(28);
        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <ul class="sortable_list">
                        <li class="item" id="parent">
                            <span>parent</span>
                            <ul>
                                <li class="item" id="child">
                                    <span>child</span>
                                </li>
                            </ul>
                        </li>
                        <li class="item" id="noChild">
                            <span>noChild</span>
                        </li>
                        <li class="item" id="dragged">
                            <span>dragged</span>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    nest: true,
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "dragged");
                        this.firstMove = true;
                    },
                    onMove({ element, previous, next, parent, prevPos }) {
                        if (this.firstMove) {
                            assert.step("move 1");
                            assert.strictEqual(element.id, "dragged");
                            assert.strictEqual(previous.id, "parent");
                            assert.strictEqual(next.id, "noChild");
                            assert.notOk(parent);
                            assert.strictEqual(prevPos.previous.id, "dragged");
                            assert.notOk(prevPos.next);
                            assert.notOk(prevPos.parent);
                            this.firstMove = false;
                        } else {
                            assert.step("move 2");
                            assert.strictEqual(element.id, "dragged");
                            assert.notOk(previous);
                            assert.strictEqual(next.id, "child");
                            assert.strictEqual(parent.id, "parent");
                            assert.strictEqual(prevPos.previous.id, "parent");
                            assert.strictEqual(prevPos.next.id, "noChild");
                            assert.notOk(prevPos.parent);
                        }
                    },
                    onDrop({ element, previous, next, parent }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "dragged");
                        assert.notOk(previous);
                        assert.strictEqual(next.id, "child");
                        assert.strictEqual(parent.id, "parent");
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "dragged");
                    },
                });
            }
        }

        await mount(NestedSortable, target);
        assert.verifySteps([]);

        const { drop, moveAbove } = await sortableDrag(".item#dragged");
        await moveAbove(".item#noChild");
        await moveAbove(".item#child");
        await drop();

        assert.containsN(target, ".item", 4);
        assert.verifySteps(["start", "move 1", "move 2", "drop", "end"]);
    });

    QUnit.test("Sorting with nesting - move child up", async (assert) => {
        assert.expect(28);

        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root">
                    <ul class="sortable_list">
                        <li class="item" id="parent">
                            <span>parent</span>
                            <ul>
                                <li class="item" id="child">
                                    <span>child</span>
                                </li>
                                <li class="item" id="dragged">
                                    <span>dragged</span>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    nest: true,
                    onDragStart({ element }) {
                        assert.step("start");
                        assert.strictEqual(element.id, "dragged");
                        this.firstMove = true;
                    },
                    onMove({ element, previous, next, parent, prevPos }) {
                        if (this.firstMove) {
                            assert.step("move 1");
                            assert.strictEqual(element.id, "dragged");
                            assert.notOk(previous);
                            assert.strictEqual(next.id, "child");
                            assert.strictEqual(parent.id, "parent");
                            assert.strictEqual(prevPos.previous.id, "dragged");
                            assert.notOk(prevPos.next);
                            assert.strictEqual(prevPos.parent.id, "parent");
                            this.firstMove = false;
                        } else {
                            assert.step("move 2");
                            assert.strictEqual(element.id, "dragged");
                            assert.notOk(previous);
                            assert.strictEqual(next.id, "parent");
                            assert.notOk(parent);
                            assert.notOk(prevPos.previous);
                            assert.strictEqual(prevPos.next.id, "child");
                            assert.strictEqual(prevPos.parent.id, "parent");
                        }
                    },
                    onDrop({ element, previous, next, parent }) {
                        assert.step("drop");
                        assert.strictEqual(element.id, "dragged");
                        assert.notOk(previous);
                        assert.strictEqual(next.id, "parent");
                        assert.notOk(parent);
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "dragged");
                    },
                });
            }
        }

        await mount(NestedSortable, target);
        assert.verifySteps([]);

        const { drop, moveAbove } = await sortableDrag(".item#dragged");
        await moveAbove(".item#child");
        await moveAbove(".item#parent");
        await drop();

        assert.containsN(target, ".item", 3);
        assert.verifySteps(["start", "move 1", "move 2", "drop", "end"]);
    });

    QUnit.test("Dynamically disable NestedSortable feature", async (assert) => {
        assert.expect(4);

        const state = reactive({ enableNestedSortable: true });
        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>
            `;

            setup() {
                this.state = useState(state);
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    enable: () => this.state.enableNestedSortable,
                    onDragStart() {
                        assert.step("start");
                    },
                });
            }
        }

        await mount(NestedSortable, target);

        assert.verifySteps([]);

        await dragAndDrop(".item:first-child", ".item:last-child");
        // Drag should have occurred
        assert.verifySteps(["start"]);

        state.enableNestedSortable = false;
        await nextTick();

        await dragAndDrop(".item:first-child", ".item:last-child");

        // Drag shouldn't have occurred
        assert.verifySteps([]);
    });

    QUnit.test(
        "Drag has a default tolerance of 10 pixels before initiating the dragging",
        async (assert) => {
            assert.expect(3);

            class NestedSortable extends Component {
                static template = xml`
                    <div t-ref="root" class="root">
                        <ul class="list">
                            <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                        </ul>
                    </div>
                `;

                setup() {
                    useNestedSortable({
                        ref: useRef("root"),
                        elements: ".item",
                        onDragStart() {
                            assert.step("Initiation of the drag sequence");
                        },
                    });
                }
            }

            await mount(NestedSortable, target);

            // Move the element from only 5 pixels
            const listItem = target.querySelector(".item:first-child");
            const { drop, moveTo } = await drag(listItem);
            await moveTo(listItem, {
                x: listItem.getBoundingClientRect().width / 2,
                y: listItem.getBoundingClientRect().height / 2 + 5,
            });
            assert.verifySteps([], "No drag sequence should have been initiated");

            // Move the element from more than 10 pixels
            await moveTo(listItem, {
                x: listItem.getBoundingClientRect().width / 2,
                y: listItem.getBoundingClientRect().height / 2 + 10,
            });
            assert.verifySteps(
                ["Initiation of the drag sequence"],
                "A drag sequence should have been initiated"
            );
            await drop();
        }
    );

    QUnit.test("shouldn't drag above max level", async (assert) => {
        assert.expect(6);
        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li class="item" id="parent">
                            <span>parent</span>
                        </li>
                        <li class="item" id="dragged">
                            <span>dragged</span>
                            <ul>
                                <li class="item" id="child">
                                    <span>child</span>
                                </li>
                            </ul>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    nest: true,
                    maxLevels: 2,
                    onDragStart() {
                        assert.step("start");
                    },
                    onMove() {
                        assert.step("move");
                    },
                    onDrop() {
                        assert.step("drop");
                    },
                    onDragEnd({ element }) {
                        assert.step("end");
                        assert.strictEqual(element.id, "dragged");
                        assert.notOk(element.parentElement.closest("#parent"));
                        assert.containsOnce(target, ".o_nested_sortable_placeholder.d-none");
                    },
                });
            }
        }

        await mount(NestedSortable, target);

        // cant move draggable under parent
        const draggedNode = target.querySelector(".item#dragged");
        const { drop, moveTo } = await drag(draggedNode);
        await moveTo("#parent", "right");
        await drop();
        assert.verifySteps(["start", "end"]);
    });

    QUnit.test("shouldn't drag when not allowed", async (assert) => {
        assert.expect(7);
        target.style.top = "1px";
        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li class="item" id="target">
                            <span>item</span>
                        </li>
                        <li class="item" id="dragged">
                            <span>dragged</span>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                let firstAllowedCheck = true;
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    isAllowed() {
                        assert.step("allowed_check");
                        if (firstAllowedCheck) {
                            // 1st check is used by internal nested_sortable hooks "onMove"
                            firstAllowedCheck = false;
                            assert.containsNone(target, ".o_nested_sortable_placeholder.d-none");
                        } else {
                            // 2e check is used by internal nested_sortable hooks "onDrop"
                            assert.containsOnce(target, ".o_nested_sortable_placeholder.d-none");
                        }
                        return false;
                    },
                    onDragStart() {
                        assert.step("start");
                    },
                    onMove() {
                        assert.step("move");
                    },
                    onDrop() {
                        assert.step("drop");
                    },
                    onDragEnd() {
                        assert.step("end");
                    },
                });
            }
        }

        await mount(NestedSortable, target);

        const draggedNode = target.querySelector(".item#dragged");
        const { drop, moveTo } = await drag(draggedNode);
        await moveTo("#target", "right");
        await drop();
        assert.verifySteps(["start", "allowed_check", "allowed_check", "end"]);
    });

    QUnit.test("placeholder and drag element have same size", async (assert) => {
        assert.expect(5);
        target.style.top = "1px";
        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li class="item" id="target">
                            <span>parent</span>
                        </li>
                        <li class="item" id="dragged">
                            <span>dragged</span>
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    useElementSize: true,
                    onDrop({ element, placeholder }) {
                        assert.strictEqual(element.id, "dragged");
                        assert.strictEqual(placeholder.id, "dragged");
                        assert.ok(
                            placeholder.classList.contains("o_nested_sortable_placeholder_realsize")
                        );
                        assert.notOk(
                            placeholder.classList.contains("o_nested_sortable_placeholder")
                        );
                        assert.strictEqual(
                            element.getBoundingClientRect().height,
                            placeholder.getBoundingClientRect().height
                        );
                    },
                });
            }
        }

        await mount(NestedSortable, target);
        const draggedNode = target.querySelector(".item#dragged");
        const { drop, moveTo } = await drag(draggedNode);
        await moveTo("#target", "right");
        await drop();
    });

    QUnit.test("Ignore specified elements", async (assert) => {
        assert.expect(6);

        class NestedSortable extends Component {
            static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" class="item">
                            <span class="ignored" t-esc="i" />
                            <span class="not-ignored" t-esc="i" />
                        </li>
                    </ul>
                </div>
            `;

            setup() {
                useNestedSortable({
                    ref: useRef("root"),
                    elements: ".item",
                    ignore: ".ignored",
                    onDragStart() {
                        assert.step("drag");
                    },
                });
            }
        }

        await mount(NestedSortable, target);

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
