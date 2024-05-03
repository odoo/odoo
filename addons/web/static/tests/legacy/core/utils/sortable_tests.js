/** @odoo-module alias=@web/../tests/core/utils/sortable_tests default=false */

import {
    drag,
    getFixture,
    mockAnimationFrame,
    mount,
    nextTick,
} from "@web/../tests/helpers/utils";
import { useSortable } from "@web/core/utils/sortable_owl";

import { Component, useRef, xml } from "@odoo/owl";

let target;
QUnit.module("Draggable", ({ beforeEach }) => {
    beforeEach(() => (target = getFixture()));

    QUnit.module("Sortable hook");

    QUnit.test("Sorting in groups with distinct per-axis scrolling", async (assert) => {
        const { advanceFrame } = mockAnimationFrame();
        class List extends Component {
            static props = ["*"];
            static template = xml`
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
        assertScrolling(50, 1);
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
});
