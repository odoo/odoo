export const defaultCarouselStyleSnippet = (bsRide, bsInterval) => /*xml*/ `
    <section class="s_carousel_wrapper p-0" data-snippet="s_carousel" data-vcss="001">
        <div id="slideshow_sample" class="s_carousel s_carousel_default carousel slide o_colored_level" data-bs-ride="${bsRide}" data-bs-interval="${bsInterval}">
            <div class="o_carousel_controllers">
                <button class="carousel-control-prev o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                    <span class="carousel-control-prev-icon" aria-hidden="true"/>
                    <span class="visually-hidden">Previous</span>
                </button>
                <div class="carousel-indicators">
                    <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="0" class="o_not_editable active">
                        <span class="visually-hidden">Slide 1 of 3</span>
                        <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="/web/image/website.landscape_md_5"/>
                    </button>
                    <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="1" class="o_not_editable">
                        <span class="visually-hidden">Slide 2 of 3</span>
                        <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="/web/image/website.set_2_square_md_1"/>
                    </button>
                    <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="2" class="o_not_editable">
                        <span class="visually-hidden">Slide 3 of 3</span>
                        <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="/web/image/website.landscape_md_1"/>
                    </button>
                </div>
                <button class="carousel-control-next o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="next" aria-label="Next" title="Next">
                    <span class="carousel-control-next-icon" aria-hidden="true"/>
                    <span class="visually-hidden">Next</span>
                </button>
            </div>
            <div class="carousel-inner">
                <div class="carousel-item active">
                    <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.landscape_md_5" data-name="Image" data-index="0" alt=""/>
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.set_2_square_md_1" data-name="Image" data-index="1" alt=""/>
                </div>
                <div class="carousel-item">
                    <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.landscape_md_1" data-name="Image" data-index="2" alt=""/>
                </div>
            </div>
        </div>
    </section>`;

export const imageGalleryCarouselStyleSnippet = (bsRide, bsInterval) => /*xml*/ `
    <section class="s_image_gallery o_slideshow pt24 pb24 s_image_gallery_controllers_outside s_image_gallery_controllers_outside_arrows_right s_image_gallery_indicators_dots s_image_gallery_arrows_default" data-snippet="s_image_gallery" data-vcss="002" data-columns="3">
        <div class="o_container_small overflow-hidden">
            <div id="slideshow_sample" class="carousel carousel-dark slide" data-bs-ride="${bsRide}" data-bs-interval="${bsInterval}">
                <div class="o_carousel_controllers">
                    <button class="carousel-control-prev o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="prev" aria-label="Previous" title="Previous">
                        <span class="carousel-control-prev-icon" aria-hidden="true"/>
                        <span class="visually-hidden">Previous</span>
                    </button>
                    <div class="carousel-indicators">
                        <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="0" class="o_not_editable active">
                            <span class="visually-hidden">Slide 1 of 3</span>
                            <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="/web/image/website.landscape_md_5"/>
                        </button>
                        <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="1" class="o_not_editable">
                            <span class="visually-hidden">Slide 2 of 3</span>
                            <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="/web/image/website.set_2_square_md_1"/>
                        </button>
                        <button type="button" data-bs-target="#slideshow_sample" data-bs-slide-to="2" class="o_not_editable">
                            <span class="visually-hidden">Slide 3 of 3</span>
                            <img class="object-fit-cover w-100 h-100" aria-hidden="true" src="/web/image/website.landscape_md_1"/>
                        </button>
                    </div>
                    <button class="carousel-control-next o_not_editable" contenteditable="false" data-bs-target="#slideshow_sample" data-bs-slide="next" aria-label="Next" title="Next">
                        <span class="carousel-control-next-icon" aria-hidden="true"/>
                        <span class="visually-hidden">Next</span>
                    </button>
                </div>
                <div class="carousel-inner">
                    <div class="carousel-item active">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.landscape_md_5" data-name="Image" data-index="0" alt=""/>
                    </div>
                    <div class="carousel-item">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.set_2_square_md_1" data-name="Image" data-index="1" alt=""/>
                    </div>
                    <div class="carousel-item">
                        <img class="img img-fluid d-block mh-100 mw-100 mx-auto rounded object-fit-cover" src="/web/image/website.landscape_md_1" data-name="Image" data-index="2" alt=""/>
                    </div>
                </div>
            </div>
        </div>
    </section>`;
