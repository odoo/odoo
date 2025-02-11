import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { animationFrame, tick } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.popup");
describe.current.tags("interaction_dev");

function getTemplate(disabled = false) {
    return `
        <div class="s_popup o_newsletter_popup o_snippet_invisible"
             data-name="Newsletter Popup" data-vcss="001" data-snippet="s_newsletter_subscribe_popup" id="sPopup" data-invisible="1">
            <div class="modal fade s_popup_middle o_newsletter_modal modal_shown"
                style="background-color: var(--black-50) !important; display: none;"
                data-show-after="0" data-display="afterDelay" data-consents-duration="7" data-bs-focus="false" data-bs-backdrop="false" tabindex="-1" aria-modal="true" role="dialog">
                <div class="modal-dialog">
                    <div class="modal-content oe_structure">
                        <div class="s_popup_close js_close_popup o_we_no_overlay o_not_editable" aria-label="Close">×</div>
                        <section>
                            <div class="container">
                                <div class="s_newsletter_subscribe_form s_newsletter_list js_subscribe"
                                    data-vxml="001" data-list-id="3" data-name="Newsletter Form" data-snippet="s_newsletter_subscribe_form">
                                    <div class="js_subscribe_wrap">
                                        <div class="input-group">
                                            <input type="email" name="email" class="js_subscribe_value form-control" ${disabled ? "disabled='true'" : ""}>
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
    beforeEach(() => defineStyle(/* css */`* { transition: none !important; }`));
    test("popup is shown if user is not subscribed (mail input not disabled)", async () => {
        const { core } = await startInteractions(getTemplate());
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        expect("#sPopup .modal").toBeVisible();
    });

    test("popup is not shown if user is subscribed (mail input disabled)", async () => {
        const { core } = await startInteractions(getTemplate(true));
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        expect("#sPopup .modal").not.toBeVisible();
    });
});
