// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryOne, queryRect } from "@odoo/hoot-dom";
import { Component, useRef, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { boxExtraWidth, useAutoresize } from "@web/core/utils/dom/autoresize";

class Sized extends Component {
    static template = xml`
        <div class="host" t-att-style="this.props.hostStyle">
            <input class="resizable" t-ref="input" t-att-style="this.props.inputStyle"/>
        </div>`;
    static props = ["*"];
    setup() {
        useAutoresize(useRef("input"));
    }
}

/**
 * @param {HTMLInputElement} el
 * @returns {number}
 */
function referenceTextWidth(el) {
    const span = document.createElement("span");
    const style = window.getComputedStyle(el);
    span.style.position = "absolute";
    span.style.visibility = "hidden";
    span.style.whiteSpace = "pre";
    for (const property of [
        "font-family",
        "font-size",
        "font-style",
        "font-weight",
        "font-stretch",
        "font-variant",
        "font-variant-numeric",
        "letter-spacing",
        "word-spacing",
    ]) {
        span.style.setProperty(property, style.getPropertyValue(property));
    }
    span.textContent = el.value;
    document.body.appendChild(span);
    const width = span.offsetWidth;
    span.remove();
    return width;
}

/**
 * @param {string} hostStyle
 * @param {string} inputStyle
 * @param {string} [text]
 */
async function assertMeasuredWithInputFont(hostStyle, inputStyle, text = "WWWWWWWWWW") {
    await mountWithCleanup(Sized, { props: { hostStyle, inputStyle } });
    await contains(`.resizable`).edit(text);
    const input = /** @type {HTMLInputElement} */ (queryOne(`.resizable`));
    const expected = referenceTextWidth(input);
    const measured = queryRect(`.resizable`).width - boxExtraWidth(input);
    expect(Math.abs(measured - expected)).toBeLessThan(2);
}

test("a container with a much smaller font does not shrink the box", async () => {
    await assertMeasuredWithInputFont(
        "font-family: monospace; font-size: 8px; width: 600px;",
        "font-family: monospace; font-size: 32px;",
    );
});

test("a container with a much larger font does not stretch the box", async () => {
    await assertMeasuredWithInputFont(
        "font-family: monospace; font-size: 40px; width: 600px;",
        "font-family: monospace; font-size: 11px;",
    );
});

test("letter-spacing on the input is accounted for", async () => {
    await assertMeasuredWithInputFont(
        "font-family: monospace; font-size: 14px; width: 600px;",
        "font-family: monospace; font-size: 14px; letter-spacing: 4px;",
    );
});

test("a numeric variant the container lacks is accounted for", async () => {
    await assertMeasuredWithInputFont(
        "font-family: monospace; font-size: 14px; width: 600px;",
        "font-family: serif; font-size: 14px; font-variant-numeric: tabular-nums;",
        "10.01 21.72 38.94",
    );
});

test("border-box padding and border do not clip the text", async () => {
    await mountWithCleanup(Sized, {
        props: {
            hostStyle: "width: 600px;",
            inputStyle:
                "box-sizing: border-box; padding: 0 12px; border: 2px solid black;",
        },
    });
    await contains(`.resizable`).edit("WWWWWWWWWW");
    const input = /** @type {HTMLInputElement} */ (queryOne(`.resizable`));
    const expected = referenceTextWidth(input) + boxExtraWidth(input);
    expect(Math.abs(queryRect(`.resizable`).width - expected)).toBeLessThan(2);
});
