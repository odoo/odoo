import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("The pause button is hidden until the option shows it", async () => {
    await setupWebsiteBuilderWithSnippet("s_announcement_scroll", { loadIframeBundles: true });
    await contains(":iframe .s_announcement_scroll").click();
    expect(":iframe .o_marquee_pause").not.toBeVisible();

    await contains(
        "[data-label='Pause Button'] [data-class-action='o_marquee_pause_btn_hidden'] input"
    ).click();
    expect(":iframe .o_marquee_pause").toBeVisible();
});

test("Cannot edit the pause button", async () => {
    await setupWebsiteBuilderWithSnippet("s_announcement_scroll", { loadIframeBundles: true });
    await contains(":iframe .s_announcement_scroll").click();
    await contains(
        "[data-label='Pause Button'] [data-class-action='o_marquee_pause_btn_hidden'] input"
    ).click();
    await contains(":iframe .s_announcement_scroll .o_marquee_pause_icon").dblclick();
    // The media dialog doesn't open.
    expect(".modal").toHaveCount(0);
});

test("No pause button option without the pause button", async () => {
    await setupWebsiteBuilder(`
        <section class="s_announcement_scroll s_announcement_scroll_direction_left" role="marquee">
            <div class="s_announcement_scroll_marquee_container d-flex">
                <div class="o_not_editable s_announcement_scroll_marquee_item">Free Shipping</div>
            </div>
        </section>
    `);
    await contains(":iframe .s_announcement_scroll").click();
    expect("[data-label='Hover effect']").toHaveCount(1);
    expect("[data-label='Pause Button']").toHaveCount(0);
});
