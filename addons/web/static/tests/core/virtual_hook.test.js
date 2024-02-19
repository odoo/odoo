import { beforeEach, expect, mountOnFixture, test } from "@odoo/hoot";
import { resize, scroll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, useRef, xml } from "@odoo/owl";
import { useVirtual } from "@web/core/virtual_hook";
import { patchWithCleanup } from "../web_test_helpers";

/**
 * @typedef ItemType
 * @property {number} id
 *
 * @typedef {import("@web/core/virtual_hook").VirtualHookParams<ItemType>} TestComponentProps
 */

function objectToStyle(obj) {
    return Object.entries(obj)
        .map(([k, v]) => `${k}: ${v};`)
        .join("");
}

/** @type {ItemType[]} */
const ITEMS = Array.from({ length: 200 }, (_, i) => ({ id: i + 1 }));
const ITEM_HEIGHT = 50;
const ITEM_STYLE = objectToStyle({
    height: `${ITEM_HEIGHT}px`,
    width: "100%",
    border: "1px solid black",
    position: "absolute",
    "background-color": "white",
});
const CONTAINER_SIZE = 5 * ITEM_HEIGHT;
const CONTAINER_STYLE = objectToStyle({
    height: `${CONTAINER_SIZE}px`,
    width: "100%",
    overflow: "auto",
    position: "relative",
    "background-color": "lightblue",
});
const MAX_SCROLL_TOP = ITEMS.length * ITEM_HEIGHT - CONTAINER_SIZE;

/**
 * @param {TestComponentProps} [props]
 */
async function mountTestComponent(props) {
    /** @extends {Component<ItemType, any>} **/
    class Item extends Component {
        static props = ["id"];
        static template = xml`
            <div class="item" t-att-data-id="props.id" t-att-style="style" t-esc="props.id"/>
        `;
        get style() {
            return `top: ${(this.props.id - 1) * ITEM_HEIGHT}px; ${ITEM_STYLE}`;
        }
    }

    /** @extends {Component<TestComponentProps, any>} **/
    class TestComponent extends Component {
        static props = ["getItems?", "scrollableRef?", "initialScroll?", "getItemHeight?"];
        static components = { Item };
        static template = xml`
            <div class="scrollable" t-ref="scrollable" style="${CONTAINER_STYLE}">
                <div class="inner" t-att-style="innerStyle">
                    <t t-foreach="items" t-as="item" t-key="item.id">
                        <Item id="item.id"/>
                    </t>
                </div>
            </div>
        `;
        setup() {
            const scrollableRef = useRef("scrollable");
            this.items = useVirtual({
                getItems: () => ITEMS,
                getItemHeight: () => ITEM_HEIGHT,
                scrollableRef,
                ...this.props,
            });
        }
        get innerStyle() {
            return `height: ${ITEMS.length * ITEM_HEIGHT}px;`;
        }
    }
    await mountOnFixture(TestComponent, { props });
}

beforeEach(() => {
    // In this test suite, we trick the hook by setting the window size to the size
    // of the scrollable, so that it is a measurable size and this suite can run
    // in a window of any size.
    patchWithCleanup(window, { innerHeight: CONTAINER_SIZE });
});

test("basic usage", async () => {
    await mountTestComponent();
    expect(".item").toHaveCount(11);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "1");
    expect(".item:last-child").toHaveAttribute("data-id", "11");

    // scroll to the middle
    scroll(".scrollable", { top: MAX_SCROLL_TOP / 2 });
    await animationFrame();
    expect(".item").toHaveCount(16);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "93");
    expect(".item:last-child").toHaveAttribute("data-id", "108");

    // scroll to the end
    scroll(".scrollable", { top: MAX_SCROLL_TOP });
    await animationFrame();
    expect(".item").toHaveCount(11);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "190");
    expect(".item:last-child").toHaveAttribute("data-id", "200");
});

test("updates on resize", async () => {
    await mountTestComponent();
    expect(".item").toHaveCount(11);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "1");
    expect(".item:last-child").toHaveAttribute("data-id", "11");

    // resize the window
    patchWithCleanup(window, { innerHeight: CONTAINER_SIZE / 2 });
    resize(window);
    await animationFrame();
    expect(".item").toHaveCount(6);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "1");
    expect(".item:last-child").toHaveAttribute("data-id", "6");

    // resize the window
    patchWithCleanup(window, { innerHeight: CONTAINER_SIZE * 2 });
    resize(window);
    await animationFrame();
    expect(".item").toHaveCount(21);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "1");
    expect(".item:last-child").toHaveAttribute("data-id", "21");
});

test("initialScroll: middle", async () => {
    const initialScroll = { top: MAX_SCROLL_TOP / 2 };
    await mountTestComponent({ initialScroll });
    expect(".item").toHaveCount(16);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "93");
    expect(".item:last-child").toHaveAttribute("data-id", "108");
});

test("initialScroll: bottom", async () => {
    const initialScroll = { top: MAX_SCROLL_TOP };
    await mountTestComponent({ initialScroll });
    expect(".item").toHaveCount(11);
    expect(".item:nth-child(1)").toHaveAttribute("data-id", "190");
    expect(".item:last-child").toHaveAttribute("data-id", "200");
});
