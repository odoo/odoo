import { expect, test, beforeEach, describe } from "@odoo/hoot";
import { queryOne, queryAll } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

beforeEach(enableTransitions);
describe.current.tags("interaction_dev");
defineWebsiteModels();

test("carousel_slider updates min height of carousel items", async () => {
    const { iframeInteractionAPI, stopInteraction } = await setupWebsiteBuilderWithSnippet(
        "s_carousel",
        {
            enableInteractions: true,
            interactionWhitelist: ["website.carousel_slider"],
            openEditor: false,
        }
    );

    await iframeInteractionAPI.waitForReady();

    const carouselEl = queryOne(":iframe .carousel");
    const itemEls = queryAll(":iframe .carousel-item");
    const minHeight = itemEls[0].style.minHeight;

    for (const itemEl of itemEls) {
        expect(itemEl).toHaveStyle({ minHeight });
    }
    await stopInteraction(carouselEl);

    for (const itemEl of itemEls) {
        expect(itemEl).not.toHaveStyle({ minHeight });
    }
});
