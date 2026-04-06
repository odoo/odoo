import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, edit, press, runAllTimers, tick } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains, defineStyle, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

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

function getTemplate(successMode = "message") {
    return `
        <div class="s_popup o_newsletter_popup o_snippet_invisible"
             data-name="Newsletter Popup" data-vcss="001" data-snippet="s_newsletter_subscribe_popup" id="sPopup" data-invisible="1">
            <div class="modal fade s_popup_middle o_newsletter_modal modal_shown"
                style="background-color: var(--black-50) !important; display: none;"
                data-show-after="0" data-display="afterDelay" data-consents-duration="7" data-bs-focus="false" data-bs-backdrop="false" tabindex="-1" aria-modal="true" role="dialog">
                <div class="modal-dialog">
                    <div class="modal-content oe_structure">
                        <button class="s_popup_close js_close_popup border-0 p-0 o_we_no_overlay o_not_editable" aria-label="Close">×</button>
                        <section>
                            <div class="container">
                                <div class="s_newsletter_subscribe_form s_newsletter_list js_subscribe"
                                    data-vxml="001" data-list-id="3" data-name="Newsletter Form" data-snippet="s_newsletter_subscribe_form" data-success-mode="${successMode}" data-success-page="/demo-route">
                                    <div class="js_subscribed_wrap d-none">
                                        <p class="h4-fs text-center text-success mb-0"><i class="fa fa-check-circle-o" role="img"/> Thanks for registering!</p>
                                    </div>
                                    <div class="js_subscribe_wrap">
                                        <div class="input-group">
                                            <input type="email" name="email" class="js_subscribe_value form-control">
                                            <a role="button" href="#" class="btn btn-primary js_subscribe_btn o_submit">Subscribe</a>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>
                    </div>
                </div>
            </div>
        </div>
    `;
}

describe("mail popup", () => {
    beforeEach(() => {
        defineStyle(/* css */ `* { transition: none !important; }`);
        isSubscriber = false;
    });
    test("popup is shown if user is not subscribed (mail input not disabled)", async () => {
        const { core } = await startInteractions(getTemplate());
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
        const { core } = await startInteractions(getTemplate());
        expect(core.interactions).toHaveLength(2);
        await tick();
        await animationFrame();
        expect("#sPopup .modal").not.toBeVisible();
    });

    test("selecting data-success-mode to redirect should redirect after subscribing", async () => {
        patchWithCleanup(browser.location, {
            assign(url) {
                expect.step(`redirect:${url}`);
            },
        });
        await startInteractions(getTemplate("redirect"));
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
        await startInteractions(getTemplate("closePopup"));
        await contains("#sPopup .modal .js_subscribe_wrap input").click();
        await edit("demouser@odoo.com");
        await runAllTimers();
        await press("Enter");
        await expect.waitForSteps(["calling subscribe"]);
        await animationFrame();
        expect("#sPopup .modal").not.toBeVisible();
    });
});
