import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { hover, leave, queryOne } from "@odoo/hoot-dom";
import { animationFrame, advanceTime } from "@odoo/hoot-mock";
import { defaultCarouselStyleSnippet, imageGalleryCarouselStyleSnippet } from "./carousel_helpers";

setupInteractionWhiteList("website.carousel_bootstrap_upgrade_fix");

describe.current.tags("interaction_dev");

// TODO : Fix this test
// -> It seems like the first slide of the carousel happen after more than 3s
test.skip("Carousel - Autoplay: Always - 3s - s_carousel", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("carousel", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

// TODO : Fix this test
// -> It seems like the first slide of the carousel happen after more than 3s
test.skip("Carousel - Autoplay: Always - 3s - s_image_gallery", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("carousel", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test.tags("desktop");
test("Carousel - Autoplay: After First Hover - 3s - s_carousel", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("true", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await hover(queryOne(".carousel"));
    await leave(queryOne(".carousel"));
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test.tags("desktop");
test("Carousel - Autoplay: After First Hover - 3s - s_image_gallery", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("true", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await hover(queryOne(".carousel"));
    await leave(queryOne(".carousel"));
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the next slide is properly active
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test("Carousel - Autoplay: Never - 3s - s_carousel", async () => {
    const { core } = await startInteractions(defaultCarouselStyleSnippet("false", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});

test("Carousel - Autoplay: Never - 3s - s_image_gallery", async () => {
    const { core } = await startInteractions(imageGalleryCarouselStyleSnippet("false", "3000"));
    expect(core.interactions).toHaveLength(1);
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
    await advanceTime(3000);
    await animationFrame();
    // We await twice to be sure the carousel did not slide
    await animationFrame();
    expect(".carousel .carousel-item:nth-child(1)").toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(2)").not.toHaveClass("active");
    expect(".carousel .carousel-item:nth-child(3)").not.toHaveClass("active");
});
