import { describe, expect, test } from "@odoo/hoot";
import { click, dblclick, queryOne, setInputFiles, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Icon styles should be retained when it is replaced with another icon", async () => {
    const extractClasses = "rounded-circle rounded shadow img-thumbnail";
    await setupWebsiteBuilder(`<i class="oi ${extractClasses}" data-icon="search"/>`);

    await dblclick(":iframe .oi");
    await waitFor(".o-IconPicker");
    expect(".o_select_media_dialog").toHaveCount(0);
    await click(".o-IconPicker-icon[data-icon=favorite]:not(.oi-filled)");
    await animationFrame();
    expect(":iframe [data-icon=favorite]").toHaveClass(extractClasses);
});

test("The Replace option of an icon opens the icon picker", async () => {
    await setupWebsiteBuilder(`<p><i class="oi" data-icon="search"></i></p>`);
    await click(":iframe .oi");
    await contains("[data-action-id=replaceMedia]").click();
    await waitFor(".o-IconPicker");
    expect(".o_select_media_dialog").toHaveCount(0);
    await click(".o-IconPicker-icon[data-icon=favorite].oi-filled");
    await animationFrame();
    expect(".o-IconPicker").toHaveCount(0);
    expect(":iframe .oi").toHaveAttribute("data-icon", "favorite");
    expect(":iframe .oi").toHaveClass("oi-filled");
});

test("The icons of the social media snippet are replaced from the icon picker", async () => {
    await setupWebsiteBuilder(
        `<div class="s_social_media" data-snippet="s_social_media">
            <a href="https://www.example.com"><i class="oi" data-icon="search"/></a>
        </div>`
    );
    await dblclick(":iframe .s_social_media .oi");
    await waitFor(".o-IconPicker");
    expect(".o_select_media_dialog").toHaveCount(0);
});

test("The images of the social media snippet are only replaced by images", async () => {
    await setupWebsiteBuilder(
        `<div class="s_social_media" data-snippet="s_social_media">
            <a href="https://www.example.com"><img class="social_media_img" src="/web/static/img/logo.png"/></a>
        </div>`
    );
    await dblclick(":iframe .s_social_media img");
    await waitFor(".o_select_media_dialog");
    expect(".o_select_media_dialog .o_notebook_headers .nav-link").toHaveCount(1);
    expect(".o_select_media_dialog .o_notebook_headers .nav-link").toHaveText("Images");
});

function mockIconFontCustomization() {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            // Stand in for the recompiled bundle, which prints the customized
            // SCSS variable as a CSS variable on the website `:root`.
            queryOne(":iframe html").style.setProperty(
                "--icon-font-family",
                `'${changes["icon-font-family"]}'`
            );
        }
    }
    defineModels([WebsiteAssets]);
    onRpc("/website/theme_customize_bundle_reload", () => ({}));
}

test("Replace an icon by an image uploaded from the icon picker", async () => {
    onRpc("/html_editor/attachment/add_data", () => ({
        id: 1,
        name: "image.png",
        mimetype: "image/png",
        image_src: "/web/static/img/logo.png",
        public: true,
    }));
    await setupWebsiteBuilder(`<p><i class="oi rounded-circle shadow" data-icon="search"></i></p>`);
    await dblclick(":iframe .oi");
    await waitFor(".o-IconPicker-upload");
    await click(".o-IconPicker-upload");
    await setInputFiles([new File(["image"], "image.png", { type: "image/png" })]);
    await waitFor(":iframe img[data-attachment-id='1']");
    expect(":iframe .oi").toHaveCount(0);
    expect(":iframe img").toHaveClass(["img", "img-fluid", "rounded-circle", "shadow"]);
    await waitFor(".o_customize_tab [data-container-title='Image']");
});

describe("Icon styles", () => {
    test("Use the icon font selected in the theme options", async () => {
        mockIconFontCustomization();
        await setupWebsiteBuilder(`<i class="oi" data-icon="search"/>`);
        await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
        await contains(".o_theme_tab [data-action-param='icon-font-family'][data-action-value='Material Symbols Sharp']").click();
        await dblclick(":iframe .oi");
        await waitFor(".o-IconPicker-icon[data-icon='favorite']");
        expect(".o-IconPicker-icon[data-icon='favorite']").toHaveStyle({
            fontFamily: /Material Symbols Sharp/,
        });
        // Odoo custom icons have their own font, whatever the selected variant.
        expect(".o-IconPicker-icon[data-icon^='oi_']").toHaveCount(null, {
            message: "Odoo custom icons are listed",
        });
        expect(".o-IconPicker-icon[data-icon^='oi_']").toHaveStyle({ fontFamily: /odoo_ui_icons/ });
    });

    test("Icons use the outlined font with the default theme options", async () => {
        await setupWebsiteBuilder(`<i class="oi" data-icon="search"/>`);
        await dblclick(":iframe .oi");
        await waitFor(".o-IconPicker-icon[data-icon='favorite']");
        expect(".o-IconPicker-icon[data-icon='favorite']").toHaveStyle({
            fontFamily: /Material Symbols Outlined/,
        });
        expect(".o-IconPicker-icon[data-icon^='oi_']").toHaveStyle({ fontFamily: /odoo_ui_icons/ });
    });
});

test("Video size should be retained when the video or its options are changed", async () => {
    const videoUrl = "//www.youtube.com/embed/qxb74CMR748";
    onRpc("/html_editor/video_url/data", () => ({ platform: "youtube", embed_url: videoUrl }));
    await setupWebsiteBuilder(
        `<div class="media_iframe_video" data-oe-expression="${videoUrl}"
            style="width: 50% !important;"/>`
    );

    await dblclick(":iframe .media_iframe_video");
    await contains(".o_video_dialog_options input[type='checkbox']").click();
    await contains(".modal-footer .btn-primary").click();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "50% !important" },
        { inline: true }
    );
});
