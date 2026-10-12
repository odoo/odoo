import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { setElementContent } from "@web/core/utils/html";
import { setupWebsiteBuilder, defineWebsiteModels } from "./website_helpers";
import { hideOutOfDatetimeRangeElements } from "@website/utils/misc";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";

defineWebsiteModels();

test("hide elements outside their visibility datetime range", () => {
    const now = Math.floor(Date.now() / 1000);
    const containerEl = document.createElement("div");
    setElementContent(
        containerEl,
        markup(`
            <section class="past" data-visibility="conditional" data-visibility-until="${
                now - 60
            }"></section>
            <section class="current" data-visibility="conditional" data-visibility-from="${
                now - 60
            }" data-visibility-until="${now + 60}"></section>
            <section class="future" data-visibility="conditional" data-visibility-from="${
                now + 60
            }"></section>
            <section class="start" data-visibility="conditional" data-visibility-from="${now}"></section>
            <section class="end" data-visibility="conditional" data-visibility-until="${now}"></section>
            <section class="invalid" data-visibility="conditional" data-visibility-from="not-a-timestamp"></section>
        `)
    );
    // inject_dom does not run in HOOT tests, so we manually set the page content
    // and call `hideOutOfDatetimeRangeElements`.
    getFixture().append(containerEl);
    hideOutOfDatetimeRangeElements();
    expect(".past").toHaveClass("o_datetime_range_hidden");
    expect(".current").not.toHaveClass("o_datetime_range_hidden");
    expect(".future").toHaveClass("o_datetime_range_hidden");
    expect(".start").not.toHaveClass("o_datetime_range_hidden");
    expect(".end").toHaveClass("o_datetime_range_hidden");
    expect(".invalid").not.toHaveClass("o_datetime_range_hidden");
});

test("o_datetime_range_hidden is not saved", async () => {
    const resultSave = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        resultSave.push(args[1]);
        return true;
    });
    const { getEditor } = await setupWebsiteBuilder(`
        <section class="o_datetime_range_hidden" data-visibility="conditional" data-visibility-until="1000000000">
            <div class="container">
                <p>TEST</p>
            </div>
        </section>
    `);
    setSelection({
        anchorNode: queryOne(":iframe p:not([data-selection-placeholder])"),
        anchorOffset: 1,
    });
    await insertText(getEditor(), "x");
    await contains(".o_hb_snippets_top_actions button:contains(Save)").click();
    expect(resultSave[0]).not.toInclude("o_datetime_range_hidden");
    expect(resultSave[0]).toInclude('data-visibility-until="1000000000"');
});
