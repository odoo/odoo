// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import { resize, scroll } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, useRef, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { useVirtualGrid } from "@web/core/utils/virtual_grid";

function objectToStyle(obj) {
    return Object.entries(obj)
        .map(([k, v]) => `${k}: ${v};`)
        .join("");
}

const ROW_COUNT = 200;
const COLUMN_COUNT = 200;
const ITEM_HEIGHT = 50;
const ITEM_WIDTH = 50;
const ITEM_STYLE = objectToStyle({
    height: `${ITEM_HEIGHT}px`,
    width: `${ITEM_WIDTH}px`,
    border: "1px solid black",
    position: "absolute",
    "background-color": "white",
});
const CONTAINER_HEIGHT = 5 * ITEM_HEIGHT;
const CONTAINER_WIDTH = 10 * ITEM_WIDTH;
const CONTAINER_STYLE = objectToStyle({
    height: "100%",
    width: "100%",
    overflow: "auto",
    "scrollbar-width": "none",
    position: "relative",
    "background-color": "lightblue",
});
const MAX_SCROLL_TOP = ROW_COUNT * ITEM_HEIGHT - CONTAINER_HEIGHT;
const MAX_SCROLL_LEFT = COLUMN_COUNT * ITEM_WIDTH - CONTAINER_WIDTH;

/**
 * @param {Partial<import("@web/core/utils/virtual_grid").VirtualGridParams>} [virtualGridParams]
 */
function getTestComponent(virtualGridParams) {
    class Item extends Component {
        static props = ["row", "col"];
        static template = xml`
            <div class="item" t-att-data-row-id="this.props.row.id" t-att-data-col-id="this.props.col.id" t-att-style="this.style" t-out="this.content"/>
        `;
        get content() {
            return `${this.props.row.id}|${this.props.col.id}`;
        }
        get style() {
            return `top: ${(this.props.row.id - 1) * ITEM_HEIGHT}px; left: ${
                (this.props.col.id - 1) * ITEM_WIDTH
            }px; ${ITEM_STYLE}`;
        }
    }

    class TestComponent extends Component {
        static props = [];
        static components = { Item };
        static template = xml`
            <div class="scrollable" t-ref="scrollable" style="${CONTAINER_STYLE}" dir="${localization.direction}">
                <div class="inner" t-att-style="innerStyle">
                    <t t-foreach="virtualRows" t-as="row" t-key="row.id">
                        <t t-foreach="virtualColumns" t-as="col" t-key="col.id">
                            <Item row="row" col="col"/>
                        </t>
                    </t>
                </div>
            </div>
        `;
        setup() {
            const scrollableRef = useRef("scrollable");
            this.virtualGrid = useVirtualGrid({
                scrollableRef,
                ...virtualGridParams,
            });
            this.virtualGrid.setRowsHeights(
                Array.from({ length: ROW_COUNT }, () => ITEM_HEIGHT),
            );
            this.virtualGrid.setColumnsWidths(
                Array.from({ length: COLUMN_COUNT }, () => ITEM_WIDTH),
            );
        }
        get innerStyle() {
            return `height: ${ROW_COUNT * ITEM_HEIGHT}px; width: ${COLUMN_COUNT * ITEM_WIDTH}px;`;
        }
        get virtualRows() {
            const [rowStart, rowEnd] = this.virtualGrid.rowsIndexes;
            return Array.from({ length: ROW_COUNT }, (_, i) => ({ id: i + 1 })).slice(
                rowStart,
                rowEnd + 1,
            );
        }
        get virtualColumns() {
            const [colStart, colEnd] = this.virtualGrid.columnsIndexes;
            return Array.from({ length: COLUMN_COUNT }, (_, i) => ({
                id: i + 1,
            })).slice(colStart, colEnd + 1);
        }
    }
    return TestComponent;
}

beforeEach(async () => {
    patchWithCleanup(localization, { direction: "ltr" });

    await resize({ height: CONTAINER_HEIGHT, width: CONTAINER_WIDTH });
});

test("basic usage", async () => {
    const comp = await mountWithCleanup(getTestComponent());
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 9]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 19]);

    await scroll(".scrollable", { top: MAX_SCROLL_TOP / 2, left: MAX_SCROLL_LEFT / 2 });
    await animationFrame();
    expect(comp.virtualGrid.rowsIndexes).toEqual([92, 107]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([85, 114]);

    await scroll(".scrollable", { top: MAX_SCROLL_TOP, left: MAX_SCROLL_LEFT });
    await animationFrame();
    expect(comp.virtualGrid.rowsIndexes).toEqual([190, 199]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([180, 199]);
});

test("visible span derives from the scrollable pane, not the window", async () => {
    await resize({ height: CONTAINER_HEIGHT * 4, width: CONTAINER_WIDTH * 4 });
    class C extends Component {
        static template = xml`
            <div class="pane" t-ref="scrollable"
                style="height: ${CONTAINER_HEIGHT}px; width: ${CONTAINER_WIDTH}px; overflow: auto; scrollbar-width: none;">
                <div style="height: ${ROW_COUNT * ITEM_HEIGHT}px; width: ${COLUMN_COUNT * ITEM_WIDTH}px;"/>
            </div>
        `;
        static props = [];
        setup() {
            const scrollableRef = useRef("scrollable");
            this.virtualGrid = useVirtualGrid({ scrollableRef });
        }
    }
    const comp = await mountWithCleanup(C);
    comp.virtualGrid.setRowsHeights(
        Array.from({ length: ROW_COUNT }, () => ITEM_HEIGHT),
    );
    comp.virtualGrid.setColumnsWidths(
        Array.from({ length: COLUMN_COUNT }, () => ITEM_WIDTH),
    );
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 9]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 19]);
});

test("updates on resize", async () => {
    const comp = await mountWithCleanup(getTestComponent());
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 9]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 19]);

    await resize({ height: CONTAINER_HEIGHT / 2, width: CONTAINER_WIDTH / 2 });
    await runAllTimers();
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 4]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 9]);

    await resize({ height: CONTAINER_HEIGHT * 2, width: CONTAINER_WIDTH * 2 });
    await runAllTimers();
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 19]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 39]);
});

test("initialScroll: middle", async () => {
    const initialScroll = { top: MAX_SCROLL_TOP / 2, left: MAX_SCROLL_LEFT / 2 };
    const comp = await mountWithCleanup(getTestComponent({ initialScroll }));
    expect(comp.virtualGrid.rowsIndexes).toEqual([92, 107]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([85, 114]);
});

test("initialScroll: bottom right", async () => {
    const initialScroll = { top: MAX_SCROLL_TOP, left: MAX_SCROLL_LEFT };
    const comp = await mountWithCleanup(getTestComponent({ initialScroll }));
    expect(comp.virtualGrid.rowsIndexes).toEqual([190, 199]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([180, 199]);
});

test("required params only", async () => {
    class C extends Component {
        static template = xml`<div t-ref="pseudoScrollable"/>`;
        static props = [];
        setup() {
            const scrollableRef = useRef("pseudoScrollable");
            this.virtualGrid = useVirtualGrid({ scrollableRef });
        }
    }
    const comp = await mountWithCleanup(C);
    expect(comp.virtualGrid.rowsIndexes).toBe(undefined);
    expect(comp.virtualGrid.columnsIndexes).toBe(undefined);
});

test("with empty rows and columns", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="pseudoScrollable"/>
        `;
        static props = [];
        setup() {
            const scrollableRef = useRef("pseudoScrollable");
            this.virtualGrid = useVirtualGrid({ scrollableRef });
            this.virtualGrid.setRowsHeights([]);
            this.virtualGrid.setColumnsWidths([]);
        }
    }
    const comp = await mountWithCleanup(C);
    expect(comp.virtualGrid.rowsIndexes).toEqual([]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([]);
});

test("with 1 row and 1 column", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="pseudoScrollable"/>
        `;
        static props = [];
        setup() {
            const scrollableRef = useRef("pseudoScrollable");
            this.virtualGrid = useVirtualGrid({ scrollableRef });
            this.virtualGrid.setRowsHeights([1]);
            this.virtualGrid.setColumnsWidths([1]);
        }
    }
    const comp = await mountWithCleanup(C);
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 0]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 0]);
});

test("with columns only", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="pseudoScrollable"/>
        `;
        static props = [];
        setup() {
            const scrollableRef = useRef("pseudoScrollable");
            this.virtualGrid = useVirtualGrid({ scrollableRef });
            this.virtualGrid.setColumnsWidths(Array.from({ length: 100 }, () => 1));
        }
    }
    const comp = await mountWithCleanup(C);
    expect(comp.virtualGrid.rowsIndexes).toBe(undefined);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 99]);
});

test("with rows only", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="pseudoScrollable"/>
        `;
        static props = [];
        setup() {
            const scrollableRef = useRef("pseudoScrollable");
            this.virtualGrid = useVirtualGrid({ scrollableRef });
            this.virtualGrid.setRowsHeights(Array.from({ length: 100 }, () => 1));
        }
    }
    const comp = await mountWithCleanup(C);
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 99]);
    expect(comp.virtualGrid.columnsIndexes).toBe(undefined);
});

test("onChange", async () => {
    const C = getTestComponent({
        onChange: (changed) => {
            expect.step(changed);
        },
    });
    const comp = await mountWithCleanup(C);
    expect.verifySteps([]);

    await scroll(".scrollable", { top: MAX_SCROLL_TOP / 2, left: MAX_SCROLL_LEFT / 2 });
    await animationFrame();
    expect.verifySteps([{ columnsIndexes: [85, 114], rowsIndexes: [92, 107] }]);
    await scroll(".scrollable", {
        top: MAX_SCROLL_TOP / 2 + Number.EPSILON,
        left: MAX_SCROLL_LEFT / 2 + Number.EPSILON,
    });
    await animationFrame();
    expect.verifySteps([]);
    await scroll(".scrollable", { top: MAX_SCROLL_TOP });
    await animationFrame();
    expect.verifySteps([{ rowsIndexes: [190, 199] }]);

    await resize({ height: CONTAINER_HEIGHT / 2, width: CONTAINER_WIDTH / 2 });
    await runAllTimers();
    expect.verifySteps([{ columnsIndexes: [90, 104], rowsIndexes: [192, 199] }]);
    await resize({
        height: CONTAINER_HEIGHT / 2 + Number.EPSILON,
        width: CONTAINER_WIDTH / 2 + Number.EPSILON,
    });
    await runAllTimers();
    expect.verifySteps([]);
    await resize({ width: CONTAINER_WIDTH * 2 });
    await runAllTimers();
    expect.verifySteps([{ columnsIndexes: [75, 134] }]);

    const actualGrid = [comp.virtualGrid.rowsIndexes, comp.virtualGrid.columnsIndexes];
    comp.virtualGrid.setRowsHeights([1, 2, 3]);
    comp.virtualGrid.setColumnsWidths([1, 2, 3]);
    expect.verifySteps([]);
    expect([comp.virtualGrid.rowsIndexes, comp.virtualGrid.columnsIndexes]).not.toEqual(
        actualGrid,
    );
});

test("when scrolling to the bottom right then updating to smaller rows and columns", async () => {
    const comp = await mountWithCleanup(getTestComponent());
    await scroll(".scrollable", { top: MAX_SCROLL_TOP, left: MAX_SCROLL_LEFT });
    await animationFrame();
    expect(comp.virtualGrid.rowsIndexes).toEqual([190, 199]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([180, 199]);

    comp.virtualGrid.setRowsHeights([1, 2, 3]);
    comp.virtualGrid.setColumnsWidths([1, 2, 3]);
    expect(comp.virtualGrid.rowsIndexes).toEqual([0, 2]);
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 2]);
});

test("horizontal scroll in RTL", async () => {
    patchWithCleanup(localization, { direction: "rtl" });
    const comp = await mountWithCleanup(getTestComponent());
    expect(comp.virtualGrid.columnsIndexes).toEqual([0, 19]);

    await scroll(".scrollable", { left: -MAX_SCROLL_LEFT / 2 });
    await animationFrame();
    expect(comp.virtualGrid.columnsIndexes).toEqual([85, 114]);

    await scroll(".scrollable", { left: -MAX_SCROLL_LEFT });
    await animationFrame();
    expect(comp.virtualGrid.columnsIndexes).toEqual([180, 199]);
});

test("sub-deadband scroll jitter does not recompute the window", async () => {
    let changes = 0;
    const comp = await mountWithCleanup(
        getTestComponent({ onChange: () => changes++ }),
    );

    await scroll(".scrollable", { top: MAX_SCROLL_TOP });
    await animationFrame();
    const settled = comp.virtualGrid.rowsIndexes;
    changes = 0;

    for (let i = 0; i < 10; i++) {
        await scroll(".scrollable", { top: MAX_SCROLL_TOP - (i % 2) });
        await animationFrame();
    }

    expect(changes).toBe(0);
    expect(comp.virtualGrid.rowsIndexes).toEqual(settled);
});

test("scroll accumulating past the deadband still recomputes", async () => {
    let changes = 0;
    const comp = await mountWithCleanup(
        getTestComponent({ onChange: () => changes++ }),
    );

    await scroll(".scrollable", { top: 0 });
    await animationFrame();
    const before = comp.virtualGrid.rowsIndexes;
    changes = 0;

    for (let top = 3; top <= 120; top += 3) {
        await scroll(".scrollable", { top });
        await animationFrame();
    }

    expect(changes).toBeGreaterThan(0);
    expect(comp.virtualGrid.rowsIndexes).not.toEqual(before);
});
