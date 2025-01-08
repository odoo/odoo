import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, press } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.gallery");
describe.current.tags("interaction_dev");

// TODO Obtain rendering from `website.s_images_wall` template ?
const defaultGallery = `
    <div id="wrapwrap">
        <section class="s_image_gallery o_spc-small o_masonry pt24 pb24 o_colored_level" data-vcss="002" data-columns="3" style="overflow: hidden;" data-snippet="s_images_wall" data-name="Images Wall">
            <div class="container">
                <div class="row s_nb_column_fixed">
                    <div class="o_masonry_col o_snippet_not_selectable col-lg-4">
                        <img class="img img-fluid d-block rounded" src="/web/image/website.library_image_03" data-index="0" data-name="Image" alt="" loading="lazy" data-mimetype="image/jpeg" data-original-id="204" data-original-src="/website/static/src/img/library/library_image_03.jpg" data-mimetype-before-conversion="image/jpeg"/>
                        <img class="img img-fluid d-block rounded" src="/web/image/website.library_image_10" data-index="3" data-name="Image" alt="" loading="lazy" data-mimetype="image/jpeg" data-original-id="211" data-original-src="/website/static/src/img/library/library_image_10.jpg" data-mimetype-before-conversion="image/jpeg"/>
                    </div>
                    <div class="o_masonry_col o_snippet_not_selectable col-lg-4">
                        <img class="img img-fluid d-block rounded" src="/web/image/website.library_image_13" data-index="1" data-name="Image" alt="" loading="lazy" data-mimetype="image/jpeg" data-original-id="214" data-original-src="/website/static/src/img/library/library_image_13.jpg" data-mimetype-before-conversion="image/jpeg"/>
                        <img class="img img-fluid d-block rounded" src="/web/image/website.library_image_05" data-index="4" data-name="Image" alt="" loading="lazy" data-mimetype="image/jpeg" data-original-id="206" data-original-src="/website/static/src/img/library/library_image_05.jpg" data-mimetype-before-conversion="image/jpeg"/>
                    </div>
                    <div class="o_masonry_col o_snippet_not_selectable col-lg-4">
                        <img class="img img-fluid d-block rounded" src="/web/image/website.library_image_14" data-index="2" data-name="Image" alt="" loading="lazy" data-mimetype="image/jpeg" data-original-id="215" data-original-src="/website/static/src/img/library/library_image_14.jpg" data-mimetype-before-conversion="image/jpeg"/>
                        <img class="img img-fluid d-block rounded" src="/web/image/website.library_image_16" data-index="5" data-name="Image" alt="" loading="lazy" data-mimetype="image/jpeg" data-original-id="217" data-original-src="/website/static/src/img/library/library_image_16.jpg" data-mimetype-before-conversion="image/jpeg"/>
                    </div>
                </div>
            </div>
        </section>
    </div>
`;

test("gallery does nothing if there is no non-slideshow s_image_gallery", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <section class="s_image_gallery o_slideshow"/>
        </div>
    `);
    expect(core.interactions.length).toBe(0);
});

async function checkLightbox({ next, previous, close }) {
    const { core, el } = await startInteractions(defaultGallery);
    expect(core.interactions.length).toBe(1);
    const imgEls = el.querySelectorAll("img");
    await click(imgEls[3]);
    await animationFrame();
    await advanceTime(1000);
    const lightboxEl = el.ownerDocument.querySelector(".s_gallery_lightbox");
    expect(lightboxEl).not.toBe(null);

    async function checkActiveImage(expectedIndex) {
        await animationFrame();
        await advanceTime(1000);
        let lightboxActiveImgEl = lightboxEl.querySelector(".active img");
        expect(lightboxActiveImgEl).not.toBe(null);
        expect(imgEls[expectedIndex].src).toMatch(
            lightboxActiveImgEl.dataset.src,
        );
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
    expect(el.ownerDocument.querySelector(".s_gallery_lightbox")).toBe(null);
}

test("gallery interaction opens lightbox on click, then use keyboard", async () => {
    await checkLightbox({
        next: async () => {
            await press("ArrowRight", { code: "ArrowRight" });
        },
        previous: async () => {
            await press("ArrowLeft", { code: "ArrowLeft" });
        },
        close: async () => {
            await press("Escape", { code: "Escape" });
        },
    });
});

test("gallery interaction opens lightbox on click, then use mouse", async () => {
    await checkLightbox({
        next: async (lightboxEl) => {
            await click(lightboxEl.querySelector(".carousel-control-next"));
        },
        previous: async (lightboxEl) => {
            await click(lightboxEl.querySelector(".carousel-control-prev"));
        },
        close: async (lightboxEl) => {
            await click(lightboxEl.querySelector(".btn-close"));
        },
    });
});
