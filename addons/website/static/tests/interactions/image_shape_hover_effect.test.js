import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { hover, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { onceAllImagesLoaded } from "@website/utils/images";

setupInteractionWhiteList(["website.image_shape_hover_effect", "website.clickable_card"]);

describe.current.tags("interaction_dev");

test.tags("desktop");
test("image_shape_hover_effect changes image on enter & leave", async () => {
    patchWithCleanup(Image.prototype, {
        set onload(fn) {
            super.onload = fn;
            setTimeout(() => super.onload());
        },
    });
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <img class="img img-fluid mx-auto o_we_image_cropped o_animate_on_hover rounded-circle rounded"
                src="/web/image/384-8a55a748/s_banner_3.svg" alt=""
                data-mimetype="image/svg+xml" data-attachment-id="276" data-original-id="276"
                data-original-src="/website/static/src/img/snippets_demo/s_banner_3.jpg"
                data-mimetype-before-conversion="image/jpeg"
                data-shape="html_builder/geometric/geo_door" data-file-name="s_banner_3.svg"
                data-shape-colors=";;;;" data-format-mimetype="image/jpeg"
                data-x="160" data-y="0"
                data-width="640" data-height="640"
                data-scale-x="1" data-scale-y="1"
                data-aspect-ratio="1/1"
                data-hover-effect="dolly_zoom"
                data-hover-effect-color="rgba(0, 0, 0, 0)"
                data-hover-effect-intensity="20"/>
            <div class="not_image">Not the image</div>
        </div>
    `);
    onRpc(
        "/web/image/384-8a55a748/s_banner_3.svg",
        () =>
            `<svg viewBox="0 0 300 100" width="500px"><g id="hoverEffects"><animate values="a=1;b=2"><rect width="100%" fill="red" height="100%" /></animate></g></svg>`
    );
    expect(core.interactions).toHaveLength(1);
    await onceAllImagesLoaded(queryOne("#wrapwrap"));
    const imgEl = queryOne("img");
    const baseSrc = imgEl.getAttribute("src");
    expect(imgEl).toHaveAttribute("src", "/web/image/384-8a55a748/s_banner_3.svg");
    await hover(imgEl);
    await advanceTime(1);
    const altSrc = imgEl.getAttribute("src");
    expect(imgEl).not.toHaveAttribute("src", baseSrc);
    await hover(".not_image");
    await advanceTime(1);
    expect(imgEl).not.toHaveAttribute("src", baseSrc);
    expect(imgEl).not.toHaveAttribute("src", altSrc);
});

test.tags("desktop");
test("image_shape_hover_effect is triggered from stretched-link hover", async () => {
    patchWithCleanup(Image.prototype, {
        set onload(fn) {
            super.onload = fn;
            setTimeout(() => super.onload());
        },
    });
    const { core } = await startInteractions(`
        <div id="wrapwrap">
            <div class="s_card o_card_img_top card o_cc o_cc1" data-vxml="001">
                <a class="stretched-link" href="#top"></a>
                <figure class="o_card_img_wrapper ratio ratio-16x9 mb-0">
                    <img class="img img-fluid mx-auto o_we_image_cropped o_animate_on_hover rounded-circle rounded"
                        src="/web/image/384-8a55a748/s_banner_3.svg" alt=""
                        data-mimetype="image/svg+xml" data-attachment-id="276" data-original-id="276"
                        data-original-src="/website/static/src/img/snippets_demo/s_banner_3.jpg"
                        data-mimetype-before-conversion="image/jpeg"
                        data-shape="html_builder/geometric/geo_door" data-file-name="s_banner_3.svg"
                        data-shape-colors=";;;;" data-format-mimetype="image/jpeg"
                        data-x="160" data-y="0"
                        data-width="640" data-height="640"
                        data-scale-x="1" data-scale-y="1"
                        data-aspect-ratio="1/1"
                        data-hover-effect="dolly_zoom"
                        data-hover-effect-color="rgba(0, 0, 0, 0)"
                        data-hover-effect-intensity="20"/>
                </figure>
                <div class="card-body">
                    <h3 class="card-title h5-fs">Card title</h3>
                    <p class="card-text">A card is a flexible and extensible content container. It includes options for headers and footers, a wide variety of content, contextual background colors, and powerful display options.</p>
                    <a t-att-href="cta_btn_href">Discover</a>
                </div>
            </div>
            <div class="not_image">Not the image</div>
        </div>
    `);
    onRpc(
        "/web/image/384-8a55a748/s_banner_3.svg",
        () =>
            `<svg viewBox="0 0 300 100" width="500px"><g id="hoverEffects"><animate values="a=1;b=2"><rect width="100%" fill="red" height="100%" /></animate></g></svg>`
    );
    expect(core.interactions).toHaveLength(2);
    await onceAllImagesLoaded(queryOne("#wrapwrap"));
    const imgEl = queryOne("img");
    const baseSrc = imgEl.getAttribute("src");
    expect(imgEl).toHaveAttribute("src", "/web/image/384-8a55a748/s_banner_3.svg");

    await hover("figure > img");
    await advanceTime(1);
    const hoverSrc = imgEl.getAttribute("src");
    expect(imgEl).not.toHaveAttribute("src", baseSrc);

    await hover(".stretched-link");
    await advanceTime(1);
    expect(imgEl).not.toHaveAttribute("src", baseSrc);
    expect(imgEl).not.toHaveAttribute("src", hoverSrc);

    await hover(".not_image");
    await advanceTime(1);
    expect(imgEl).not.toHaveAttribute("src", baseSrc);
    expect(imgEl).not.toHaveAttribute("src", hoverSrc);
});
