import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
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
