import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { BackgroundPositionOverlay } from "@html_builder/plugins/background_option/background_position_overlay";
import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

test("show and leave the 'BackgroundShapeComponent'", async () => {
    await setupWebsiteBuilder(`<section>AAAA</section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='toggleBgShape']").click();
    await contains("button.o_pager_nav_angle").click();
    await animationFrame();
    expect("button[data-action-id='toggleBgShape']").toBeVisible();
});

test("change the background shape of elements", async () => {
    addOption({
        selector: ".selector",
        applyTo: ".applyTo",
        Component: BackgroundOption,
        props: {
            withColors: true,
            withImages: true,
            // todo: handle with_videos
            withShapes: true,
            withColorCombinations: false,
        },
    });
    await setupWebsiteBuilder(`
        <div class="selector">
            <div id="first" class="applyTo" data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                AAAA
            </div>
            <div id="second" class="applyTo" data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                BBBB
            </div>
        </div>`);
    await contains(":iframe .selector").click();
    await contains("[data-label='Shape'] button").click();
    await contains(
        ".o_pager_container .o-hb-bg-shape-btn:nth-child(2) [data-action-id='setBackgroundShape']"
    ).click();
    expect(":iframe .selector div#first").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"web_editor/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
    expect(":iframe .selector div#second").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"web_editor/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
});

test("remove background shape", async () => {
    await setupWebsiteBuilder(`
        <section data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            AAAA
        </section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='setBackgroundShape']").click();
    expect(":iframe section").not.toHaveAttribute("data-oe-shape-data");
    expect("button[data-action-id='setBackgroundShape']").not.toHaveCount();
});

test("toggle Show/Hide on mobile of the shape background", async () => {
    await setupWebsiteBuilder(`
        <section data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_web_editor_Connections_01">
                AAAA
            </div>
        </section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='showOnMobile']").click();
    expect(":iframe section .o_we_shape").toHaveClass("o_shape_show_mobile");
    await contains("button[data-action-id='showOnMobile']").click();
    expect(":iframe section .o_we_shape").not.toHaveClass("o_shape_show_mobile");
});

test("Check if an element with a background image has necessary classes", async () => {
    await setupWebsiteBuilder(`
        <section class="s_banner overflow-hidden" style="background-color:(0, 0, 0, 0);
                background-image: url(&quot;/website_slides/static/src/img/banner_default.svg&quot;); height: 300px" data-snippet="s_banner">
            AAA
        </section>`);
    await contains(":iframe section").click();
    expect(":iframe section").toHaveClass("oe_img_bg");
    expect(":iframe section").toHaveClass("o_bg_img_center");
    expect(":iframe section").toHaveClass("o_bg_img_origin_border_box");
});

test("Change the background position and apply", async () => {
    await dragAndDropBgImage();
    await contains(".overlay .btn-primary").click();
    expect("button.fa-undo").toBeEnabled();
});

test("Change the background position and discard", async () => {
    await dragAndDropBgImage();
    await contains(".overlay .btn-primary").click();
    expect("button.fa-undo").toBeEnabled();
});

test("Change the background position and click out of the iframe", async () => {
    await dragAndDropBgImage();
    await contains(".o_customize_tab").click();
    expect("button.fa-undo").not.toBeEnabled();
});

async function dragAndDropBgImage() {
    patchWithCleanup(BackgroundPositionOverlay.prototype, {
        onDragBackgroundMove(ev) {
            const movementX = ev.clientX === 200 ? 1 : 0;
            const movementY = ev.clientY === 200 ? 1 : 0;
            // Mock the movementX and movementY readonly property
            const newEv = {
                preventDefault: () => {},
                movementX: movementX,
                movementY: movementY,
            };
            super.onDragBackgroundMove(newEv);
        },
    });
    await setupWebsiteBuilder(`
        <section style="background-image: url('/web/image/123/transparent.png'); width: 500px; height:500px">
            <div class="o_we_shape o_web_editor_Connections_01">
                AAAA
            </div>
        </section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='backgroundPositionOverlay']").click();

    const sectionOverlaySelector = ".overlay .o_overlay_background section";
    await waitFor(sectionOverlaySelector);
    expect(sectionOverlaySelector).not.toHaveStyle("background-position", { inline: true });
    const dragActions = await contains(sectionOverlaySelector).drag({
        position: { x: 199, y: 199 },
    });
    await dragActions.moveTo(sectionOverlaySelector, { position: { x: 200, y: 200 } });
    await dragActions.drop();
}

test("change the main color of a background image of type '/html_editor/shape'", async () => {
    await setupWebsiteBuilder(
        `
            <section style="background-image: url('/web_editor/shape/http_routing/404.svg?c2=o-color-2');">
                AAAA
            </section>
        `,
        {
            loadIframeBundles: true,
        }
    );
    await contains(":iframe section").click();
    await contains("[data-label='Main Color'] .o_we_color_preview").click();
    await contains(
        ".o-main-components-container .o_colorpicker_section [data-color='o-color-5']"
    ).hover();
    expect(":iframe section").toHaveStyle({
        backgroundImage: `url("${window.location.origin}/web_editor/shape/http_routing/404.svg?c2=o-color-5")`,
    });
    await contains(
        ".o-main-components-container .o_colorpicker_section [data-color='o-color-4']"
    ).hover();
    expect(":iframe section").toHaveStyle({
        backgroundImage: `url("${window.location.origin}/web_editor/shape/http_routing/404.svg?c2=o-color-4")`,
    });
});

test("open the media dialog to toggle the image background but do not choose an image", async () => {
    await setupWebsiteBuilder(`
        <section>
            AAAA
        </section>`);
    await contains(":iframe section").click();
    await contains("[data-action-id='toggleBgImage']").click();
    await contains(".modal button.btn-close").click();
    await contains("[data-action-id='toggleBgImage']").click();
    expect(".modal").toBeDisplayed();
});

test("remove the background image of a snippet", async () => {
    const { waitDomUpdated } = await setupWebsiteBuilder(`
        <section style="background-image: url('/web/image/123/transparent.png'); width: 500px; height:500px">
            <div class="o_we_shape o_web_editor_Connections_01">
                AAAA
            </div>
        </section>`);
    await contains(":iframe section").click();
    expect(":iframe section").toHaveStyle("backgroundImage");
    await contains("[data-action-id='toggleBgImage']").click();
    await waitDomUpdated();
    expect(":iframe section").not.toHaveStyle("backgroundImage", { inline: true });
});

test("changing shape's background color doesn't hide the shape itself", async () => {
    await setupWebsiteBuilder(
        `<section style="background-image: url('/web_editor/shape/http_routing/404.svg?c2=o-color-2');">
            AAAA
        </section>`,
        {
            loadIframeBundles: true,
        }
    );
    await contains(":iframe section").click();
    await contains("button[data-action-id='toggleBgShape']").click();
    await contains(
        ".o_pager_container .o-hb-bg-shape-btn [data-action-value='web_editor/Connections/01'][data-action-id='setBackgroundShape']"
    ).click();
    const backgroundImageValue = getComputedStyle(queryOne(":iframe .o_we_shape")).backgroundImage;
    expect(backgroundImageValue).toMatch(/Connections\/01/);
    await contains("[data-label='Colors'] button:nth-child(2)").click();
    await contains(".o_colorpicker_section button[data-color='o-color-1']").click();
    expect(":iframe .o_we_shape").toHaveStyle({ backgroundImage: backgroundImageValue });
});

test("remove background image removes color filter", async () => {
    const backgroundImageUrl = "url('/web/image/123/transparent.png')";
    await setupWebsiteBuilder(`
        <section>
            <span class='s_parallax_bg oe_img_bg o_bg_img_center' style="background-image: ${backgroundImageUrl} !important;">aaa</span>
            <div class="o_we_bg_filter bg-black-50 o-paragraph"><br></div>
        </section>`);
    await contains(":iframe section").click();
    await contains("[data-action-id='toggleBgImage']").click();
    expect(":iframe section .o_we_bg_filter").not.toHaveCount();
});
