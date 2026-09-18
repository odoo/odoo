import { describe, expect, getFixture, test } from "@odoo/hoot";
import {
    animationFrame,
    manuallyDispatchProgrammaticEvent,
    queryOne,
    queryRect,
    scroll,
} from "@odoo/hoot-dom";
import {
    setupInteractionWhiteList,
    startInteractions,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.bottom_fixed_element");

describe.current.tags("interaction_dev");

const scrollTo = async function (el, scrollTarget, bottomFixedElement) {
    await scroll(el, { y: scrollTarget });
    bottomFixedElement.style.position = "absolute";
    bottomFixedElement.style.top = scrollTarget + "px";
    bottomFixedElement.style.left = `calc(50% - ${queryRect(bottomFixedElement).width / 2}px)`;
    await manuallyDispatchProgrammaticEvent(document, "scroll");
    await animationFrame();
};

const scrollToMiddle = async function (el, bottomFixedElement) {
    await scrollTo(
        el,
        2550 / 2 - queryRect(bottomFixedElement).height,
        bottomFixedElement,
    );
};

const scrollToBottom = async function (el, bottomFixedElement) {
    await scrollTo(el, 2550 - queryRect(bottomFixedElement).height, bottomFixedElement);
};

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
};

test("bottom_fixed_element is started when there is an element #wrapwrap", async () => {
    const { core } = await startInteractions(getTemplate());
    expect(core.interactions).toHaveLength(1);
});

test("show button fixed element when over no button (0 button)", async () => {
    await startInteractions(
        getTemplate({ withButtonCenter: false, withButtonLeft: false }),
    );
    const fixture = getFixture();
    fixture.style.overflowY = "scroll";
    const bottomFixedElement = queryOne(".o_bottom_fixed_element");
    await scrollToMiddle(fixture, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(fixture, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
});

test("show button fixed element when over no button (1 button)", async () => {
    await startInteractions(
        getTemplate({ withButtonCenter: false, withButtonLeft: true }),
    );
    const fixture = getFixture();
    fixture.style.overflowY = "scroll";
    const bottomFixedElement = queryOne(".o_bottom_fixed_element");
    await scrollToMiddle(fixture, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(fixture, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
});

test("hide button fixed element when over one button (1 button)", async () => {
    await startInteractions(
        getTemplate({ withButtonCenter: true, withButtonLeft: false }),
    );
    const fixture = getFixture();
    fixture.style.overflowY = "scroll";
    const bottomFixedElement = queryOne(".o_bottom_fixed_element");
    await scrollToMiddle(fixture, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(fixture, bottomFixedElement);
    expect(bottomFixedElement).toHaveClass("o_bottom_fixed_element_hidden");
});

test("hide button fixed element when over one button (2 buttons)", async () => {
    await startInteractions(
        getTemplate({ withButtonCenter: true, withButtonLeft: true }),
    );
    const fixture = getFixture();
    fixture.style.overflowY = "scroll";
    const bottomFixedElement = queryOne(".o_bottom_fixed_element");
    await scrollToMiddle(fixture, bottomFixedElement);
    expect(bottomFixedElement).not.toHaveClass("o_bottom_fixed_element_hidden");
    await scrollToBottom(fixture, bottomFixedElement);
    expect(bottomFixedElement).toHaveClass("o_bottom_fixed_element_hidden");
});
