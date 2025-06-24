import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    insertCategorySnippet,
    setupWebsiteBuilder,
    waitForEndOfOperation,
} from "../website_helpers";

defineWebsiteModels();

describe("Popup options: empty page before edit", () => {
    // Note: for some reason, `before()` doesn't work.
    // Done in `beforeEach` because frontend JS takes too much time to load.
    beforeEach(async () => {
        await setupWebsiteBuilder("", { loadIframeBundles: true, loadAssetsFrontendJS: true });
    });
    test("dropping the popup snippet automatically displays it", async () => {
        await insertCategorySnippet({ group: "content", snippet: "s_popup" });
        expect(".o_add_snippet_dialog").toHaveCount(0);
        await waitForEndOfOperation();
        // Check if the popup is visible.
        expect(":iframe .s_popup .modal").toHaveClass("show");
        expect(":iframe .s_popup .modal").toHaveStyle({ display: "block" });
    });
});
describe("Popup options: popup in page before edit", () => {
    // Done in `beforeEach` because frontend JS takes too much time to load.
    beforeEach(async () => {
        await setupWebsiteBuilder(
            `<div class="s_popup o_snippet_invisible o_draggable" data-snippet="s_popup" data-name="Popup" id="sPopup" data-invisible="1">
                <div class="modal fade s_popup_middle modal_shown" style="background-color: var(--black-50)  !important; display: none;" data-show-after="5000" data-display="afterDelay" data-consents-duration="7" data-bs-focus="false" data-bs-backdrop="false" tabindex="-1" aria-label="Popup" aria-hidden="true">
                    <div class="modal-dialog d-flex">
                        <div class="modal-content oe_structure">
                            <div class="s_popup_close js_close_popup o_we_no_overlay o_not_editable" aria-label="Close" contenteditable="false">×</div>
                            <section>Popup content</section>
                        </div>
                    </div>
                </div>
            </div>`,
            {
                loadIframeBundles: true,
                loadAssetsFrontendJS: true,
            }
        );
    });

    test("editing a page with a popup snippet doesn't automatically display it", async () => {
        await advanceTime(5000);
        expect(":iframe .s_popup .modal").not.toBeVisible();
        expect(":iframe .s_popup").toHaveAttribute("data-invisible", "1");
    });

    test("closing s_popup with the X button updates the invisible elements panel", async () => {
        await contains(".o_we_invisible_entry .fa-eye-slash").click();
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye");
        // Sometimes bootstrap.js takes a bit of time to close the popup.
        await waitFor(":iframe .s_popup div.js_close_popup", { timeout: 500 });
        await contains(":iframe .s_popup div.js_close_popup").click();
        expect(":iframe .s_popup").not.toBeVisible();
        expect(".o_we_invisible_entry .fa").toHaveClass("fa-eye-slash");
    });
});
