import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, clear, click, fill, queryAll, queryFirst, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const websiteContent = `
    <div class="s_rating pt16 pb16" data-icon="fa-star" data-snippet="s_rating" data-name="Rating">
        <strong class="s_rating_title">Quality</strong>
        <div class="s_rating_icons o_not_editable">
            <span class="s_rating_active_icons">
                <i class="fa fa-star"></i>
                <i class="fa fa-star"></i>
                <i class="fa fa-star"></i>
            </span>
            <span class="s_rating_inactive_icons">
                <i class="fa fa-star"></i>
                <i class="fa fa-star"></i>
            </span>
        </div>
    </div>`;

test("change rating score", async () => {
    await setupHTMLBuilder(websiteContent);
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
        `<strong class="s_rating_title">Quality</strong>
        <div class="s_rating_icons o_not_editable" contenteditable="false">
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
test("changing the rating keeps the inactive icons' glyph", async () => {
    await setupHTMLBuilder(websiteContent);
    // Remember the glyph the inactive icons have before any re-render.
    const inactiveClass = queryFirst(":iframe .s_rating_inactive_icons i").className;
    // Change the rating, which re-renders all the icons.
    await contains(":iframe .s_rating").click();
    await contains(".options-container [data-action-id='activeIconsNumber'] input").click();
    await clear();
    await fill("1");
    await animationFrame();
    // All inactive icons (old ones and new ones) still have that glyph.
    const inactiveIconEls = queryAll(":iframe .s_rating_inactive_icons i");
    expect(inactiveIconEls).toHaveLength(4);
    for (const iconEl of inactiveIconEls) {
        expect(iconEl).toHaveAttribute("class", inactiveClass);
    }
});
test("Ensure order of operations when clicking very fast on two options", async () => {
    await setupHTMLBuilder(websiteContent);
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
