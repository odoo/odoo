import { setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, press, queryAll } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { startInteractionsWithSnippet } from "../helpers";

setupInteractionWhiteList(["website.gallery", "website.base_lightbox"]);

describe.current.tags("interaction_dev");

async function checkLightbox({ next, previous, close }) {
    const { core } = await startInteractionsWithSnippet("s_images_wall", {
        withImgSrc: true,
    });
    expect(core.interactions).toHaveLength(1);
    const imgEls = queryAll("img");
    await click(imgEls[3]);
    await animationFrame();
    await advanceTime(1000);
    const lightboxEl = document.querySelector(".o_image_lightbox");
    expect(lightboxEl).not.toBe(null);

    async function checkActiveImage(expectedIndex) {
        await animationFrame();
        await advanceTime(1000);
        const lightboxActiveImgEl = lightboxEl.querySelector(".active img");
        expect(lightboxActiveImgEl).not.toBe(null);
        expect(imgEls[expectedIndex]).toHaveAttribute("src", lightboxActiveImgEl.dataset.src);
    }

    await checkActiveImage(3);
    await next(lightboxEl);
    await checkActiveImage(4);
    await next(lightboxEl);
    await checkActiveImage(5);
    await next(lightboxEl);
    await checkActiveImage(0);
    await previous(lightboxEl);
    await checkActiveImage(5);
    await previous(lightboxEl);
    await checkActiveImage(4);
    await close(lightboxEl);
    await animationFrame();
    await advanceTime(1000);
    expect(document.querySelector(".o_image_lightbox")).toBe(null);
}

test("gallery interaction opens lightbox on click, then use keyboard", async () => {
    await checkLightbox({
        close: async () => await press("Escape", { code: "Escape" }),
        next: async () => await press("ArrowRight", { code: "ArrowRight" }),
        previous: async () => await press("ArrowLeft", { code: "ArrowLeft" }),
    });
});

test("gallery interaction opens lightbox on click, then use mouse", async () => {
    await checkLightbox({
        close: async (lightboxEl) => await click(lightboxEl.querySelector(".btn-close")),
        next: async (lightboxEl) => await click(lightboxEl.querySelector(".carousel-control-next")),
        previous: async (lightboxEl) =>
            await click(lightboxEl.querySelector(".carousel-control-prev")),
    });
});
