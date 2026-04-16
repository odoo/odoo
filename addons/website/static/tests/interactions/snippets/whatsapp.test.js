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
            <div class="wa-input-box">
                <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" data-name="Placeholder" name="message_placeholder" value="Enter Your Message..."/>
            </div>
            <div class="wa-cta-box">
                <input type="hidden" class="o_translatable_input_hidden d-block mb-1 w-100" data-name="CTA Label" name="cta_label" value="Start Conversation"/>
            </div>
        </div>
        <button class="p-0 border-0 bg-transparent position-relative d-inline-flex o_not_editable" aria-label="Open WhatsApp chat">
            <i class="fa fa-whatsapp wa-fab rounded-circle d-flex align-items-center justify-content-center shadow-lg o_pos_right"></i>
            <span class="notification-badge bg-danger position-absolute rounded-circle"></span>
        </button>
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
    expect(".s_whatsapp .chatbox").toHaveCount(0);

    // Simulate opening and closing the chatbox (lazy mount/unmount).
    await click(".wa-fab");
    expect(".s_whatsapp .chatbox").toHaveCount(1);
    expect(".s_whatsapp .chatbox").not.toHaveClass("d-none");
    await click(".wa-close-btn");
    expect(".s_whatsapp .chatbox").toHaveCount(0);
    await click(".wa-fab");
    expect(".s_whatsapp .chatbox").toHaveCount(1);

    // Simulate entering a message and sending it with Enter.
    await contains(".wa-user-message").edit("Hello, I need help!");
    await contains(".wa-user-message").press("Enter");

    // Verify the opened URL
    expect.verifySteps(["open https://wa.me/1234567890?text=Hello%2C%20I%20need%20help!"]);
});

test("Drop Whatsapp snippet and verify warning when no number is configured", async () => {
    await startInteractions(getWhatsappSnippet());
    expect(".s_whatsapp").toHaveCount(1);
    expect(".s_whatsapp .chatbox").toHaveCount(0);
    await click(".wa-fab");
    expect(".s_whatsapp .chatbox").toHaveCount(1);
    expect(".s_whatsapp .wa-warning").not.toHaveClass("d-none");
    expect(".s_whatsapp .wa-user-input").toHaveClass("d-none");
});
