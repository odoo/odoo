/** @odoo-module **/

import { dragAndDrop, getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { useSortable } from "@web/core/utils/ui";
import { LegacyComponent } from "@web/legacy/legacy_component";

const { useRef, useState, xml } = owl;

let target;
QUnit.module("UI", ({ beforeEach }) => {
    beforeEach(() => {
        target = getFixture();
    });

    QUnit.module("Sortable");

    QUnit.test("Parameters error handling", async (assert) => {
        assert.expect(8);

        const mountListAndAssert = async (setupList, shouldThrow) => {
            class List extends LegacyComponent {
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
                setup: () => ({ items: ".item" }),
            });
        }, true);
        await mountListAndAssert(() => {
            useSortable({
                setup: () => ({
                    items: ".item",
                    lists: ".list",
                }),
            });
        }, true);
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
                items: ".item",
            });
        }, true);

        // Correct params
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
                setup: () => false,
            });
        }, false);
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
                setup: () => ({}),
            });
        }, false);
        await mountListAndAssert(() => {
            useSortable({
                ref: useRef("root"),
                setup: () => ({ items: ".item" }),
            });
        }, false);
    });

    QUnit.test("Simple sorting in single list", async (assert) => {
        assert.expect(19);

        class List extends LegacyComponent {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    setup: () => ({
                        items: ".item",
                    }),
                    onStart(list, item) {
                        assert.step("start");
                        assert.notOk(list);
                        assert.strictEqual(item.innerText, "1");
                    },
                    onItemEnter(item) {
                        assert.step("itementer");
                        assert.strictEqual(item.innerText, "2");
                    },
                    onStop(list, item) {
                        assert.step("stop");
                        assert.notOk(list);
                        assert.strictEqual(item.innerText, "1");
                        assert.containsN(target, ".item", 4);
                    },
                    onDrop({ list, item, previous, next, parent }) {
                        assert.step("drop");
                        assert.notOk(list);
                        assert.strictEqual(item.innerText, "1");
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
        assert.verifySteps(["start", "itementer", "stop", "drop"]);
    });

    QUnit.test("Simple sorting in multiple lists", async (assert) => {
        assert.expect(20);

        class List extends LegacyComponent {
            setup() {
                useSortable({
                    ref: useRef("root"),
                    setup: () => ({
                        items: ".item",
                        lists: ".list",
                        connectLists: true,
                    }),
                    onStart(list, item) {
                        assert.step("start");
                        assert.hasClass(list, "list2");
                        assert.strictEqual(item.innerText, "2 1");
                    },
                    onListEnter(list) {
                        assert.step("listenter");
                        assert.hasClass(list, "list1");
                    },
                    onStop(list, item) {
                        assert.step("stop");
                        assert.hasClass(list, "list2");
                        assert.strictEqual(item.innerText, "2 1");
                    },
                    onDrop({ list, item, previous, next, parent }) {
                        assert.step("drop");
                        assert.hasClass(list, "list2");
                        assert.strictEqual(item.innerText, "2 1");
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
        assert.verifySteps(["start", "listenter", "stop", "drop"]);
    });

    QUnit.test("Dynamically disable sortable feature", async (assert) => {
        assert.expect(4);

        class List extends LegacyComponent {
            setup() {
                this.state = useState({ enableSortable: true });
                useSortable({
                    ref: useRef("root"),
                    setup: () =>
                        this.state.enableSortable && {
                            items: ".item",
                        },
                    onStart() {
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

        const list = await mount(List, target);

        assert.verifySteps([]);

        // First item before last item
        await dragAndDrop(".item:first-child", ".item:last-child");

        // Drag should have occurred
        assert.verifySteps(["start"]);

        list.state.enableSortable = false;
        await nextTick();

        // First item before last item
        await dragAndDrop(".item:first-child", ".item:last-child");

        // Drag shouldn't have occurred
        assert.verifySteps([]);
    });
});
