import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import {
    defineWebsiteModels,
    getWebsiteBuilderIframe,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("interaction_dev");

defineWebsiteModels();
test("[EDIT] carousel_bootstrap_upgrade_fix prevents ride", async () => {
    const { iframeInteractionAPI } = await setupWebsiteBuilderWithSnippet("s_image_gallery", {
        enableEditInteractions: true,
        interactionWhitelist: ["website.carousel_bootstrap_upgrade_edit_fix"],
    });

    await iframeInteractionAPI.waitForReady();

    const iframe = getWebsiteBuilderIframe();
    const iframeWindow = iframe.contentWindow;

    // Query carousel from iframe document
    const carouselEl = queryOne(":iframe .carousel");
    await contains(":iframe .s_image_gallery").click();
    expect(carouselEl).not.toBe(null);

    // Get Bootstrap Carousel instance from iframe's Bootstrap
    const carouselBS = iframeWindow.Carousel?.getOrCreateInstance(carouselEl);

    // Verify edit mode configuration
    expect(carouselBS._config.ride).toBe(false);
    expect(carouselBS._config.pause).toBe(true);
});

test("carousel_bootstrap_upgrade_fix is tagged while sliding", async () => {
    const { iframeInteractionAPI } = await setupWebsiteBuilderWithSnippet("s_image_gallery", {
        enableInteractions: true,
        interactionWhitelist: ["website.carousel_bootstrap_upgrade_fix"],
    });

    await iframeInteractionAPI.waitForReady();

    const carouselEl = queryOne(":iframe .carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "1000");
    expect(carouselEl).not.toHaveClass("o_carousel_sliding");

    await click(carouselEl.querySelector(".carousel-control-next"));

    expect(carouselEl).toHaveClass("o_carousel_sliding");
    await advanceTime(750);
    expect(carouselEl).not.toHaveClass("o_carousel_sliding");
});
