import { setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, queryOne } from "@odoo/hoot-dom";

import { setupTest, simpleScroll, doubleScroll } from "./helpers";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList([
    "website.header_standard",
    "website.header_fixed",
    "website.header_disappears",
    "website.header_fade_out",
    "website.faq_horizontal",
]);

describe.current.tags("interaction_dev");

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
const DEFAULT_OFFSET = 16;

const SCROLLS = [0, 40, 250, 400, 250, 40, 0];
const SCROLLS_SPECIAL = [0, 40, 400, 40, 0];

test("faq_horizontal is started when there is an element .s_faq_horizontal", async () => {
    const { core } = await startInteractionsWithSnippet("s_faq_horizontal", {
        processHTML: addHeader(""),
    });
    expect(core.interactions).toHaveLength(1);
});

test.tags("desktop");
test("faq_horizontal updates titles position with a o_header_standard", async () => {
    const { core } = await startInteractionsWithSnippet("s_faq_horizontal", {
        processHTML: addHeader("o_header_standard"),
    });
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
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
test("faq_horizontal updates titles position with a o_header_fixed", async () => {
    const { core } = await startInteractionsWithSnippet("s_faq_horizontal", {
        processHTML: addHeader("o_header_fixed"),
    });
    expect(core.interactions).toHaveLength(2);
    // We force the header to never be consider "atTop", so that its
    // position is properly computed.
    core.interactions[0].interaction.topGap = -1;
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
    await setupTest(core, wrapwrap);
    for (const target of SCROLLS_SPECIAL) {
        await simpleScroll(wrapwrap, target);
        // There is no need to compensate the scroll here
        expect(Math.round(parseFloat(title.style.top))).toBe(HEADER_SIZE + DEFAULT_OFFSET);
    }
});

test.tags("desktop");
test("faq_horizontal updates titles position with a o_header_disappears", async () => {
    const { core } = await startInteractionsWithSnippet("s_faq_horizontal", {
        processHTML: addHeader("o_header_disappears"),
    });
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
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
test("faq_horizontal updates titles position with a o_header_fade_out", async () => {
    const { core } = await startInteractionsWithSnippet("s_faq_horizontal", {
        processHTML: addHeader("o_header_fade_out"),
    });
    expect(core.interactions).toHaveLength(2);
    const wrapwrap = queryOne("#wrapwrap");
    const title = queryFirst(".s_faq_horizontal_entry_title");
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
