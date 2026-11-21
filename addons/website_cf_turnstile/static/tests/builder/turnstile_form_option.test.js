import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { animationFrame, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";
import { contains, onRpc, webModels } from "@web/../tests/web_test_helpers";
import { WebsiteBridgePlugin } from "@website/builder/plugins/website_bridge_plugin";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

async function setupTurnstileFormBuilder(siteKey) {
    onRpc("get_authorized_fields", () => ({}));
    patch(webModels.IrModel.prototype, {
        get_compatible_form_models() {
            return [
                {
                    id: 184,
                    model: "mail.mail",
                    name: "Outgoing Mails",
                    website_form_label: "Send an E-mail",
                    website_form_key: "send_mail",
                },
            ];
        },
    });

    return setupWebsiteBuilderWithSnippet("s_website_form", {
        loadIframeBuilderTemplates: true,
        onIframeLoaded() {
            if (!siteKey) {
                return;
            }
            patch(WebsiteBridgePlugin.prototype, {
                getSession() {
                    return { turnstile_site_key: siteKey };
                },
            });
        },
    });
}

test("Turnstile policy option stays hidden without a site key", async () => {
    await setupTurnstileFormBuilder(false);
    await contains(":iframe section.s_website_form").click();
    await waitFor(".o_hb_row[data-label='Action']");
    expect("[data-label='Show Turnstile Policy']").toHaveCount(0);
});

test("Show Turnstile Policy toggles the legal notice", async () => {
    const { getEditor } = await setupTurnstileFormBuilder("test-site-key");

    const editor = getEditor();
    await contains(":iframe section.s_website_form").click();
    expect("[data-label='Show Turnstile Policy'] input").not.toBeChecked();

    await contains("[data-label='Show Turnstile Policy'] input").click();
    await waitFor(":iframe .s_website_form_turnstile");
    await animationFrame();

    expect("[data-label='Show Turnstile Policy'] input").toBeChecked();
    expect(":iframe .s_website_form_turnstile + .s_website_form_submit").toHaveCount(1);
    expect(":iframe .o_turnstile_legal_terms").toHaveText(/Protected by Turnstile/);
    expect(
        ":iframe .o_turnstile_legal_terms a[href='https://www.cloudflare.com/turnstile-privacy-policy/']"
    ).toHaveText("Privacy Policy");
    expect(
        ":iframe .o_turnstile_legal_terms a[href='https://www.cloudflare.com/policies/terms/']"
    ).toHaveText("Terms of use");

    undo(editor);
    await waitForNone(":iframe .s_website_form_turnstile");
    redo(editor);
    await waitFor(":iframe .s_website_form_turnstile + .s_website_form_submit");

    await contains("[data-label='Show Turnstile Policy'] input").click();
    await waitForNone(":iframe .s_website_form_turnstile");
    await animationFrame();
    expect("[data-label='Show Turnstile Policy'] input").not.toBeChecked();
});
