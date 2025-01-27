import { expect, test } from "@odoo/hoot";
import { queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { advanceFrame, animationFrame } from "@odoo/hoot-mock";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Component, reactive, useRef, useState, xml } from "@odoo/owl";
import { useSortable } from "@web/core/utils/sortable_owl";

test("Parameters error handling", async () => {
    const mountListAndAssert = async (setupList) => {
        class List extends Component {
            static props = ["*"];
            static template = xml`
                    <div t-ref="root" class="root">
                        <ul class="list">
                            <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                        </ul>
                    </div>`;
            setup() {
                setupList();
            }
        }

        await mountWithCleanup(List);
    };

    // Incorrect params
    await mountListAndAssert(() => {
        expect(() => useSortable({})).toThrow(
            `Error in hook useSortable: missing required property "ref" in parameter`
        );
    });
    await mountListAndAssert(() => {
        expect(() =>
            useSortable({
                elements: ".item",
            })
        ).toThrow(`Error in hook useSortable: missing required property "ref" in parameter`);
    });
    await mountListAndAssert(() => {
        expect(() =>
            useSortable({
                elements: ".item",
                groups: ".list",
            })
        ).toThrow(`Error in hook useSortable: missing required property "ref" in parameter`);
    });

    // Correct params
    await mountListAndAssert(() => {
        useSortable({
            ref: useRef("root"),
        });
    });
    await mountListAndAssert(() => {
        useSortable({
            ref: {},
            elements: ".item",
            enable: false,
        });
    });
    await mountListAndAssert(() => {
        useSortable({
            ref: useRef("root"),
            elements: ".item",
            connectGroups: () => true,
        });
    });
});

test("Simple sorting in single group", async () => {
    expect.assertions(18);

    class List extends Component {
        static props = ["*"];
        static template = xml`
            <div t-ref="root" class="root">
                <ul class="list">
                    <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                </ul>
            </div>`;
        setup() {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                onDragStart({ element, group }) {
                    expect.step("start");
                    expect(group).toBe(undefined);
                    expect(element).toHaveText("1");
                },
                onElementEnter({ element }) {
                    expect.step("elemententer");
                    expect(element).toHaveText("2");
                },
                onDragEnd({ element, group }) {
                    expect.step("end");
                    expect(group).toBe(undefined);
                    expect(element).toHaveText("1");
                    expect(".item").toHaveCount(4);
                    expect(".item.o_dragged").toHaveCount(1);
                },
                onDrop({ element, group, previous, next, parent }) {
                    expect.step("drop");
                    expect(group).toBe(undefined);
                    expect(element).toHaveText("1");
                    expect(previous).toHaveText("2");
                    expect(next).toHaveText("3");
                    expect(parent).toBe(null);
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
    expect.verifySteps(["start", "elemententer", "drop", "end"]);
});

test("Simple sorting in multiple groups", async () => {
    expect.assertions(16);

    class List extends Component {
        static props = ["*"];
        static template = xml`
                <div t-ref="root" class="root">
                    <ul t-foreach="[1, 2, 3]" t-as="l" t-key="l" t-attf-class="list p-3 list{{ l }}">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="l + ' ' + i" class="item" />
                    </ul>
                </div>`;
        setup() {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                groups: ".list",
                connectGroups: true,
                onDragStart({ element, group }) {
                    expect.step("start");
                    expect(group).toHaveClass("list2");
                    expect(element).toHaveText("2 1");
                },
                onGroupEnter({ group }) {
                    expect.step("groupenter");
                    expect(group).toHaveClass("list1");
                },
                onDragEnd({ element, group }) {
                    expect.step("end");
                    expect(group).toHaveClass("list2");
                    expect(element).toHaveText("2 1");
                },
                onDrop({ element, group, previous, next, parent }) {
                    expect.step("drop");
                    expect(group).toHaveClass("list2");
                    expect(element).toHaveText("2 1");
                    expect(previous).toHaveText("1 3");
                    expect(next).toBe(null);
                    expect(parent).toHaveClass("list1");
                },
            });
        }
    }

    await mountWithCleanup(List, { noMainContainer: true });

    expect(".list").toHaveCount(3);
    expect(".item").toHaveCount(9);
    expect.verifySteps([]);

    // First item of 2nd list appended to first list
    await contains(".list2 .item:first-child").dragAndDrop(".list1");

    expect(".list").toHaveCount(3);
    expect(".item").toHaveCount(9);
    expect.verifySteps(["start", "groupenter", "drop", "end"]);
});

test("Sorting in groups with distinct per-axis scrolling", async () => {
    /**
     * @param {string} selector
     * @param {{ x?: number; y?: number }} position
     * @param {() => any} callback
     */
    const dragAndExpect = async (selector, position, callback) => {
        const { drop, moveTo } = await contains(selector).drag();
        await moveTo(`${selector}:last`, { position });
        // Wait for the edge scrolling to scroll to the end
        await advanceFrame(50);

        callback();

        await drop();

        queryFirst(".scroll_parent_y").scrollTop = 0;
        queryFirst(".root").scrollLeft = 0;
    };

    class List extends Component {
        static props = ["*"];
        static template = xml`
            <div style="left:0;top:0; position: fixed; width: 100%; height: 100%;">
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
            </div>
            `;
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

    await mountWithCleanup(List);

    expect(".list").toHaveCount(3);
    expect(".item").toHaveCount(9);

    // Negative horizontal scrolling

    queryFirst(".spacer_horizontal").scrollIntoView({ behavior: "instant" });
    queryFirst(".root").scrollLeft = 16;
    expect(".root").toHaveProperty("scrollLeft", 16, {
        message: "Negative horizontal scrolling: scrollLeft",
    });
    expect(".scroll_parent_y").toHaveProperty("scrollTop", 50, {
        message: "Negative horizontal scrolling: scrollTop",
    });

    await dragAndExpect(".item12", { x: 0 }, () => {
        expect(".scroll_parent_y").toHaveProperty("scrollTop", 50, {
            message: "Negative horizontal scrolling left - scrollTop",
        });
        expect(".root").toHaveProperty("scrollLeft", 0, {
            message: "Negative horizontal scrolling left - scrollLeft",
        });
    });

    expect(".o_dragged").toHaveCount(0);

    // Positive horizontal scrolling

    queryFirst(".spacer_horizontal").scrollIntoView({ behavior: "instant" });
    expect(".root").toHaveProperty("scrollLeft", 0, {
        message: "Positive horizontal scrolling - scrollLeft",
    });
    expect(".scroll_parent_y").toHaveProperty("scrollTop", 50, {
        message: "Positive horizontal scrolling - scrollTop",
    });

    await dragAndExpect(".item11", { x: 1000 }, () => {
        expect(".scroll_parent_y").toHaveProperty("scrollTop", 50, {
            message: "Positive horizontal scrolling right - scrollTop",
        });
        expect(".root").toHaveProperty("scrollLeft", 75, {
            message: "Positive horizontal scrolling right - scrollLeft",
        });
    });

    expect(".o_dragged").toHaveCount(0);

    // Negative vertical scrolling

    queryFirst(".root").scrollIntoView({ behavior: "instant" });
    queryFirst(".root").scrollLeft = 16;
    expect(".root").toHaveProperty("scrollLeft", 16, {
        message: "Negative vertical scrolling - scrollLeft",
    });
    expect(".scroll_parent_y").toHaveProperty("scrollTop", 100, {
        message: "Negative vertical scrolling - scrollTop",
    });

    await dragAndExpect(".item11", { y: 0 }, () => {
        expect(".scroll_parent_y").toHaveProperty("scrollTop", 0, {
            message: "Negative vertical scrolling top - scrollTop",
        });
        expect(".root").toHaveProperty("scrollLeft", 16, {
            message: "Negative vertical scrolling top - scrollLeft",
        });
    });

    expect(".o_dragged").toHaveCount(0);

    // Positive vertical scrolling

    queryFirst(".spacer_before").scrollIntoView({ behavior: "instant" });
    queryFirst(".root").scrollLeft = 16;
    expect(".root").toHaveProperty("scrollLeft", 16, {
        message: "Positive vertical scrolling - scrollLeft",
    });
    expect(".scroll_parent_y").toHaveProperty("scrollTop", 0, {
        message: "Positive vertical scrolling - scrollTop",
    });

    await dragAndExpect(".item21", { y: 1000 }, () => {
        expect(".scroll_parent_y").toHaveProperty("scrollTop", 215, {
            message: "Positive vertical scrolling bottom - scrollTop",
        });
        expect(".root").toHaveProperty("scrollLeft", 16, {
            message: "Positive vertical scrolling bottom - scrollLeft",
        });
    });

    expect(".o_dragged").toHaveCount(0);
});

test("draggable area contains overflowing visible elements", async () => {
    class List extends Component {
        static props = ["*"];
        static template = xml`
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
        setup() {
            useSortable({
                ref: useRef("renderer"),
                elements: ".item",
                groups: ".list",
                connectGroups: true,
                touchDelay: 0,
            });
        }
    }

    await mountWithCleanup(List);

    const controller = queryFirst(".controller");
    const content = queryFirst(".content");
    const renderer = queryFirst(".renderer");

    expect(content).toHaveProperty("scrollLeft", 0);
    expect(controller.getBoundingClientRect().width).toBe(900);
    expect(content.getBoundingClientRect().width).toBe(600);
    expect(renderer.getBoundingClientRect().width).toBe(600);
    expect(renderer).toHaveProperty("scrollWidth", 900);
    expect(".item.o_dragged").toHaveCount(0);

    const { cancel, moveTo } = await contains(".item11").drag();

    // Drag first record of first group to the right
    await moveTo(".list3 .item:first");

    // Verify that there is no scrolling
    expect(content).toHaveProperty("scrollLeft", 0);
    expect(".item.o_dragged").toHaveCount(1);

    // Verify that the dragged element is allowed to go inside the
    // overflowing part of the draggable container.
    expect(".item.o_dragged").toHaveRect({ right: 900 });
    expect(".list3 .item:first").toHaveRect({ right: 900 });

    // Cancel drag
    await cancel();

    expect(".item.o_dragged").toHaveCount(0);
});

test("Dynamically disable sortable feature", async () => {
    expect.assertions(3);

    const state = reactive({ enableSortable: true });
    class List extends Component {
        static props = ["*"];
        static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>`;
        setup() {
            this.state = useState(state);
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                enable: () => this.state.enableSortable,
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

    state.enableSortable = false;
    await animationFrame();

    // First item before last item
    await contains(".item:first-child").dragAndDrop(".item:last-child");

    // Drag shouldn't have occurred
    expect.verifySteps([]);
});

test("Drag has a default tolerance of 10 pixels before initiating the dragging", async () => {
    expect.assertions(2);

    class List extends Component {
        static props = ["*"];
        static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>`;

        setup() {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                onDragStart() {
                    expect.step("Initiation of the drag sequence");
                },
            });
        }
    }

    await mountWithCleanup(List);

    const listItem = queryFirst(".item");
    const { cancel, moveTo } = await contains(listItem).drag({
        initialPointerMoveDistance: 0,
        position: { x: 0, y: 0 }, // Move the element from only 5 pixels
        relative: true,
    });
    await moveTo(listItem, {
        position: { x: 0, y: 5 },
        relative: true,
    });

    expect.verifySteps([]);

    await moveTo(listItem, {
        position: { x: 10, y: 10 }, // Move the element from more than 10 pixels
        relative: true,
    });

    expect.verifySteps(["Initiation of the drag sequence"]);

    await cancel();
});

test("Ignore specified elements", async () => {
    expect.assertions(4);

    class List extends Component {
        static props = ["*"];
        static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" class="item">
                            <span class="ignored" t-esc="i" />
                            <span class="not-ignored" t-esc="i" />
                        </li>
                    </ul>
                </div>`;
        setup() {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                ignore: ".ignored",
                onDragStart() {
                    expect.step("drag");
                },
            });
        }
    }

    await mountWithCleanup(List);

    expect.verifySteps([]);

    // Drag root item element
    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps(["drag"]);

    // Drag ignored element
    await contains(".item:first-child .not-ignored").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps(["drag"]);

    // Drag non-ignored element
    await contains(".item:first-child .ignored").dragAndDrop(".item:nth-child(2)");

    expect.verifySteps([]);
});

test("the classes parameters (placeholderElement, helpElement)", async () => {
    expect.assertions(7);

    let dragElement;

    class List extends Component {
        static props = ["*"];
        static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>`;
        setup() {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                placeholderClasses: ["placeholder-t1", "placeholder-t2"],
                followingElementClasses: ["add-1", "add-2"],
                onDragStart({ element }) {
                    dragElement = element;
                    expect(dragElement).toHaveClass("add-1");
                    expect(dragElement).toHaveClass("add-2");
                    // the placeholder is added in onDragStart after the current element
                    const children = [...dragElement.parentElement.children];
                    const placeholder = children[children.indexOf(dragElement) + 1];
                    expect(placeholder).toHaveClass("placeholder-t1");
                    expect(placeholder).toHaveClass("placeholder-t2");
                },
            });
        }
    }

    await mountWithCleanup(List);
    // First item after 2nd item
    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");
    expect(dragElement).not.toHaveClass("add-1");
    expect(dragElement).not.toHaveClass("add-2");
    expect(".item.placeholder-t1.placeholder-t2").toHaveCount(0);
});

test("applyChangeOnDrop option", async () => {
    expect.assertions(2);

    class List extends Component {
        static props = ["*"];
        static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>`;
        setup() {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                placeholderClasses: ["placeholder"],
                applyChangeOnDrop: true,
                onDragStart() {
                    expect(queryAllTexts(".item:not(.placeholder)")).toEqual(["1", "2", "3"]);
                },
                onDrop() {
                    expect(queryAllTexts(".item:not(.placeholder)")).toEqual(["2", "1", "3"]);
                },
            });
        }
    }

    await mountWithCleanup(List);
    // First item after 2nd item
    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");
});

test("clone option", async () => {
    expect.assertions(2);

    class List extends Component {
        static props = ["*"];
        static template = xml`
                <div t-ref="root" class="root">
                    <ul class="list">
                        <li t-foreach="[1, 2, 3]" t-as="i" t-key="i" t-esc="i" class="item" />
                    </ul>
                </div>`;
        setup() {
            useSortable({
                ref: useRef("root"),
                elements: ".item",
                placeholderClasses: ["placeholder"],
                clone: false,
                onDragStart() {
                    expect(".placeholder:not(.item)").toHaveCount(1);
                },
            });
        }
    }

    await mountWithCleanup(List);
    // First item after 2nd item
    await contains(".item:first-child").dragAndDrop(".item:nth-child(2)");
    expect(".placeholder:not(.item)").toHaveCount(0);
});
