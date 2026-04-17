import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, tick } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { startInteractionsWithSnippet } from "@website/../tests/interactions/helpers";

setupInteractionWhiteList("website.popup");
describe.current.tags("interaction_dev");

test("click on primary button which is add to cart button doesn't close popup", async () => {
    defineStyle(/* css */`* { transition: none !important; }`);
    const { core } = await startInteractionsWithSnippet("s_popup", {
        processHTML: (html) => {
            const popupEl = html.querySelector("[data-snippet='s_popup']");
            popupEl.id = "sPopup";
            popupEl.querySelector(".modal").dataset.showAfter = 0;
            popupEl.querySelector(".btn-primary").classList.add("js_add_cart");
        },
    });
    expect(core.interactions).toHaveLength(1);
    const modal = "#sPopup .modal";
    await tick();
    await animationFrame();
    expect(modal).toBeVisible();
    await tick();
    await click(".btn-primary");
    expect(modal).toBeVisible();
});
