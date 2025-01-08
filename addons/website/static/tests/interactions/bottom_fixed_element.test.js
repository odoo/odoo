import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { scroll } from "@odoo/hoot-dom";

setupInteractionWhiteList("website.bottom_fixed_element");

describe.current.tags("interaction_dev");

const scrollTo = async function (el, scrollTarget, bottomFixedElement) {
    // Simulate the scroll event
    await scroll(el, { y: scrollTarget });
    // Replace the bottomFixedElement at the bottom of the page
    bottomFixedElement.style.position = "absolute";
    bottomFixedElement.style.top = scrollTarget + "px";
    bottomFixedElement.style.left = `calc(50% - ${bottomFixedElement.getBoundingClientRect().width / 2}px)`;
    // Dispatch the scroll event
    document.dispatchEvent(new Event("scroll"));
}

const scrollToMiddle = async function (el, bottomFixedElement) {
    // 2550 = headerHeight + mainHeight + footerHeight
    await scrollTo(el, 2550 / 2 - bottomFixedElement.getBoundingClientRect().height, bottomFixedElement)
}

const scrollToBottom = async function (el, bottomFixedElement) {
    // 2550 = headerHeight + mainHeight + footerHeight
    await scrollTo(el, 2550 - bottomFixedElement.getBoundingClientRect().height, bottomFixedElement)
}

const getTemplate = function (options = {}) {
    const withButtonLeft = options.withButtonLeft || false;
    const withButtonCenter = options.withButtonCenter || false;

    const emptyDiv = `<div style="height: 50px; width: 150px;"></div>`;
    const buttonEl = `<a href="#" style="background-color: white; border: solid; height: 50px; width: 150px;"></a>`;

    return `
        <header style="height: 50px; background-color: #CCCCFF;"></header>
        <main style="height: 2000px; background-color: #CCFFCC;">
            <div class="o_bottom_fixed_element" style="height: 100px; width: 100px; background-color: black;"></div>
        </main>
        <footer style="height: 500px; background-color: #FFCCCC; display: flex; justify-content: space-between; align-items: end;">
            ${withButtonLeft ? buttonEl : emptyDiv}
            ${withButtonCenter ? buttonEl : emptyDiv}
            ${emptyDiv}
        </footer>
    `;
}

test("bottom_fixed_element is started when there is an element #wrapwrap", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions).toHaveLength(1);
});

test("show button fixed element when over no button (0 button)", async () => {
    const { el } = await startInteractions(getTemplate({ withButtonCenter: false, withButtonLeft: false }));
    el.style.overflowY = "scroll";
    const bottomFixedElement = el.querySelector(".o_bottom_fixed_element");
    await scrollToMiddle(el, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(el, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
});

test("show button fixed element when over no button (1 button)", async () => {
    const { el } = await startInteractions(getTemplate({ withButtonCenter: false, withButtonLeft: true }));
    el.style.overflowY = "scroll";
    const bottomFixedElement = el.querySelector(".o_bottom_fixed_element");
    await scrollToMiddle(el, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(el, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
});

test("hide button fixed element when over one button (1 button)", async () => {
    const { el } = await startInteractions(getTemplate({ withButtonCenter: true, withButtonLeft: false }));
    el.style.overflowY = "scroll";
    const bottomFixedElement = el.querySelector(".o_bottom_fixed_element");
    await scrollToMiddle(el, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(el, bottomFixedElement);
    expect(bottomFixedElement).toHaveClass("o_bottom_fixed_element_hidden");
});

test("hide button fixed element when over one button (2 buttons)", async () => {
    const { el } = await startInteractions(getTemplate({ withButtonCenter: true, withButtonLeft: true }));
    el.style.overflowY = "scroll";
    const bottomFixedElement = el.querySelector(".o_bottom_fixed_element");
    await scrollToMiddle(el, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(el, bottomFixedElement);
    expect(bottomFixedElement).toHaveClass("o_bottom_fixed_element_hidden");
});
