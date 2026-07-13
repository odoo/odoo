import {
    isElementVerticallyInViewportOf,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryOne, scroll } from "@odoo/hoot-dom";

import { setupTest, simpleScroll, doubleScroll } from "./helpers";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList([
    "website.header_standard",
    "website.header_fixed",
    "website.header_disappears",
    "website.header_fade_out",
    "website.table_of_content",
]);

describe.current.tags("interaction_dev");

const wrapTableOfContent = (html) => {
    const content = html.innerHTML;
    html.innerHTML = `
        <div id="wrapwrap" style="overflow: scroll; max-height: 300px;">
            ${content}
        </div>
    `;
};

const addHeader = (headerType) => (html) => {
    const content = html.innerHTML;
    html.innerHTML = `
        <header class="${headerType}" style="background-color:#CCFFCC">
            <div style="height: 50px; background-color:#33FFCC;"></div>
        </header>
        <main>
            ${content}
        </main>
    `;
};

const HEADER_SIZE = 50;
const DEFAULT_OFFSET = 20;

const SCROLLS = [0, 40, 250, 400, 250, 40, 0];
const SCROLLS_SPECIAL = [0, 40, 400, 40, 0];

// This function only works if the elements are displayed
const checkVisibility = function (aEls, h2Els, wrapEl) {
    return [
        isElementVerticallyInViewportOf(aEls[0], wrapEl),
        isElementVerticallyInViewportOf(aEls[1], wrapEl),
        isElementVerticallyInViewportOf(h2Els[0], wrapEl),
        isElementVerticallyInViewportOf(h2Els[1], wrapEl),
    ];
};

test.tags("desktop");
test("table_of_content is correctly started (desktop)", async () => {
    const { core } = await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: wrapTableOfContent,
    });
    expect(core.interactions).toHaveLength(1);
    const wrapEl = queryOne("#wrapwrap");
    const aEls = queryAll("a[href]");
    const h2Els = queryAll("h2[id]");
    expect(aEls[0]).toHaveClass("active");
    expect(aEls[1]).not.toHaveClass("active");
    expect(checkVisibility(aEls, h2Els, wrapEl)).toEqual([true, true, true, false]);
});

test.tags("mobile");
test("table_of_content is correctly started (mobile)", async () => {
    const { core } = await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: wrapTableOfContent,
    });
    expect(core.interactions).toHaveLength(1);
    const wrapEl = queryOne("#wrapwrap");
    const aEls = queryAll("a[href]");
    const h2Els = queryAll("h2[id]");
    // We do not check the active class in mobile
    expect(checkVisibility(aEls, h2Els, wrapEl)).toEqual([true, true, true, false]);
});

test.tags("desktop");
test("table_of_content scrolls to targetted location (desktop)", async () => {
    await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: wrapTableOfContent,
    });
    const wrapEl = queryOne("#wrapwrap");
    const aEls = queryAll("a[href]");
    const h2Els = queryAll("h2[id]");
    await click(aEls[1]);
    await animationFrame();
    expect(aEls[0]).not.toHaveClass("active");
    expect(aEls[1]).toHaveClass("active");
    expect(checkVisibility(aEls, h2Els, wrapEl)).toEqual([true, true, false, true]);
});

test.tags("mobile");
test("table_of_content scrolls to targetted location (mobile)", async () => {
    await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: wrapTableOfContent,
    });
    const wrapEl = queryOne("#wrapwrap");
    const aEls = queryAll("a[href]");
    const h2Els = queryAll("h2[id]");
    await click(aEls[1]);
    await animationFrame();
    // We do not check the active class in mobile
    expect(checkVisibility(aEls, h2Els, wrapEl)).toEqual([true, true, false, true]);
});

test.tags("desktop");
test("table_of_content highlights reached header (desktop)", async () => {
    await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: wrapTableOfContent,
    });
    const wrapEl = queryOne("#wrapwrap");
    const aEls = queryAll("a[href]");
    const h2Els = queryAll("h2[id]");
    await scroll(wrapEl, { top: h2Els[1].getBoundingClientRect().top });
    await animationFrame();
    expect(aEls[0]).not.toHaveClass("active");
    expect(aEls[1]).toHaveClass("active");
    expect(checkVisibility(aEls, h2Els, wrapEl)).toEqual([true, true, false, true]);
});

test.tags("mobile");
test("table_of_content highlights reached header (mobile)", async () => {
    await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: wrapTableOfContent,
    });
    const wrapEl = queryOne("#wrapwrap");
    const aEls = queryAll("a[href]");
    const h2Els = queryAll("h2[id]");
    await scroll(wrapEl, { top: h2Els[1].getBoundingClientRect().top });
    await animationFrame();
    // We do not check the active class in mobile
    expect(checkVisibility(aEls, h2Els, wrapEl)).toEqual([true, true, false, true]);
});

test.tags("desktop");
test("table_of_content updates titles position with a o_header_standard", async () => {
    const { core } = await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: addHeader("o_header_standard"),
    });
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryOne(".s_table_of_content_navbar");
    await setupTest(core, wrapwrap);
    for (const target of SCROLLS) {
        await simpleScroll(wrapwrap, target);
        const calculatedTop = Math.round(parseFloat(title.style.top));
        const isHeaderVisible = target < HEADER_SIZE || target > 300;
        // We compensate the scroll since the header does not move in Hoot.
        const correctedTop = isHeaderVisible ? calculatedTop + target : calculatedTop;
        expect(correctedTop).toBe(isHeaderVisible ? HEADER_SIZE + DEFAULT_OFFSET : DEFAULT_OFFSET);
    }
});

test.tags("desktop");
test("table_of_content updates titles position with a o_header_fixed", async () => {
    const { core } = await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: addHeader("o_header_fixed"),
    });
    expect(core.interactions).toHaveLength(2);
    // We force the header to never be consider "atTop", so that its
    // position is properly computed.
    core.interactions[0].interaction.topGap = -1;
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryOne(".s_table_of_content_navbar");
    await setupTest(core, wrapwrap);
    for (const target of SCROLLS_SPECIAL) {
        await simpleScroll(wrapwrap, target);
        // There is no need to compensate the scroll here
        expect(Math.round(parseFloat(title.style.top))).toBe(HEADER_SIZE + DEFAULT_OFFSET);
    }
});

test.tags("desktop");
test("table_of_content updates titles position with a o_header_disappears", async () => {
    const { core } = await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: addHeader("o_header_disappears"),
    });
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryOne(".s_table_of_content_navbar");
    await setupTest(core, wrapwrap);
    for (let i = 1; i < SCROLLS_SPECIAL.length; i++) {
        const target = SCROLLS_SPECIAL[i];
        const source = SCROLLS_SPECIAL[i - 1];
        await doubleScroll(wrapwrap, target, source);
        const calculatedTop = Math.round(parseFloat(title.style.top));
        const isHeaderVisible = target < 300;
        // We compensate the scroll since the header does not move in Hoot.
        const correctedTop = isHeaderVisible ? calculatedTop + target : calculatedTop;
        expect(correctedTop).toBe(isHeaderVisible ? HEADER_SIZE + DEFAULT_OFFSET : DEFAULT_OFFSET);
    }
});

test.tags("desktop");
test("table_of_content updates titles position with a o_header_fade_out", async () => {
    const { core } = await startInteractionsWithSnippet("s_table_of_content", {
        processHTML: addHeader("o_header_fade_out"),
    });
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryOne(".s_table_of_content_navbar");
    await setupTest(core, wrapwrap);
    for (let i = 1; i < SCROLLS_SPECIAL.length; i++) {
        const target = SCROLLS_SPECIAL[i];
        const source = SCROLLS_SPECIAL[i - 1];
        await doubleScroll(wrapwrap, target, source);
        const calculatedTop = Math.round(parseFloat(title.style.top));
        const isHeaderVisible = target < 300;
        // We compensate the scroll since the header does not move in Hoot.
        const correctedTop = isHeaderVisible ? calculatedTop + target : calculatedTop;
        expect(correctedTop).toBe(isHeaderVisible ? HEADER_SIZE + DEFAULT_OFFSET : DEFAULT_OFFSET);
    }
});
