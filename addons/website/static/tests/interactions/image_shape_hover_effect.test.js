import { describe, expect, test } from "@odoo/hoot";
import { hover } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { MockServer } from "@web/../tests/_framework/mock_server/mock_server";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { onceAllImagesLoaded } from "@website/utils/images";

setupInteractionWhiteList("website.image_shape_hover_effect");
describe.current.tags("interaction_dev");

test.tags("desktop")("image shape hover effect changes image on enter & leave", async () => {
    patchWithCleanup(Image.prototype, {
        set onload(fn) {
            super.onload = fn;
            setTimeout(() => {
                super.onload();
            });
        }
    });
    const { core, el } = await startInteractions(`
        <div id="wrapwrap">
            <img class="img img-fluid mx-auto o_we_image_cropped o_animate_on_hover rounded-circle rounded"
                src="/web/image/384-8a55a748/s_banner_3.svg" alt=""
                data-mimetype="image/svg+xml" data-original-id="276"
                data-original-src="/website/static/src/img/snippets_demo/s_banner_3.jpg"
                data-mimetype-before-conversion="image/jpeg"
                data-shape="web_editor/geometric/geo_door" data-file-name="s_banner_3.svg"
                data-shape-colors=";;;;" data-original-mimetype="image/jpeg"
                data-x="160.00000000000003" data-y="-5.3290705182007514e-14"
                data-width="640" data-height="640"
                data-scale-x="1" data-scale-y="1"
                data-aspect-ratio="1/1"
                data-hover-effect="dolly_zoom"
                data-hover-effect-color="rgba(0, 0, 0, 0)"
                data-hover-effect-intensity="20"
            />
            <div class="not_image">Not the image</div>
        </div>
    `);
    MockServer.current.onRoute(["/web/image/384-8a55a748/s_banner_3.svg"], (x) => {
        return `<svg viewBox="0 0 300 100" width="500px"><g id="hoverEffects"><animate values="a=1;b=2"><rect width="100%" fill="red" height="100%" /></animate></g></svg>`;
    }, { pure: true });
    expect(core.interactions.length).toBe(1);
    await onceAllImagesLoaded(el);
    const imgEl = el.querySelector("img");
    const baseSrc = imgEl.getAttribute("src");
    expect(baseSrc).toBe("/web/image/384-8a55a748/s_banner_3.svg");
    await hover(imgEl);
    await advanceTime(1);
    const altSrc = imgEl.getAttribute("src");
    expect(altSrc).not.toBe(baseSrc);
    const notImageEl = el.querySelector(".not_image");
    await hover(notImageEl);
    await advanceTime(1);
    const restoredSrc = imgEl.getAttribute("src");
    expect(restoredSrc).not.toBe(baseSrc);
    expect(restoredSrc).not.toBe(altSrc);
});
