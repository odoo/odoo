import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { expect, test } from "@odoo/hoot";
import { queryOne, waitFor, waitForNone, waitUntil } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

async function setupWithHighlightInteraction(content) {
    await setupWebsiteBuilder(content, {
        loadIframeBundles: true,
        interactions: ["website.text_highlight"],
    });
}

async function selectAndOpenHighlights(el) {
    setSelection({
        anchorNode: el,
        anchorOffset: 0,
        focusNode: el,
        focusOffset: el.childNodes.length,
    });
    await expandToolbar();
    await contains(".o-we-toolbar button[title='Apply highlight']").click();
}

function countLines(textNode) {
    const range = textNode.ownerDocument.createRange();
    range.selectNodeContents(textNode);
    return new Set([...range.getClientRects()].map((rect) => Math.round(rect.top))).size;
}

test("highlight draws one svg per line", async () => {
    await setupWithHighlightInteraction(`
        <h2 style="width: 300px">This is an example of an unusually long title that exists purely to test multi-line wrapping</h2>`);
    await selectAndOpenHighlights(queryOne(":iframe h2"));
    await contains(".o_popover .o_text_highlight_underline").click();
    const highlightEl = queryOne(":iframe h2 .o_text_highlight_underline");
    const textNode = [...highlightEl.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
    expect(countLines(textNode)).toBeGreaterThan(1);
    await waitUntil(
        () => highlightEl.querySelectorAll("svg").length === countLines(textNode)
    );
});

test("reset removes the highlight and its svg", async () => {
    await setupWithHighlightInteraction(`<h1>Catchy Headline</h1>`);
    await selectAndOpenHighlights(queryOne(":iframe h1"));
    await contains(".o_popover .o_text_highlight_underline").click();
    await waitFor(":iframe h1 span.o_text_highlight_underline svg.o_text_highlight_svg");
    await contains(".o_popover button[title='Reset']").click();
    await waitForNone(":iframe h1 svg");
    expect(":iframe h1").toHaveInnerHTML("Catchy Headline");
});

test("highlight wraps each line of a multi-line text", async () => {
    await setupWithHighlightInteraction(
        `<p><strong>Text content line A</strong><br><i>Text content line B</i></p>`
    );
    await selectAndOpenHighlights(queryOne(":iframe p"));
    await contains(".o_popover .o_text_highlight_underline").click();
    expect(":iframe p > span.o_text_highlight_underline").toHaveCount(2);
    expect(":iframe p > br").toHaveCount(1);
    expect(":iframe p > span:first-child").toHaveText("Text content line A");
    expect(":iframe p > span:last-child").toHaveText("Text content line B");

    await contains(".o_popover #highlightPicker").click();
    await contains(".o_popover .o_text_highlight_jagged").click();
    expect(":iframe p > span.o_text_highlight_jagged").toHaveCount(2);
    expect(":iframe p > span.o_text_highlight_underline").toHaveCount(0);

    await contains(".o_popover button[title='Reset']").click();
    await waitForNone(":iframe p svg");
    expect(":iframe p").toHaveInnerHTML(
        "<strong>Text content line A</strong><br><i>Text content line B</i>"
    );
});
