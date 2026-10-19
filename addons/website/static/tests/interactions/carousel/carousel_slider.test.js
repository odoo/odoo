import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { queryAll } from "@odoo/hoot-dom";
import { enableTransitions } from "@odoo/hoot-mock";
import { onceAllImagesLoaded } from "@website/utils/images";
import { defaultCarouselStyleSnippet } from "./carousel_helpers";

setupInteractionWhiteList("website.carousel_slider");
beforeEach(enableTransitions);

describe.current.tags("interaction_dev");

test("carousel_slider updates min height of carousel items", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("carousel", "1000"));
    await onceAllImagesLoaded(getFixture());
    const itemEls = queryAll(".carousel-item");
    const minHeight = itemEls[0].style.minHeight;

    expect(core.interactions).toHaveLength(1);
    for (const itemEl of itemEls) {
        expect(itemEl).toHaveStyle({ minHeight });
    }

    core.stopInteractions();

    expect(core.interactions).toHaveLength(0);
    for (const itemEl of itemEls) {
        expect(itemEl).not.toHaveStyle({ minHeight });
    }
});
