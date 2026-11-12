import { addBuilderPlugin, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, clear, click, fill, waitFor } from "@odoo/hoot-dom";
import { Plugin } from "@html_editor/plugin";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

/**
 * Rating markup with 3 active stars and 2 inactive ones.
 */
function getRatingContent({ inactiveClass = "fa fa-star", classes = "" } = {}) {
    return `
    <div class="s_rating ${classes}" data-icon="fa-star" data-snippet="s_rating" data-name="Rating">
        <div class="s_rating_icons o_not_editable">
            <span class="s_rating_active_icons">${'<i class="fa fa-star"></i>'.repeat(3)}</span>
            <span class="s_rating_inactive_icons">${`<i class="${inactiveClass}"></i>`.repeat(
                2
            )}</span>
        </div>
    </div>`;
}

test("change rating score", async () => {
    await setupHTMLBuilder(getRatingContent());
    expect(":iframe .s_rating .s_rating_active_icons i").toHaveCount(3);
    expect(":iframe .s_rating .s_rating_inactive_icons i").toHaveCount(2);
    await contains(":iframe .s_rating").click();
    await contains(".options-container [data-action-id='activeIconsNumber'] input").click();
    await clear();
    await fill("1");
    await animationFrame();
    expect(":iframe .s_rating .s_rating_active_icons i").toHaveCount(1);
    await contains(".options-container [data-action-id='totalIconsNumber'] input").click();
    await clear();
    await fill("4");
    await animationFrame();
    expect(":iframe .s_rating .s_rating_inactive_icons i").toHaveCount(3);
    expect(":iframe .s_rating").toHaveInnerHTML(
        `<div class="s_rating_icons o_not_editable" contenteditable="false">
            <span class="s_rating_active_icons">
                <i class="fa fa-star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
            </span>
            <span class="s_rating_inactive_icons">
                <i class="fa fa-star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
                <i class="fa fa-star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
                <i class="fa fa-star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
            </span>
        </div>`
    );
});

function expectIcons(selector, count, className) {
    expect(`:iframe ${selector} i`).toHaveCount(count);
    expect(`:iframe ${selector} i`).toHaveAttribute("class", className);
}

test("changing the score keeps filled inactive icons", async () => {
    await setupHTMLBuilder(getRatingContent());
    await contains(":iframe .s_rating").click();

    await contains(".options-container [data-action-id='activeIconsNumber'] input").edit("1");
    expectIcons(".s_rating_inactive_icons", 4, "fa fa-star");
});

test("ratings matched by a hollow selector keep hollow inactive icons", async () => {
    addBuilderPlugin(
        class extends Plugin {
            static id = "testHollowRating";
            resources = { hollow_rating_selectors: ".s_rating.o_test_hollow" };
        }
    );
    await setupHTMLBuilder(
        getRatingContent({ inactiveClass: "fa fa-star-o", classes: "o_test_hollow" })
    );
    await contains(":iframe .s_rating").click();

    await contains(".options-container [data-action-id='activeIconsNumber'] input").edit("1");
    expectIcons(".s_rating_inactive_icons", 4, "fa fa-star-o");

    await contains("[data-label='Icon'] .dropdown-toggle").click();
    await contains(".dropdown-item:contains(Hearts)").click();
    expectIcons(".s_rating_active_icons", 1, "fa fa-heart");
    expectIcons(".s_rating_inactive_icons", 4, "fa fa-heart-o");
});

test("Ensure order of operations when clicking very fast on two options", async () => {
    await setupHTMLBuilder(getRatingContent());
    await contains(":iframe .s_rating").click();
    await waitFor("[data-label='Icon']");
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Stars");
    expect(":iframe .s_rating").not.toHaveAttribute("data-active-custom-icon");
    await click(".options-container [data-action-id='customIcon']");
    await click(".options-container [data-class-action='fa-2x']");
    await animationFrame();
    expect(":iframe .s_rating_icons").not.toHaveClass("fa-2x");
    await contains(".modal-dialog .fa-glass").click();
    expect(":iframe .s_rating").toHaveAttribute("data-active-custom-icon", "fa fa-glass");
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Custom");
    expect(":iframe .s_rating_icons").toHaveClass("fa-2x");
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Custom");
    expect(":iframe .s_rating").toHaveAttribute("data-active-custom-icon", "fa fa-glass");
    expect(":iframe .s_rating_icons").not.toHaveClass("fa-2x");
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Stars");
    expect(":iframe .s_rating").not.toHaveAttribute("data-active-custom-icon");
    expect(":iframe .s_rating_icons").not.toHaveClass("fa-2x");
});
