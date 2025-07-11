import { expect, test } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Img } from "@html_builder/core/img";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { animationFrame, Deferred } from "@odoo/hoot-dom";

defineMailModels(); // meh
test("Img component should not be blocked before src load", async () => {
    const def = new Deferred();
    patchWithCleanup(Img.prototype, {
        loadImage() {
            return Promise.all([super.loadImage(), def]);
        },
    });
    await mountWithCleanup(Img, { props: { src: "" } });
    expect(".o-img-placeholder").toHaveCount(1);
    expect("img").toHaveCount(0);
    def.resolve();
    await animationFrame();
    expect(".o-img-placeholder").toHaveCount(0);
    expect("img").toHaveCount(1);
});
