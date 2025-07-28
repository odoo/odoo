import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { waitFor } from "@odoo/hoot-dom";

defineWebsiteModels();

test("test parallax zoom", async () => {
    await setupWebsiteAndOpenParallaxOptions();
    await contains("[data-action-value='zoomOut']").click();
    await waitFor("[data-label='Intensity'] input");
    expect(":iframe section").not.toHaveStyle("background-image", { inline: true });
    expect("[data-label='Intensity'] input").toBeVisible();
});
test("add parallax changes editing element", async () => {
    await setupWebsiteAndOpenParallaxOptions();
    await contains("[data-action-value='fixed']").click();
    await contains("[data-label='Position'] .dropdown-toggle").click();
    await contains("[data-action-value='repeat-pattern']").click();
    expect(":iframe section").not.toHaveClass("o_bg_img_opt_repeat");
    expect(":iframe section .s_parallax_bg").toHaveClass("o_bg_img_opt_repeat");
});
test("add parallax removes classes on the original editing element", async () => {
    await setupWebsiteAndOpenParallaxOptions({ editingElClasses: "o_modified_image_to_save" });
    await contains("[data-action-value='fixed']").click();
    expect(":iframe section").not.toHaveClass("o_modified_image_to_save");
    expect(":iframe section .s_parallax_bg").toHaveClass("o_modified_image_to_save");
});
test("remove parallax changes editing element", async () => {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    await setupWebsiteBuilder(`
        <section>
            <span class='s_parallax_bg oe_img_bg o_bg_img_center' style="background-image: ${backgroundImageUrl} !important;">aaa</span>
        </section>`);
    await contains(":iframe section").click();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    await contains("[data-action-value='none']").click();
    await contains("[data-label='Position'] .dropdown-toggle").click();
    await contains("[data-action-value='repeat-pattern']").click();
    expect(":iframe section").toHaveClass("o_bg_img_opt_repeat");
});

async function setupWebsiteAndOpenParallaxOptions({ editingElClasses = "" } = {}) {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    const editingElClass = editingElClasses ? `class=${editingElClasses}` : "";
    const websiteBuilder = await setupWebsiteBuilder(`
        <section ${editingElClass} style="background-image: ${backgroundImageUrl}; width: 500px; height:500px">
        </section>`);
    await contains(":iframe section").click();
    await contains("[data-label='Scroll Effect'] button.o-dropdown").click();
    return websiteBuilder;
}
