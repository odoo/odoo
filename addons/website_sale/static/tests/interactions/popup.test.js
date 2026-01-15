import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, tick } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.popup");
describe.current.tags("interaction_dev");

test("click on primary button which is add to cart button doesn't close popup", async () => {
    defineStyle(/* css */`* { transition: none !important; }`);
    const { core } = await startInteractions(`
        <div class="s_popup o_snippet_invisible" data-vcss="001" data-snippet="s_popup"
             data-name="Popup" id="sPopup" data-invisible="1">
            <div class="modal fade s_popup_middle modal_shown"
                 style="background-color: var(--black-50) !important; display: none;"
                 data-show-after="0"
                 data-display="afterDelay"
                 data-consents-duration="7"
                 data-bs-focus="false"
                 data-bs-backdrop="false"
                 tabindex="-1"
                 aria-label="Popup"
                 aria-modal="true"
                 role="dialog">
                <div class="modal-dialog d-flex">
                    <div class="modal-content oe_structure">
                        <div class="s_popup_close js_close_popup o_we_no_overlay o_not_editable" aria-label="Close">×</div>
                        <section>
                            <a href="#" class="btn btn-primary js_add_cart">Primary button</a>
                        </section>
                    </div>
                </div>
            </div>
        </div >
    `);
    expect(core.interactions).toHaveLength(1);
    const modal = "#sPopup .modal";
    await tick();
    await animationFrame();
    expect(modal).toBeVisible();
    await tick();
    await click(".btn-primary");
    expect(modal).toBeVisible();
});
