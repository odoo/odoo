import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { switchToEditMode } from "../../helpers";
import { imageGalleryCarouselStyleSnippet } from "./carousel_helpers";

setupInteractionWhiteList("website.carousel_bootstrap_upgrade_fix");

describe.current.tags("interaction_dev");

test("[EDIT] carousel_bootstrap_upgrade_fix prevents ride", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("true", "5000"));
    expect(core.interactions).toHaveLength(1);
    await switchToEditMode(core);
    const carouselEl = queryOne(".carousel");
    const carouselBS = window.Carousel.getInstance(carouselEl);
    expect(carouselBS._config.ride).toBe(false);
    expect(carouselBS._config.pause).toBe(true);
});

test("carousel_bootstrap_upgrade_fix is tagged while sliding", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("true", "5000"));
    expect(core.interactions).toHaveLength(1);

    const carouselEl = queryOne(".carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).not.toHaveClass("o_carousel_sliding");

    await click(carouselEl.querySelector(".carousel-control-next"));

    expect(carouselEl).toHaveClass("o_carousel_sliding");
    await advanceTime(750);
    expect(carouselEl).not.toHaveClass("o_carousel_sliding");
});
