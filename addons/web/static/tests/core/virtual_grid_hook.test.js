import { after, beforeEach, expect, test } from "@odoo/hoot";
import { resize, scroll } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, computed, effect, props, signal, types as t, xml } from "@odoo/owl";
import { defineParams, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { range } from "@web/core/utils/numbers";
import { useVirtualGrid } from "@web/core/virtual_grid_hook";

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
const CONTAINER_HEIGHT = 5 * ITEM_HEIGHT; // 5 rows
const CONTAINER_WIDTH = 10 * ITEM_WIDTH; // 10 columns
const CONTAINER_STYLE = objectToStyle({
    height: `${CONTAINER_HEIGHT}px`,
    width: `${CONTAINER_WIDTH}px`,
    overflow: "auto",
    position: "relative",
    "background-color": "lightblue",
});
const MAX_SCROLL_TOP = ROW_COUNT * ITEM_HEIGHT - CONTAINER_HEIGHT;
const MAX_SCROLL_LEFT = COLUMN_COUNT * ITEM_WIDTH - CONTAINER_WIDTH;

class TestGridItem extends Component {
    static template = xml`
        <div
            class="item"
            t-att-data-row-id="this.props.row"
            t-att-data-col-id="this.props.col"
            t-attf-style="
                top: {{ this.props.row - 1 * ${ITEM_HEIGHT} }}px;
                left: {{ this.props.col - 1 * ${ITEM_WIDTH} }}px;
                ${ITEM_STYLE}
            "
        >
            <t t-out="this.props.row" />|<t t-out="this.props.col" />
        </div>
    `;

    props = props({
        col: t.number(),
        row: t.number(),
    });
}

class TestGridComponent extends Component {
    static components = { TestGridItem };
    static template = xml`
        <div class="scrollable" t-ref="this.virtualGrid.ref" style="${CONTAINER_STYLE}" t-att-dir="this.direction">
            <div class="inner" style="height: ${ROW_COUNT * ITEM_HEIGHT}px; width: ${COLUMN_COUNT * ITEM_WIDTH}px;">
                <t t-foreach="this.virtualRows()" t-as="row" t-key="row">
                    <t t-foreach="this.virtualColumns()" t-as="col" t-key="col">
                        <TestGridItem row="row" col="col" />
                    </t>
                </t>
            </div>
        </div>
    `;

    props = props();
    direction = localization.direction;

    virtualGrid = useVirtualGrid({
        ...this.props,
        rowHeights: Array(ROW_COUNT).fill(ITEM_HEIGHT),
        columnWidths: Array(COLUMN_COUNT).fill(ITEM_WIDTH),
    });

    virtualColumns = computed(() =>
        range(1, COLUMN_COUNT + 1).slice(
            this.virtualGrid.firstColumn(),
            this.virtualGrid.lastColumn() + 1
        )
    );

    virtualRows = computed(() =>
        range(1, ROW_COUNT + 1).slice(this.virtualGrid.firstRow(), this.virtualGrid.lastRow() + 1)
    );
}

// In this test suite, we trick the hook by setting the window size to the size
// of the scrollable, so that it is a measurable size and this suite can run
// in a window of any size.
beforeEach(() => resize({ height: CONTAINER_HEIGHT, width: CONTAINER_WIDTH }));

test("basic usage", async () => {
    const { virtualGrid } = await mountWithCleanup(TestGridComponent);

    expect(virtualGrid.firstRow()).toBe(0);
    expect(virtualGrid.lastRow()).toBe(9);
    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(19);

    // scroll to the middle
    await scroll(".scrollable", { top: MAX_SCROLL_TOP / 2, left: MAX_SCROLL_LEFT / 2 });
    await animationFrame();

    expect(virtualGrid.firstRow()).toBe(92);
    expect(virtualGrid.lastRow()).toBe(107);
    expect(virtualGrid.firstColumn()).toBe(85);
    expect(virtualGrid.lastColumn()).toBe(114);

    // // scroll to bottom right
    await scroll(".scrollable", { top: MAX_SCROLL_TOP, left: MAX_SCROLL_LEFT });
    await animationFrame();

    expect(virtualGrid.firstRow()).toBe(190);
    expect(virtualGrid.lastRow()).toBe(199);
    expect(virtualGrid.firstColumn()).toBe(180);
    expect(virtualGrid.lastColumn()).toBe(199);
});

test("updates on resize", async () => {
    const { virtualGrid } = await mountWithCleanup(TestGridComponent);

    expect(virtualGrid.firstRow()).toBe(0);
    expect(virtualGrid.lastRow()).toBe(9);
    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(19);

    // resize the window
    await resize({ height: CONTAINER_HEIGHT / 2, width: CONTAINER_WIDTH / 2 });
    await runAllTimers();

    expect(virtualGrid.firstRow()).toBe(0);
    expect(virtualGrid.lastRow()).toBe(4);
    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(9);

    // resize the window
    await resize({ height: CONTAINER_HEIGHT * 2, width: CONTAINER_WIDTH * 2 });
    await runAllTimers();

    expect(virtualGrid.firstRow()).toBe(0);
    expect(virtualGrid.lastRow()).toBe(19);
    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(39);
});

test("initialScroll: middle", async () => {
    const { virtualGrid } = await mountWithCleanup(TestGridComponent, {
        props: {
            initialScroll: { top: MAX_SCROLL_TOP / 2, left: MAX_SCROLL_LEFT / 2 },
        },
    });

    expect(virtualGrid.firstRow()).toBe(92);
    expect(virtualGrid.lastRow()).toBe(107);
    expect(virtualGrid.firstColumn()).toBe(85);
    expect(virtualGrid.lastColumn()).toBe(114);
});

test("initialScroll: bottom right", async () => {
    const { virtualGrid } = await mountWithCleanup(TestGridComponent, {
        props: {
            initialScroll: { top: MAX_SCROLL_TOP, left: MAX_SCROLL_LEFT },
        },
    });

    expect(virtualGrid.firstRow()).toBe(190);
    expect(virtualGrid.lastRow()).toBe(199);
    expect(virtualGrid.firstColumn()).toBe(180);
    expect(virtualGrid.lastColumn()).toBe(199);
});

test("required params only", async () => {
    class C extends Component {
        static template = xml`
            <div class="scrollable" t-ref="this.virtualGrid.ref"
        />`;

        virtualGrid = useVirtualGrid({ scrollableRef });
    }

    const scrollableRef = signal.ref();
    const { virtualGrid } = await mountWithCleanup(C);

    expect(virtualGrid.ref()).toBe(scrollableRef());
    expect(scrollableRef()).toHaveClass("scrollable");

    expect(virtualGrid.firstRow()).toBe(null);
    expect(virtualGrid.lastRow()).toBe(null);
    expect(virtualGrid.firstColumn()).toBe(null);
    expect(virtualGrid.lastColumn()).toBe(null);
});

test("with empty rows and columns", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="this.virtualGrid.ref" />
        `;

        virtualGrid = useVirtualGrid({
            rowHeights: [],
            columnWidths: [],
        });
    }

    const { virtualGrid } = await mountWithCleanup(C);

    expect(virtualGrid.firstRow()).toBe(null);
    expect(virtualGrid.lastRow()).toBe(null);
    expect(virtualGrid.firstColumn()).toBe(null);
    expect(virtualGrid.lastColumn()).toBe(null);
});

test("with 1 row and 1 column", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="this.virtualGrid.ref" />
        `;

        virtualGrid = useVirtualGrid({
            rowHeights: [1],
            columnWidths: [1],
        });
    }

    const { virtualGrid } = await mountWithCleanup(C);

    expect(virtualGrid.firstRow()).toBe(0);
    expect(virtualGrid.lastRow()).toBe(0);
    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(0);
});

test("with columns only", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="this.virtualGrid.ref" />
        `;

        virtualGrid = useVirtualGrid({
            columnWidths: Array(100).fill(1),
        });
    }

    const { virtualGrid } = await mountWithCleanup(C);

    expect(virtualGrid.firstRow()).toBe(null);
    expect(virtualGrid.lastRow()).toBe(null);
    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(99);
});

test("with rows only", async () => {
    class C extends Component {
        static template = xml`
            <div t-ref="this.virtualGrid.ref" />
        `;

        virtualGrid = useVirtualGrid({
            rowHeights: Array(100).fill(1),
        });
    }

    const { virtualGrid } = await mountWithCleanup(C);

    expect(virtualGrid.firstRow()).toBe(0);
    expect(virtualGrid.lastRow()).toBe(99);
    expect(virtualGrid.firstColumn()).toBe(null);
    expect(virtualGrid.lastColumn()).toBe(null);
});

test("react to individual virtual grid changes", async () => {
    const { virtualGrid } = await mountWithCleanup(TestGridComponent);

    // FIXME: currently, effects order is inverted for computed * computed
    // values: https://github.com/odoo/owl/issues/1983
    after(effect(() => expect.step("firstRow: " + virtualGrid.firstRow())));
    after(effect(() => expect.step("lastRow: " + virtualGrid.lastRow())));
    after(effect(() => expect.step("firstColumn: " + virtualGrid.firstColumn())));
    after(effect(() => expect.step("lastColumn: " + virtualGrid.lastColumn())));

    // Effect calls steps immediatly
    expect.verifySteps(["firstRow: 0", "lastRow: 9", "firstColumn: 0", "lastColumn: 19"]);

    // called on scroll
    await scroll(".scrollable", { top: MAX_SCROLL_TOP / 2, left: MAX_SCROLL_LEFT / 2 });
    await animationFrame();

    expect.verifySteps(["lastColumn: 114", "firstColumn: 85", "lastRow: 107", "firstRow: 92"]);

    // but it is not if the scroll is too small
    await scroll(".scrollable", {
        top: MAX_SCROLL_TOP / 2 + Number.EPSILON,
        left: MAX_SCROLL_LEFT / 2 + Number.EPSILON,
    });
    await animationFrame();

    expect.verifySteps([]);

    // it can also receive the changed indexes of a single direction
    await scroll(".scrollable", { top: MAX_SCROLL_TOP });
    await animationFrame();

    expect.verifySteps(["lastRow: 199", "firstRow: 190"]);

    // called on resize
    await resize({ height: CONTAINER_HEIGHT / 2, width: CONTAINER_WIDTH / 2 });
    await runAllTimers();

    expect.verifySteps([
        "firstColumn: 90",
        "lastColumn: 104",
        /** `lastRow` didn't change */
        "firstRow: 192",
    ]);

    // but it is not if the resize is too small
    await resize({
        height: CONTAINER_HEIGHT / 2 + Number.EPSILON,
        width: CONTAINER_WIDTH / 2 + Number.EPSILON,
    });
    await runAllTimers();

    expect.verifySteps([]);

    // it can also receive the changed indexes of a single direction
    await resize({ width: CONTAINER_WIDTH * 2 });
    await runAllTimers();

    expect.verifySteps(["lastColumn: 134", "firstColumn: 75"]);
});

test("when scrolling to the bottom right then updating to smaller rows and columns", async () => {
    const { virtualGrid } = await mountWithCleanup(TestGridComponent);

    await scroll(".scrollable", { top: MAX_SCROLL_TOP, left: MAX_SCROLL_LEFT });
    await animationFrame();

    expect(virtualGrid.firstRow()).toBe(190);
    expect(virtualGrid.lastRow()).toBe(199);
    expect(virtualGrid.firstColumn()).toBe(180);
    expect(virtualGrid.lastColumn()).toBe(199);

    virtualGrid.setRowHeights([1, 2, 3]);
    virtualGrid.setColumnWidths([1, 2, 3]);

    expect(virtualGrid.firstRow()).toBe(0);
    expect(virtualGrid.lastRow()).toBe(2);
    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(2);
});

test("horizontal scroll in RTL", async () => {
    // Please note that if you debug this test, the applied style of elements
    // is not adapted to RTL. The test is still valid because we only want to
    // assert the returned indexes of the virtual grid.
    defineParams({
        lang_parameters: {
            direction: "rtl",
        },
    });

    const { virtualGrid } = await mountWithCleanup(TestGridComponent);

    expect(virtualGrid.firstColumn()).toBe(0);
    expect(virtualGrid.lastColumn()).toBe(19);

    // scroll to the middle
    await scroll(".scrollable", { left: -MAX_SCROLL_LEFT / 2 });
    await animationFrame();

    expect(virtualGrid.firstColumn()).toBe(85);
    expect(virtualGrid.lastColumn()).toBe(114);

    // scroll to left
    await scroll(".scrollable", { left: -MAX_SCROLL_LEFT });
    await animationFrame();

    expect(virtualGrid.firstColumn()).toBe(180);
    expect(virtualGrid.lastColumn()).toBe(199);
});
