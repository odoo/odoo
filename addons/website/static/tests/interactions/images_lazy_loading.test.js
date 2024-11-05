import { expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { startInteractions, setupInteractionWhiteList } from "../core/helpers";
import {
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { ImagesLazyLoading } from "@website/interactions/images_lazy_loading";

setupInteractionWhiteList("website.images_lazy_loading");

test("images lazy loading removes height then restores it", async () => {
    const log = [];
    const oldUpdateImgMinHeight = ImagesLazyLoading.prototype.updateImgMinHeight;
    patchWithCleanup(ImagesLazyLoading.prototype, {
        updateImgMinHeight: function (imgEl, reset) {
            log.push({
                when: `before ${reset ? "reset" : "load"}`,
                backup: imgEl.dataset.lazyLoadingInitialMinHeight,
                style: imgEl.style.minHeight,
            });
            oldUpdateImgMinHeight.bind(this)(imgEl, reset);
            log.push({
                when: `after ${reset ? "reset" : "load"}`,
                backup: imgEl.dataset.lazyLoadingInitialMinHeight,
                style: imgEl.style.minHeight,
            });
        },
    });
    const { core, el } = await startInteractions(`
        <div>Fake surrounding
            <div id="wrapwrap">
                <img src="/web/image/website.library_image_08" loading="lazy" style="min-height: 100px;"/>
            </div>
        </div>
    `);
    expect(core.interactions.length).toBe(1);
    // Verify log.
    expect(log[0]).toEqual({
        when: "before load",
        backup: undefined,
        style: "100px",
    });
    expect(log[1]).toEqual({
        when: "after load",
        backup: "100px",
        style: "1px",
    });
    expect(log[2]).toEqual({
        when: "before reset",
        backup: "100px",
        style: "1px",
    });
    expect(log[3]).toEqual({
        when: "after reset",
        backup: undefined,
        style: "100px",
    });
    // Check final state.
    const imgEl = el.querySelector("img");
    expect(imgEl.dataset.lazyLoadingInitialMinHeight).toBe(undefined);
    expect(imgEl.style.minHeight).toBe("100px");
});
