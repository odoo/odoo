import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { describe, expect, test } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

const cookiesBarTemplate = `
    <div id="website_cookies_bar" class="s_popup o_snippet_invisible o_no_save o_editable o_dirty" data-name="Cookies Bar" data-vcss="001" data-oe-id="1328" data-oe-xpath="/data/xpath/div" data-oe-model="ir.ui.view" data-oe-field="arch" contenteditable="true" data-invisible="1">
        <div class="modal s_popup_bottom s_popup_no_backdrop o_cookies_discrete modal_shown show" data-show-after="500" data-display="afterDelay" data-consents-duration="999" data-bs-focus="false" data-bs-backdrop="false" data-bs-keyboard="false" tabindex="-1" style="display: block;" aria-modal="true" role="dialog">
            <div class="modal-dialog d-flex s_popup_size_full">
                <div class="modal-content oe_structure">

                    <section class="o_colored_level o_cc o_cc1">
                        <div class="container">
                            <div class="row">
                                <div class="col-lg-8 pt16">
                                    <p>
                                        <span class="pe-1">We use cookies to provide you a better user experience on this website.</span>
                                        <a href="/cookie-policy" class="o_cookies_bar_text_policy btn btn-link btn-sm px-0">Cookie Policy</a>
                                    </p>
                                </div>
                                <div class="col-lg-4 text-end pt16 pb16">
                                    <a href="#" id="cookies-consent-essential" role="button" class="js_close_popup btn btn-outline-primary rounded-circle btn-sm px-2">Only essentials</a>
                                    <a href="#" id="cookies-consent-all" role="button" class="js_close_popup btn btn-outline-primary rounded-circle btn-sm">I agree</a>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    </div>`;

describe("Cookies bar popup options", () => {
    test("Position option is not visible for discrete layout", async () => {
        await setupWebsiteBuilder(cookiesBarTemplate, {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        });
        await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
        await waitFor(".options-container");
        expect("[data-label='Position']").not.toHaveCount();
    });
    test("Position option is not visible for popup layout", async () => {
        await setupWebsiteBuilder(cookiesBarTemplate, {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        });
        await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
        await contains(".dropdown-toggle:contains('Discrete')").click();
        await contains("[data-class-action=o_cookies_popup]").click();
        expect("[data-label='Position']").toBeVisible();
    });

    test("Switch between cookies bar layout should keep the edited cookies bar content", async () => {
        const cookieBarContents = {
            ".o_cookies_bar_text_button": "Allow all cookies",
            ".o_cookies_bar_text_button_essential": "Only allow essential cookies",
            ".o_cookies_bar_text_title": "Respecting your privacy is our priority.",
            ".o_cookies_bar_text_primary":
                "Allow the use of cookies from this website on this browser?",
            ".o_cookies_bar_text_secondary":
                "We use cookies to provide improved experience on this website. You can learn more about our cookies and how we use them in our Cookie Policy .",
            ".o_cookies_bar_text_policy": "Cookie Policy",
        };
        function expectCookieBarContent() {
            for (const selector in cookieBarContents) {
                expect(`:iframe ${selector}`).toHaveText(cookieBarContents[selector]);
            }
        }

        const { getEditor } = await setupWebsiteBuilder(cookiesBarTemplate, {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        });
        const editor = getEditor();
        await contains(".o_we_invisible_el_panel .o_we_invisible_entry").click();
        await contains("[data-label='Layout'] .dropdown-toggle").click();
        await contains("[data-class-action=o_cookies_classic]").click();
        expectCookieBarContent();

        setSelection({
            anchorNode: queryOne(":iframe .o_cookies_bar_text_secondary"),
            anchorOffset: 0,
        });
        await insertText(editor, "Test:");
        cookieBarContents[".o_cookies_bar_text_secondary"] =
            "Test: We use cookies to provide improved experience on this website. You can learn more about our cookies and how we use them in our Cookie Policy .";
        expectCookieBarContent();

        await contains("[data-label='Layout'] .dropdown-toggle").click();
        await contains("[data-class-action=o_cookies_discrete]").click();
        await contains("[data-label='Layout'] .dropdown-toggle").click();
        await contains("[data-class-action=o_cookies_classic]").click();
        expectCookieBarContent();

        await contains("[data-label='Layout'] .dropdown-toggle").click();
        await contains("[data-class-action=o_cookies_popup]").click();
        expectCookieBarContent();

        await contains("[data-label='Layout'] .dropdown-toggle").click();
        await contains("[data-class-action=o_cookies_classic]").click();
        expectCookieBarContent();
    });
});
