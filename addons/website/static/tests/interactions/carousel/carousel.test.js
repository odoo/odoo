import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { hover, leave, queryOne } from "@odoo/hoot-dom";
import { animationFrame, advanceTime } from "@odoo/hoot-mock";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList("website.carousel_bootstrap_upgrade_fix");

describe.current.tags("interaction_dev");

function processCarouselSnippet(bsRide, bsInterval, snippetName = "s_carousel") {
    return (html) => {
        const snippetEl = html.querySelector(`[data-snippet='${snippetName}']`) || html;
        const carouselEl = snippetEl.querySelector(".carousel");
        Object.assign(carouselEl.dataset, {
            bsRide,
            bsInterval,
        });
    };
}

// TODO : Fix this test
// -> It seems like the first slide of the carousel happen after more than 3s
test.skip("Carousel - Autoplay: Always - 3s - s_carousel", async () => {
    const { core } = await startInteractionsWithSnippet("s_carousel", {
        processHTML: processCarouselSnippet("carousel", 3000),
    });
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
    const { core } = await startInteractionsWithSnippet("s_image_gallery", {
        processHTML: processCarouselSnippet("carousel", 3000, "s_image_gallery"),
    });
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
    const { core } = await startInteractionsWithSnippet("s_carousel", {
        processHTML: processCarouselSnippet("true", 3000),
    });
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
    const { core } = await startInteractionsWithSnippet("s_image_gallery", {
        processHTML: processCarouselSnippet("true", 3000),
    });
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
    const { core } = await startInteractionsWithSnippet("s_carousel", {
        processHTML: processCarouselSnippet("false", 3000),
    });
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
    const { core } = await startInteractionsWithSnippet("s_image_gallery", {
        processHTML: processCarouselSnippet("false", 3000, "s_image_gallery"),
    });
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
