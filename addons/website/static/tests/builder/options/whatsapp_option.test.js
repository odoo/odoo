import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { dummyBase64Img } from "@html_builder/../tests/helpers";
import { contains, dataURItoBlob, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Drop Whatsapp snippet and verify snippet options", async () => {
    await setupWebsiteBuilderWithSnippet("s_whatsapp", {
        loadIframeBundles: true,
    });
    await contains(":iframe .s_whatsapp").click();
    // Notification badge
    await contains("[data-label='Show Notification'] input").click();
    expect(":iframe .s_whatsapp .s_whatsapp_notification_badge").toHaveClass("d-none");

    // Cta mode
    await contains("[data-label='Show CTA'] input").click();
    expect(":iframe .s_whatsapp .s_whatsapp_cta_box").toHaveStyle({ display: "flex" });
    expect(":iframe .s_whatsapp .s_whatsapp_input_box").toHaveStyle({ display: "none" });

    // Layout
    await click("[data-label='Layout'] button");
    await contains("[data-class-action='rounded']").click();
    expect(":iframe .s_whatsapp .s_whatsapp_fab").toHaveClass("rounded");

    await click("[data-label='Layout'] button");
    await contains("[data-class-action='s_whatsapp_fab_circle']").click();
    expect(":iframe .s_whatsapp .s_whatsapp_fab").toHaveClass("s_whatsapp_fab_circle");

    await click("[data-label='Layout'] button");
    await contains("[data-class-action='rounded-circle']").click();
    expect(":iframe .s_whatsapp .s_whatsapp_fab").toHaveClass("rounded-circle");

    // Position
    await contains("[data-class-action='s_whatsapp_pos_left']").click();
    expect(":iframe .s_whatsapp .s_whatsapp_fab").toHaveClass("s_whatsapp_pos_left");
    expect(":iframe .s_whatsapp").toHaveStyle({
        left: "24px",
    });

    // Size
    await click("[data-label='Size'] button");
    await contains("[data-class-action='s_whatsapp_fab_medium']").click();
    expect(":iframe .s_whatsapp .s_whatsapp_fab > i").toHaveClass("s_whatsapp_fab_medium");

    await click("[data-label='Size'] button");
    await contains("[data-class-action='s_whatsapp_fab_large']").click();
    expect(":iframe .s_whatsapp .s_whatsapp_fab > i").toHaveClass("s_whatsapp_fab_large");

    // Color
    await contains("[data-class-action='no_icon_color'] input").click();
    expect(":iframe .s_whatsapp .s_whatsapp_fab").toHaveClass("no_icon_color");
});

test("Replacing the agent avatar stores an attachment URL", async () => {
    const avatarUrl = "/web/image/1-abcdef/agent.webp";
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/image/hoot.png",
            public: true,
        },
    ]);
    onRpc("/html_editor/get_image_info", () => ({
        attachment: { id: 1 },
        original: { id: 1, image_src: "/web/image/hoot.png", mimetype: "image/png" },
    }));
    onRpc("/web/image/hoot.png", () => dataURItoBlob(dummyBase64Img + "A".repeat(1000)));
    onRpc("/html_editor/modify_image/1", () => ({ original: avatarUrl }));

    await setupWebsiteBuilderWithSnippet("s_whatsapp", { loadIframeBundles: true });
    await contains(":iframe .s_whatsapp").click();
    await contains("[data-action-id='replaceAgentAvatar']").click();
    await click(".o_existing_attachment_cell .o_button_area");
    await waitFor(":iframe .s_whatsapp[data-agent-avatar-src^='/web/image/']");
    expect(":iframe .s_whatsapp").toHaveAttribute("data-agent-avatar-src", avatarUrl);
});
