import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, clear, click, fill, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const websiteContent = `
    <div class="s_rating pt16 pb16" data-rating-icon="star" data-snippet="s_rating" data-name="Rating">
        <strong class="s_rating_title">Quality</strong>
        <div class="s_rating_icons o_not_editable">
            <span class="s_rating_active_icons">
                <i class="oi oi-filled" data-icon="star"></i>
                <i class="oi oi-filled" data-icon="star"></i>
                <i class="oi oi-filled" data-icon="star"></i>
            </span>
            <span class="s_rating_inactive_icons">
                <i class="oi" data-icon="star"></i>
                <i class="oi" data-icon="star"></i>
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
                <i class="oi oi-filled" data-icon="star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
            </span>
            <span class="s_rating_inactive_icons">
                <i class="oi" data-icon="star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
                <i class="oi" data-icon="star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
                <i class="oi" data-icon="star" contenteditable="false">
                    &ZeroWidthSpace;
                </i>
            </span>
        </div>`
    );
});
test("Ensure order of operations when clicking very fast on two options", async () => {
    await setupHTMLBuilder(websiteContent);
    await contains(":iframe .s_rating").click();
    await waitFor("[data-label='Icon']");
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Stars");
    expect(":iframe .s_rating").not.toHaveAttribute("data-active-custom-icon");
    await click(".options-container [data-action-id='customIcon']");
    await click(".options-container [data-class-action='oi-2x']");
    await animationFrame();
    expect(":iframe .s_rating_icons").not.toHaveClass("oi-2x");
    await contains(".modal-dialog [data-icon='local_bar']").click();
    expect(":iframe .s_rating").toHaveAttribute("data-active-custom-icon", "local_bar");
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Custom");
    expect(":iframe .s_rating_icons").toHaveClass("oi-2x");
    await contains(".o-snippets-top-actions [data-icon='undo']").click();
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Custom");
    expect(":iframe .s_rating").toHaveAttribute("data-active-custom-icon", "local_bar");
    expect(":iframe .s_rating_icons").not.toHaveClass("oi-2x");
    await contains(".o-snippets-top-actions [data-icon='undo']").click();
    expect("[data-label='Icon'] .dropdown-toggle").toHaveText("Stars");
    expect(":iframe .s_rating").not.toHaveAttribute("data-active-custom-icon");
    expect(":iframe .s_rating_icons").not.toHaveClass("oi-2x");
});
