import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryOne } from "@odoo/hoot-dom";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList(["website_sale.carousel_product"]);
describe.current.tags("interaction_dev");

test("scroll miniatures", async () => {
    defineStyle(/* css */`li { min-width: 64px !important; }`);
    const { core } = await startInteractions(`
        <div class="o_wsale_product_images position-relative" style="width: 600px" data-image-amount="16">
            <div id="o-carousel-product" data-bs-ride="true" class="o_carousel_not_single carousel slide position-sticky mb-3 overflow-hidden" data-name="Product Carousel">
                <div class="o_carousel_product_outer carousel-outer position-relative d-flex align-items-center w-100 overflow-hidden">
                    <span class="o_ribbon o_ribbon_right z-1" style=""></span>
                    <div class="carousel-inner h-100">
                        <div class="carousel-item h-100 text-center active">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_08" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                        <div class="carousel-item h-100 text-center">
                            <div class="d-flex align-items-center justify-content-center h-100 oe_unmovable"><img src="/web/image/website.library_image_01" class="img img-fluid oe_unmovable product_detail_img w-100 mh-100" loading="lazy" style=""></div>
                        </div>
                    </div>
                    <a class="carousel-control-prev" href="#o-carousel-product" role="button" data-bs-slide="prev">
                        <i class="oi oi-chevron-left oe_unmovable border bg-white text-900" role="img" aria-label="Previous" title="Previous"></i>
                    </a>
                    <a class="carousel-control-next" href="#o-carousel-product" role="button" data-bs-slide="next">
                        <i class="oi oi-chevron-right oe_unmovable border bg-white text-900" role="img" aria-label="Next" title="Next"></i>
                    </a>
                </div>
                <div class="o_carousel_product_indicators pt-2 overflow-hidden">
                    <ol class="carousel-indicators position-static pt-2 pt-lg-0 mx-auto my-0" style="justify-content: start;">
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative active" data-bs-slide-to="0" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="1" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="2" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="3" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="4" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="5" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="6" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="7" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="8" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="9" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="10" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="11" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="12" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="13" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="14" aria-current="true">
                            <div><img src="/web/image/website.library_image_08" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                        <li data-bs-target="#o-carousel-product" class="align-top position-relative" data-bs-slide-to="15" aria-current="true">
                            <div><img src="/web/image/website.library_image_01" class="img o_image_64_cover" loading="lazy" style=""></div>
                        </li>
                    </ol>
                </div>
            </div>
        </div>
    `);
    expect(core.interactions).toHaveLength(1);
    const olEl = queryOne(".carousel-indicators");
    expect(olEl.style.transform).toBe("");
    await click(`[data-bs-slide-to="15"]`);
    await animationFrame();
    expect(olEl.style.transform).toMatch(/translate3d(.*px, 0px, 0px)/);
});
