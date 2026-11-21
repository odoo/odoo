import { expect, getFixture, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";
import { setElementContent } from "@web/core/utils/html";
import { setupWebsiteBuilder, defineWebsiteModels } from "./website_helpers";
import { hideOutOfDatetimeRangeElements } from "@website/utils/misc";

defineWebsiteModels();

// POSIX timestamp (in seconds) of 01/01/2020 00:00 UTC.
const VISIBILITY_TIMESTAMP = 1577836800;

test("hide elements outside their visibility datetime range", () => {
    const now = Math.floor(Date.now() / 1000);
    const containerEl = document.createElement("div");
    setElementContent(
        containerEl,
        markup`
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
        `
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

test("o_datetime_range_hidden is removed when the editor starts", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <section class="o_datetime_range_hidden" data-visibility="conditional" data-visibility-until="${
            VISIBILITY_TIMESTAMP - 3600
        }">
            <div class="container">
                <p>TEST</p>
            </div>
        </section>
    `);
    expect(":iframe section").not.toHaveClass("o_datetime_range_hidden");
    // The removal must not be in the history, else the page becomes dirty.
    expect(getEditor().shared.history.canUndo()).toBe(false);
});
