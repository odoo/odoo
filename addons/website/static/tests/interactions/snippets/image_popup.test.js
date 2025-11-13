import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, press, queryAll } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

setupInteractionWhiteList(["website.image_popup", "website.base_lightbox"]);

describe.current.tags("interaction_dev");

const defaultImage = `
    <img src="/web/image/website.s_picture_default_image" class="figure-img img-fluid rounded o_image_popup" alt=""/>
`;
test("image won't open in pop-up if there is no 'o_image_popup' class in img element", async () => {
    const { core } = await startInteractions(`
        <img src="/web/image/website.s_picture_default_image" class="figure-img img-fluid rounded" alt=""/>
    `);
    expect(core.interactions).toHaveLength(0);
});

async function checkLightbox({ close }) {
    const { core } = await startInteractions(defaultImage);
    expect(core.interactions).toHaveLength(1);
    const imgEl = queryAll("img");
    await click(imgEl);
    await animationFrame();
    await advanceTime(1000);
    const lightboxEl = document.querySelector(".o_image_lightbox");
    expect(lightboxEl).not.toBe(null);
    await close(lightboxEl);
    await animationFrame();
    await advanceTime(1000);
    expect(document.querySelector(".o_image_lightbox")).toBe(null);
}

test("image interaction opens lightbox on click, then use keyboard", async () => {
    await checkLightbox({
        close: async () => await press("Escape", { code: "Escape" }),
    });
});

test("image interaction opens lightbox on click, then use mouse", async () => {
    await checkLightbox({
        close: async (lightboxEl) => await click(lightboxEl.querySelector(".btn-close")),
    });
});
