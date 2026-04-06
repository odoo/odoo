import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, edit, press, runAllTimers, tick } from "@odoo/hoot-dom";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { contains, defineStyle, onRpc } from "@web/../tests/web_test_helpers";
import { location } from "@web/core/browser/browser";
import { patch } from "@web/core/utils/patch";
import { startInteractionsWithSnippet } from "@website/../tests/interactions/helpers";

setupInteractionWhiteList(["website.popup", "website_mass_mailing.subscribe"]);
describe.current.tags("interaction_dev");

// Mock the RPC route for checking subscriber status
let isSubscriber;
onRpc("/website_mass_mailing/is_subscriber", () => ({
    is_subscriber: isSubscriber,
    warn_missing_list: false,
    value: "",
}));

// Mock the RPC route for subscribing
onRpc("/website_mass_mailing/subscribe", () => {
    expect.step("calling subscribe");
    return { toast_type: "success", toast_content: "Successfully subscribed!" };
});

function processNewsletterPopupHTML(formDataset = {}) {
    return (html) => {
        const popupEl = html.querySelector("[data-snippet='s_newsletter_subscribe_popup']");
        popupEl.id = "sPopup";
        popupEl.querySelector(".modal").dataset.showAfter = 0;
        Object.assign(popupEl.querySelector(".s_newsletter_subscribe_form").dataset, formDataset);
    };
}

describe("mail popup", () => {
    beforeEach(() => {
        defineStyle(/* css */ `* { transition: none !important; }`);
        isSubscriber = false;
    });
    test("popup is shown if user is not subscribed (mail input not disabled)", async () => {
        const { core } = await startInteractionsWithSnippet("s_newsletter_subscribe_popup", {
            processHTML: processNewsletterPopupHTML(),
        });
        expect(core.interactions).toHaveLength(2);
        await tick();
        await animationFrame();
        expect("#sPopup .modal").toBeVisible();
        // As data-success-mode is message, the thanks message should be shown
        // in the popup after subscribing.
        await contains("#sPopup .modal .js_subscribe_wrap input").click();
        await edit("demouser@odoo.com");
        await press("Enter");
        await expect.waitForSteps(["calling subscribe"]);
        expect("#sPopup .modal .js_subscribed_wrap").not.toHaveClass("d-none");
        expect("#sPopup .modal .js_subscribe_wrap").toHaveClass("d-none");
    });

    test("popup is not shown if user is subscribed (mail input disabled)", async () => {
        isSubscriber = true;
        const { core } = await startInteractionsWithSnippet("s_newsletter_subscribe_popup", {
            processHTML: processNewsletterPopupHTML(),
        });
        expect(core.interactions).toHaveLength(2);
        await tick();
        await animationFrame();
        expect("#sPopup .modal").not.toBeVisible();
    });

    test("selecting data-success-mode to redirect should redirect after subscribing", async () => {
        patch(location, {
            assign(url) {
                expect.step(`redirect:${url}`);
            },
        });
        await startInteractionsWithSnippet("s_newsletter_subscribe_popup", {
            processHTML: processNewsletterPopupHTML({
                successMode: "redirect",
                successPage: "/demo-route",
            }),
        });
        await contains("#sPopup .modal .js_subscribe_wrap input").click();
        await edit("demouser@odoo.com");
        await press("Enter");
        await expect.waitForSteps([
            "calling subscribe",
            "redirect:https://www.hoot.test/demo-route",
        ]);
        expect("#sPopup .modal .js_subscribed_wrap").not.toHaveClass("d-none");
        expect("#sPopup .modal .js_subscribe_wrap").toHaveClass("d-none");
    });

    test("selecting data-success-mode to closePopup should close the popup after subscribing", async () => {
        await startInteractionsWithSnippet("s_newsletter_subscribe_popup", {
            processHTML: processNewsletterPopupHTML({ successMode: "closePopup" }),
        });
        await contains("#sPopup .modal .js_subscribe_wrap input").click();
        await edit("demouser@odoo.com");
        await runAllTimers();
        await press("Enter");
        await expect.waitForSteps(["calling subscribe"]);
        await animationFrame();
        expect("#sPopup .modal").not.toBeVisible();
    });
});
