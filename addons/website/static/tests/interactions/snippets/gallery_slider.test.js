import {
    startInteractions,
    setupInteractionWhiteList,
} from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { onceAllImagesLoaded } from "@website/utils/images";

setupInteractionWhiteList("website.gallery_slider");

describe.current.tags("interaction_dev");

const SLIDE_DURATION = 1000;

// TODO Obtain rendering from `website.s_images_gallery` template ?
const defaultGallery = `
    <div id="wrapwrap">
        <section class="s_image_gallery o_slideshow pt24 pb24 s_image_gallery_controllers_outside s_image_gallery_controllers_outside_arrows_right s_image_gallery_indicators_dots s_image_gallery_arrows_default" data-vcss="002" data-columns="3">
            <div class="o_container_small overflow-hidden">
                <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-ride="false" data-bs-interval="0">
                    <div class="carousel-inner">
                        <div class="carousel-item active">
                            <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_08" data-name="Image" data-index="0" alt=""/>
                        </div>
                        <div class="carousel-item">
                            <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_03" data-name="Image" data-index="1" alt=""/>
                        </div>
                        <div class="carousel-item">
                            <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.library_image_02" data-name="Image" data-index="2" alt=""/>
                        </div>
                    </div>
                    <div class="o_carousel_controllers">
                        <button class="carousel-control-prev o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                            <span class="carousel-control-prev-icon" aria-hidden="true"/>
                            <span class="visually-hidden">Previous</span>
                        </button>
                        <div class="carousel-indicators">
                            <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="0" style="background-image: url(/web/image/website.library_image_08)" class="active" aria-label="Carousel indicator"/>
                            <button type="button" style="background-image: url(/web/image/website.library_image_03)" data-bs-target="#slideshow_sample" data-bs-slide-to="1" aria-label="Carousel indicator"/>
                            <button type="button" style="background-image: url(/web/image/website.library_image_02)" data-bs-target="#slideshow_sample" data-bs-slide-to="2" aria-label="Carousel indicator"/>
                        </div>
                        <button class="carousel-control-next o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="next" aria-label="Next" title="Next">
                            <span class="carousel-control-next-icon" aria-hidden="true"/>
                            <span class="visually-hidden">Next</span>
                        </button>
                    </div>
                </div>
            </div>
        </section>
    </div>
`;

// TODO Obtain rendering from `website.gallery.s_image_gallery_mirror.lightbox` template ?
const defaultLightbox = `
    <main class="modal-body o_slideshow bg-transparent">
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close" style="position: absolute; right: 10px; top: 10px;">
        </button>
        <div style="margin: 0 12px;" id="slideshow_3" class="carousel slide undefined" data-bs-ride="false" data-bs-interval="0">
            <div class="carousel-inner">
                <div class="carousel-item active">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_03" alt="">
                </div>
                <div class="carousel-item undefined">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_10" alt="">
                </div>
                <div class="carousel-item undefined">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_13" alt="">
                </div>
                <div class="carousel-item undefined">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_05" alt="">
                </div>
                <div class="carousel-item undefined">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_14" alt="">
                </div>
                <div class="carousel-item undefined">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_16" alt="">
                </div>
            </div>
            <div class="o_carousel_controllers">
                <button class="carousel-control-prev o_we_no_overlay o_not_editable" contenteditable="false" data-bs-slide="prev" aria-label="Previous" title="Previous" data-bs-target="#slideshow_3">
                    <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Previous</span>
                </button>
                <div class="carousel-indicators s_image_gallery_indicators_bars">
                    <button type="button" aria-label="Carousel indicator" data-bs-target="#slideshow_3" data-bs-slide-to="0" class="active" style="background-image: url(/web/image/website.library_image_03)"></button>
                    <button type="button" aria-label="Carousel indicator" data-bs-target="#slideshow_3" data-bs-slide-to="1" style="background-image: url(/web/image/website.library_image_10)"></button>
                    <button type="button" aria-label="Carousel indicator" data-bs-target="#slideshow_3" data-bs-slide-to="2" style="background-image: url(/web/image/website.library_image_13)"></button>
                    <button type="button" aria-label="Carousel indicator" data-bs-target="#slideshow_3" data-bs-slide-to="3" style="background-image: url(/web/image/website.library_image_05)"></button>
                    <button type="button" aria-label="Carousel indicator" data-bs-target="#slideshow_3" data-bs-slide-to="4" style="background-image: url(/web/image/website.library_image_14)"></button>
                    <button type="button" aria-label="Carousel indicator" data-bs-target="#slideshow_3" data-bs-slide-to="5" style="background-image: url(/web/image/website.library_image_16)"></button>
                </div>
                <button class="carousel-control-next o_we_no_overlay o_not_editable" contenteditable="false" data-bs-slide="next" aria-label="Next" title="Next" data-bs-target="#slideshow_3">
                    <span class="carousel-control-next-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Next</span>
                </button>
            </div>
        </div>
    </main>
`;

// TODO Obtain rendering from `website.gallery.slideshow` template.
const defaultOldLightbox = `
    <main class="modal-body o_slideshow bg-transparent">
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close" style="position: absolute; right: 10px; top: 10px;">
        </button>
        <div class="carousel slide" style="margin: 0 12px;" id="slideshow_3" data-bs-ride="false" data-bs-interval="0">
            <div class="carousel-inner" style="padding: 0;">
                <div class="carousel-item active">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_03" alt="">
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_10" alt="">
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_13" alt="">
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_05" alt="">
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_14" alt="">
                </div>
                <div class="carousel-item undefined">
                    <img class="img img-fluid d-block" data-name="Image" src="/web/image/website.library_image_16" alt="">
                </div>
            </div>
            <ul class="carousel-indicators">
                <li class="o_indicators_left text-center d-none" aria-label="Previous" title="Previous">
                    <i class="oi oi-chevron-left"></i>
                </li>
                <li data-bs-target="#slideshow_3" data-bs-slide-to="0" class="" style="background-image: url(/web/image/website.library_image_03)"></li>
                <li data-bs-target="#slideshow_3" data-bs-slide-to="1" style="background-image: url(/web/image/website.library_image_10)" class=""></li>
                <li data-bs-target="#slideshow_3" data-bs-slide-to="2" style="background-image: url(/web/image/website.library_image_13)" class=""></li>
                <li data-bs-target="#slideshow_3" data-bs-slide-to="3" style="background-image: url(/web/image/website.library_image_05)" class="active" aria-current="true"></li><li data-bs-target="#slideshow_3" data-bs-slide-to="4" style="background-image: url(/web/image/website.library_image_14)"></li>
                <li data-bs-target="#slideshow_3" data-bs-slide-to="5" style="background-image: url(/web/image/website.library_image_16)" class=""></li>
                <li class="o_indicators_right text-center d-none" aria-label="Next" title="Next">
                    <i class="oi oi-chevron-right"></i>
                </li>
            </ul>
        </div>
    </main>
`;

test("gallery_slider does nothing if there is no o_slideshow s_image_gallery", async () => {
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <section class="s_image_gallery"/>
        </div>
    `);
    expect(core.interactions).toHaveLength(0);
});

test("gallery_slider interaction on image gallery", async () => {
    const { core, el } = await startInteractions(defaultGallery);
    expect(core.interactions).toHaveLength(1);
    await animationFrame();
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    const imgEl = el.querySelector(".carousel-item.active img");
    const goToEls = el.querySelectorAll("button[data-bs-slide-to]");
    await click(goToEls[2]);
    await animationFrame();
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    const img2El = el.querySelector(".carousel-item.active img");
    expect(imgEl).not.toBe(img2El);
});

test("gallery_slider interaction on lightbox", async () => {
    const { core, el } = await startInteractions(defaultLightbox);
    expect(core.interactions).toHaveLength(1);
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    const imgEl = el.querySelector(".carousel-item.active img");
    const nextEl = el.querySelector(".carousel-control-next");
    const goToEls = el.querySelectorAll("button[data-bs-slide-to]");
    await click(nextEl);
    await animationFrame();
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    const img2El = el.querySelector(".carousel-item.active img");
    expect(imgEl).not.toBe(img2El);
    await click(goToEls[2]);
    await animationFrame();
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    const img3El = el.querySelector(".carousel-item.active img");
    expect(imgEl).not.toBe(img3El);
    expect(img2El).not.toBe(img3El);
});

test("gallery_slider interaction on old lightbox", async () => {
    const { core, el } = await startInteractions(defaultOldLightbox);
    expect(core.interactions).toHaveLength(1);
    const interaction = core.interactions[0].interaction;
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    // Fix parameters that are based on sizes.
    interaction.page = 0;
    interaction.nbPages = 6;
    interaction.realNbPerPage = 1;
    const imgEl = el.querySelector(".carousel-item.active img");
    const nextEl = el.querySelector(".o_indicators_right");
    const goToEls = el.querySelectorAll("li[data-bs-slide-to]");
    await click(nextEl);
    await animationFrame();
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    const img2El = el.querySelector(".carousel-item.active img");
    expect(imgEl).not.toBe(img2El);
    await click(goToEls[2]);
    await animationFrame();
    await onceAllImagesLoaded(el);
    await advanceTime(SLIDE_DURATION);
    const img3El = el.querySelector(".carousel-item.active img");
    expect(imgEl).not.toBe(img3El);
    expect(img2El).not.toBe(img3El);
});
