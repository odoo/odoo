import { after, before, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList("website.whatsapp");

let originalWindowOpen;

function mockWindowOpen() {
    originalWindowOpen = window.open;
    window.open = (url) => {
        expect.step(`window_open ${url}`);
    };
}

function unmockWindowOpen() {
    window.open = originalWindowOpen;
}

before(() => {
    mockWindowOpen();
});

after(() => {
    unmockWindowOpen();
});

const whatsappSnippet = `
    <section class="s_whatsapp position-fixed bottom-0">
        <div class="position-relative d-inline-flex o_not_editable">
            <i class="fa fa-2x fa-whatsapp wa-fab rounded-circle d-flex align-items-center justify-content-center shadow-lg o_pos_right"></i>
            <span class="notification-badge bg-danger position-absolute rounded-circle"></span>
        </div>
        <div class="chatbox bg-white rounded-3 position-absolute shadow-lg overflow-hidden mb-2 d-none">
            <div class="header d-flex align-items-center p-2 text-white">
                <div class="o_not_editable">
                    <img class="wa-agent-img rounded-circle" src="/website/static/src/img/snippets_demo/s_whatsapp_agent.webp" alt="agent"/>
                </div>
                <div class="ms-2 me-auto flex-grow-1 d-flex flex-column lh-1">
                    <strong class="wa-agent-name text-break mb-1">Jane Doe</strong>
                    <span class="wa-agent-description text-break">Online</span>
                </div>
                <div class="o_not_editable">
                    <button class="btn wa-close-btn p-2 text-white">
                        <i class="fa fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="wa-messages p-2">
                <p class="wa-agent-msg text-break w-75 bg-white rounded-3 p-2 m-0 fs-6">Hi there 👋
                    <br/>How can I help you?
                </p>
            </div>
            <div class="wa-user-input">
                <!-- Regular input box -->
                <div class="wa-input-box border-top align-items-end">
                    <textarea name="wa_message" class="wa-user-message flex-grow-1 p-2 border-0" placeholder="Enter Your Message..." rows="1"></textarea>
                    <div class="o_not_editable">
                        <button class="wa-send border-0 p-2 text-white">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M2 21l21-9L2 3v7l15 2-15 2z"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <!-- CTA mode -->
                <div class="wa-cta-box justify-content-center p-2 border-top">
                    <button class="wa-cta-btn d-flex align-items-center gap-2 px-5 py-3 fw-semibold rounded-4 shadow-sm border-0 text-white" >
                        <div class="o_not_editable">
                            <i class="fa fa-whatsapp"></i>
                        </div>
                        Start Conversation
                    </button>
                </div>
            </div>
            <div class="wa-warning alert alert-warning d-none m-2 fs-6">
                <i class="fa fa-info-circle me-1"></i>
                Messaging is not available. Please contact us by another way.
            </div>
        </div>
    </section>
`;

test("Drop Whatsapp snippet and verify redirection to company number", async () => {
    onRpc("/website/company_phone", () => "1234567890");
    await startInteractions(whatsappSnippet);
    expect(".s_whatsapp").toHaveCount(1);
    const whatsappEl = document.querySelector(".s_whatsapp");
    // Simulate opening the chatbox
    await click(".wa-fab");
    const chatboxEl = whatsappEl.querySelector(".chatbox");
    expect(chatboxEl).not.toHaveClass("d-none");

    // Simulate entering a message
    const inputEl = whatsappEl.querySelector(".wa-user-message");
    inputEl.value = "Hello, I need help!";

    // Click send button
    const sendBtnEl = whatsappEl.querySelector(".wa-send");
    sendBtnEl.click();

    // Verify the opened URL
    expect.verifySteps(["window_open https://wa.me/1234567890?text=Hello%2C%20I%20need%20help!"]);
});
