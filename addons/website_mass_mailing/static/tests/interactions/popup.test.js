import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { startInteractionsWithSnippet } from "@website/../tests/interactions/helpers";

setupInteractionWhiteList("website.popup");
describe.current.tags("interaction_dev");

function processNewsletterPopupHTML(disabled = false) {
    return (html) => {
        const popupEl = html.querySelector("[data-snippet='s_newsletter_subscribe_popup']");
        popupEl.id = "sPopup";
        popupEl.querySelector(".modal").dataset.showAfter = 0;
        popupEl.querySelector(".js_subscribe_value").disabled = disabled;
    };
}

describe("mail popup", () => {
    beforeEach(() => defineStyle(/* css */`* { transition: none !important; }`));
    test("popup is shown if user is not subscribed (mail input not disabled)", async () => {
        const { core } = await startInteractionsWithSnippet("s_newsletter_subscribe_popup", {
            processHTML: processNewsletterPopupHTML(),
        });
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        expect("#sPopup .modal").toBeVisible();
    });

    test("popup is not shown if user is subscribed (mail input disabled)", async () => {
        const { core } = await startInteractionsWithSnippet("s_newsletter_subscribe_popup", {
            processHTML: processNewsletterPopupHTML(true),
        });
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        expect("#sPopup .modal").not.toBeVisible();
    });
});
