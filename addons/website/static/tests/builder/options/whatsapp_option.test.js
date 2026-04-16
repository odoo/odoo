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
    expect(":iframe .s_whatsapp .notification-badge").toHaveClass("d-none");

    // Cta mode
    await contains("[data-label='Show CTA'] input").click();
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
    expect(":iframe .s_whatsapp").toHaveStyle({
        left: "25px",
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
