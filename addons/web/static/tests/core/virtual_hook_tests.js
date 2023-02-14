/** @odoo-module **/

import { Component, useRef, xml } from "@odoo/owl";
import { useVirtual } from "@web/core/virtual_hook";
import { getFixture, mount, patchWithCleanup, triggerEvent } from "../helpers/utils";

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
 * @param {HTMLElement} [target]
 * @param {TestComponentProps} [props]
 */
async function mountTestComponent(target, props) {
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
    await mount(TestComponent, target, { props });
}

function scroll(target, scrollTop) {
    target.querySelector(".scrollable").scrollTop = scrollTop;
    return triggerEvent(target, ".scrollable", "scroll");
}

let target;
QUnit.module("useVirtual hook", {
    async beforeEach() {
        target = getFixture();
        // In this test suite, we trick the hook by setting the window size to the size
        // of the scrollable, so that it is a measurable size and this suite can run
        // in a window of any size.
        patchWithCleanup(window, { innerHeight: CONTAINER_SIZE });
    },
});

QUnit.test("basic usage", async (assert) => {
    await mountTestComponent(target);
    assert.containsN(target, ".item", 11);
    assert.strictEqual(target.querySelector(".item").dataset.id, "1");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "11");

    // scroll to the middle
    await scroll(target, MAX_SCROLL_TOP / 2);
    assert.containsN(target, ".item", 16);
    assert.strictEqual(target.querySelector(".item").dataset.id, "93");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "108");

    // scroll to the end
    await scroll(target, MAX_SCROLL_TOP);
    assert.containsN(target, ".item", 11);
    assert.strictEqual(target.querySelector(".item").dataset.id, "190");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "200");
});

QUnit.test("updates on resize", async (assert) => {
    await mountTestComponent(target);
    assert.containsN(target, ".item", 11);
    assert.strictEqual(target.querySelector(".item").dataset.id, "1");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "11");

    // resize the window
    patchWithCleanup(window, { innerHeight: CONTAINER_SIZE / 2 });
    await triggerEvent(window, null, "resize");
    assert.containsN(target, ".item", 6);
    assert.strictEqual(target.querySelector(".item").dataset.id, "1");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "6");

    // resize the window
    patchWithCleanup(window, { innerHeight: CONTAINER_SIZE * 2 });
    await triggerEvent(window, null, "resize");
    assert.containsN(target, ".item", 21);
    assert.strictEqual(target.querySelector(".item").dataset.id, "1");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "21");
});

QUnit.test("initialScroll: middle", async (assert) => {
    const initialScroll = { top: MAX_SCROLL_TOP / 2 };
    await mountTestComponent(target, { initialScroll });
    assert.containsN(target, ".item", 16);
    assert.strictEqual(target.querySelector(".item").dataset.id, "93");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "108");
});

QUnit.test("initialScroll: bottom", async (assert) => {
    const initialScroll = { top: MAX_SCROLL_TOP };
    await mountTestComponent(target, { initialScroll });
    assert.containsN(target, ".item", 11);
    assert.strictEqual(target.querySelector(".item").dataset.id, "190");
    assert.strictEqual(target.querySelector(".item:last-child").dataset.id, "200");
});
