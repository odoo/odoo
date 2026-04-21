import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";

setupInteractionWhiteList("website.whatsapp");

function getWhatsappSnippet(dataWhatsappNumber = "") {
    const dataWhatsappNumberAttr = dataWhatsappNumber
        ? `data-whatsapp-number="${dataWhatsappNumber}"`
        : "";
    return `
    <section
            class="s_whatsapp position-fixed bottom-0 o_no_save" ${dataWhatsappNumberAttr}
            data-agent-avatar-src="/website/static/src/img/snippets_demo/s_whatsapp_agent.webp"
        >
        <div class="s_whatsapp_translation_inputs">
            <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" data-name="Name" name="agent_name" value="Jane Doe"/>
            <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" data-name="Description" name="agent_description" value="Online"/>
            <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" data-name="Default Message" name="agent_message" value="Hi there 👋 how can I help you?"/>
            <div class="s_whatsapp_input_box">
                <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" data-name="Placeholder" name="message_placeholder" value="Enter Your Message..."/>
            </div>
            <div class="s_whatsapp_cta_box">
                <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" data-name="CTA Label" name="cta_label" value="Start Conversation"/>
            </div>
        </div>
        <div class="o_not_editable">
            <button class="s_whatsapp_fab btn position-relative d-inline-flex align-items-center justify-content-center rounded-circle p-0" aria-label="Open WhatsApp chat" contenteditable="false">
                <i class="fa fa-whatsapp fs-4" aria-hidden="true"/>
                <span class="s_whatsapp_notification_badge bg-danger position-absolute rounded-circle w-25 h-25"/>
            </button>
        </div>
    </section>
`;
}

test("Drop Whatsapp snippet and verify redirection to company number", async () => {
    patchWithCleanup(browser, {
        open: (url) => {
            expect.step(`open ${url}`);
        },
    });

    await startInteractions(getWhatsappSnippet("1234567890"));
    expect(".s_whatsapp").toHaveCount(1);
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(0);

    // Simulate opening and closing the chatbox (lazy mount/unmount).
    await click(".s_whatsapp_fab");
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(1);
    expect(".s_whatsapp .s_whatsapp_chatbox").not.toHaveClass("d-none");
    await click(".s_whatsapp_close_btn");
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(0);
    await click(".s_whatsapp_fab");
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(1);

    // Simulate entering a message and sending it with Enter.
    await contains(".s_whatsapp_user_message").edit("Hello, I need help!");
    await contains(".s_whatsapp_user_message").press("Enter");

    // Verify the opened URL
    expect.verifySteps(["open https://wa.me/1234567890?text=Hello%2C%20I%20need%20help!"]);
});

test("Drop Whatsapp snippet and verify warning when no number is configured", async () => {
    await startInteractions(getWhatsappSnippet());
    expect(".s_whatsapp").toHaveCount(1);
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(0);
    await click(".s_whatsapp_fab");
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(1);
    expect(".s_whatsapp .s_whatsapp_warning").not.toHaveClass("d-none");
    expect(".s_whatsapp .s_whatsapp_user_input").toHaveClass("d-none");
});
