import { describe, expect, test } from "@odoo/hoot";
import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ImageLazyLoading } from "@website/interactions/image_lazy_loading";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList("website.image_lazy_loading");
describe.current.tags("interaction_dev");

test("images lazy loading removes height then restores it", async () => {
    patchWithCleanup(ImageLazyLoading.prototype, {
        async willStart() {
            await super.willStart();
            await new Promise(resolve => {
                setTimeout(resolve, 100)
            });
        }
    });
    const { core, el } = await startInteractions(`
        <div>Fake surrounding
            <div id="wrapwrap">
                <img src="/web/image/website.library_image_08" loading="lazy" style="min-height: 100px;"/>
            </div>
        </div>
    `, { waitForStart: false});
    expect(core.interactions.length).toBe(1);
    const img = el.querySelector("img");
    expect(img.outerHTML).toBe(`<img src="/web/image/website.library_image_08" loading="lazy" style="min-height: 1px;">`);
    await advanceTime(200);
    expect(img.outerHTML).toBe(`<img src="/web/image/website.library_image_08" loading="lazy" style="min-height: 100px;">`);
});
