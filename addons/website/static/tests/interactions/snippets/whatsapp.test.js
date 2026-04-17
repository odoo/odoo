import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList("website.whatsapp");

test("Drop Whatsapp snippet and verify redirection to company number", async () => {
    patchWithCleanup(browser, {
        open: (url) => {
            expect.step(`open ${url}`);
        },
    });

    await startInteractionsWithSnippet("s_whatsapp", {
        processHTML: (html) => {
            const whatsappEl = html.querySelector(".s_whatsapp");
            whatsappEl.dataset.whatsappNumber = "1234567890";
        },
    });
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
    await startInteractionsWithSnippet("s_whatsapp");
    expect(".s_whatsapp").toHaveCount(1);
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(0);
    await click(".s_whatsapp_fab");
    expect(".s_whatsapp .s_whatsapp_chatbox").toHaveCount(1);
    expect(".s_whatsapp .s_whatsapp_warning").not.toHaveClass("d-none");
    expect(".s_whatsapp .s_whatsapp_user_input").toHaveClass("d-none");
});
