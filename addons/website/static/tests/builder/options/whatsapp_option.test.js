import { expect, test } from "@odoo/hoot";
import { click, waitForNone } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Drop Whatsapp snippet and verify snippet options", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "avatar",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    await setupWebsiteBuilderWithSnippet("s_whatsapp", {
        loadIframeBundles: true,
    });
    await contains(":iframe .s_whatsapp").click();
    // Check that agent default values are correct
    expect("[data-action-id='agentName'] input").toHaveValue("Jane Doe");
    expect("[data-action-id='agentDescription'] input").toHaveValue("Online");
    expect("[data-action-id='defaultMessage'] input").toHaveValue(
        "Hi there 👋 how can I help you?"
    );

    // Agent name
    await contains("[data-action-id='agentName'] input").edit("Abel Smith");
    expect(":iframe .s_whatsapp .wa-agent-name").toHaveText("Abel Smith");

    // Agent description
    await contains("[data-action-id='agentDescription'] input").edit("Available");
    expect(":iframe .s_whatsapp .wa-agent-description").toHaveText("Available");

    // Contact number
    await contains("[data-label='Contact Number'] input").edit("1234567890");
    expect(":iframe .s_whatsapp").toHaveAttribute("data-whatsapp-number", "1234567890");

    // Avatar
    await contains("[data-action-id='replaceMedia']").click();
    expect(".modal-content:contains(Select a media) .o_upload_media_button").toHaveCount(1);
    expect("div.o-tooltip").toHaveCount(0);
    await contains(".o_select_media_dialog .o_button_area[aria-label='avatar']").click();
    await waitForNone(".o_select_media_dialog");
    expect(":iframe .s_whatsapp .wa-agent-img").toHaveClass("o_modified_image_to_save");

    // Default message
    await contains("[data-action-id='defaultMessage'] input").edit("Hello, how can I assist you?");
    expect(":iframe .s_whatsapp .wa-agent-msg").toHaveText("Hello, how can I assist you?");

    // Notification badge
    await contains("[data-label='Show Notification'] input").click();
    expect(":iframe .s_whatsapp .notification-badge").toHaveClass("d-none");

    // Cta mode
    await contains("[data-class-action='o_cta_mode'] input").click();
    expect(":iframe .s_whatsapp .wa-cta-box").toHaveStyle({ display: "flex" });
    expect(":iframe .s_whatsapp .wa-input-box").toHaveStyle({ display: "none" });

    // Layout
    await click("[data-label='Layout'] button");
    await contains("[data-class-action='rounded']").click();
    expect(":iframe .s_whatsapp .wa-fab").toHaveClass("rounded");

    await click("[data-label='Layout'] button");
    await contains("[data-class-action='rounded-empty-circle']").click();
    expect(":iframe .s_whatsapp .wa-fab").toHaveClass("rounded-empty-circle");

    await click("[data-label='Layout'] button");
    await contains("[data-class-action='rounded-circle']").click();
    expect(":iframe .s_whatsapp .wa-fab").toHaveClass("rounded-circle");

    // Position
    await contains("[data-class-action='o_pos_left']").click();
    expect(":iframe .s_whatsapp .wa-fab").toHaveClass("o_pos_left");
    expect(":iframe .s_whatsapp .chatbox").toHaveStyle({
        left: "0px",
    });

    // Size
    await click("[data-label='Size'] button");
    await contains("[data-class-action='fa-2x']").click();
    expect(":iframe .s_whatsapp .wa-fab").toHaveClass("fa-2x");

    await click("[data-label='Size'] button");
    await contains("[data-class-action='fa-3x']").click();
    expect(":iframe .s_whatsapp .wa-fab").toHaveClass("fa-3x");

    // Color
    await contains("[data-class-action='no_icon_color'] input").click();
    expect(":iframe .s_whatsapp").toHaveClass("no_icon_color");
});
