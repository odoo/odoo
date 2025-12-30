import { describe, expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    getWebsiteBuilderIframe,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

describe.current.tags("interaction_dev");
defineWebsiteModels();

test("[EDIT] carousel_edit resets slide to attributes", async () => {
    const { iframeInteractionAPI, stopInteraction } = await setupWebsiteBuilderWithSnippet(
        "s_carousel",
        {
            enableEditInteractions: true,
            interactionWhitelist: ["website.carousel_edit"],
            // SHSA: doesnt looks good, though we are in edit mode and sidebar is not opened
            // BUT for cases like these when we are not changing anything from option.
            // we dont need to open it, still things will work as expected.
            openEditor: false,
        }
    );

    await iframeInteractionAPI.waitForReady();

    const iframe = getWebsiteBuilderIframe();
    const iframeDoc = iframe.contentDocument;
    const carouselEl = iframeDoc.querySelector(".carousel");
    const controlEls = iframeDoc.querySelectorAll(".carousel-control-prev, .carousel-control-next");
    const indicatorEls = iframeDoc.querySelectorAll(".carousel-indicators > *");
    for (const controlEl of controlEls) {
        expect(controlEl).not.toHaveAttribute("data-bs-slide");
    }
    for (const indicatorEl of indicatorEls) {
        expect(indicatorEl).not.toHaveAttribute("data-bs-slide-to");
    }

    // Stop interactions to reset attributes
    await stopInteraction(carouselEl);

    for (const controlEl of controlEls) {
        expect(controlEl).toHaveAttribute("data-bs-slide");
    }
    for (const indicatorEl of indicatorEls) {
        expect(indicatorEl).toHaveAttribute("data-bs-slide-to");
    }
});
