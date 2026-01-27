import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { BackgroundPositionOverlay } from "@html_builder/plugins/background_option/background_position_overlay";
import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne, scroll, waitFor } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addPlugin,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

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
        Component: class TestBackgroundOption extends BackgroundOption {
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                // todo: handle with_videos
                withShapes: true,
                withColorCombinations: false,
            };
        },
    });
    await setupWebsiteBuilder(`
        <div class="selector">
            <div id="first" class="applyTo" data-oe-shape-data='{"shape":"html_builder/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                AAAA
            </div>
            <div id="second" class="applyTo" data-oe-shape-data='{"shape":"html_builder/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
                BBBB
            </div>
        </div>`);
    await contains(":iframe .selector").click();
    await contains("[data-label='Shape'] button").click();
    expect(
        ".o_pager_container .o-hb-bg-shape-btn:nth-child(1) .btn.active[data-action-id='setBackgroundShape']"
    ).toHaveCount();
    await contains(
        ".o_pager_container .o-hb-bg-shape-btn:nth-child(2) .btn:not(.active)[data-action-id='setBackgroundShape']"
    ).click();
    expect(":iframe .selector div#first").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"html_builder/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
    expect(":iframe .selector div#second").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"html_builder/Connections/02","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
});

test("remove background shape", async () => {
    await setupWebsiteBuilder(`
        <section data-oe-shape-data='{"shape":"html_builder/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            AAAA
        </section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='setBackgroundShape']").click();
    expect(":iframe section").not.toHaveAttribute("data-oe-shape-data");
    expect("button[data-action-id='setBackgroundShape']").not.toHaveCount();
});

test("toggle Show/Hide on mobile of the shape background", async () => {
    await setupWebsiteBuilder(`
        <section data-oe-shape-data='{"shape":"html_builder/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Connections_01">
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
    await contains(".o_we_background_position_overlay .btn-primary").click();
    expect(".o_we_background_position_overlay").toHaveCount(0);
    expect("button.fa-undo").toBeEnabled();
});

test("Change the background position and discard", async () => {
    await dragAndDropBgImage();
    await contains(".o_we_background_position_overlay .btn-danger").click();
    expect(".o_we_background_position_overlay").toHaveCount(0);
    expect("button.fa-undo").not.toBeEnabled();
});

test("Change the background position and click out of the iframe", async () => {
    await dragAndDropBgImage();
    await contains(".o_customize_tab").click();
    expect(".o_we_background_position_overlay").toHaveCount(0);
    expect("button.fa-undo").not.toBeEnabled();
});

test("Background position overlay layout", async () => {
    expect.assertions(18);

    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(
        `<section>
            <div class="container">
                <section style="background-image: url('/web/image/123/transparent.png'); width: 500px; height: 500px">
                </section>
            </div>
        </section>`
    );

    const iframe = getEditor().editable.ownerDocument.defaultView.frameElement;
    const body = queryOne(":iframe body");
    const section = queryOne(":iframe .container section");

    const testLayout = async (mobile) => {
        // In mobile preview, the iframe is scaled by the o-mobile-phone SCSS mixin.
        // This mixin creates multiple similar CSS rules with different scales
        // that activate depending on the screen size.
        // The following scale of 0.87 is just one of them. It is here to have
        // a more representative test.
        const iframeContainerScale = mobile ? 0.87 : 1.0;
        if (mobile) {
            const iframeContainer = queryOne(".o_website_preview.o_is_mobile .o_iframe_container");
            iframeContainer.style.transform = `translate(-50%, -50%) scale(${iframeContainerScale})`;
        }
        await openBgPositionOverlay(section, waitSidebarUpdated);

        // The overlay should cover exactly the iframe
        const iframeRect = iframe.getBoundingClientRect();
        const bgOverlayRect = queryOne(".o_we_background_position_overlay").getBoundingClientRect();
        expect(bgOverlayRect.left).toBeCloseTo(iframeRect.left);
        expect(bgOverlayRect.top).toBeCloseTo(iframeRect.top);
        expect(bgOverlayRect.width).toBeCloseTo(body.clientWidth * iframeContainerScale);
        expect(bgOverlayRect.height).toBeCloseTo(body.clientHeight * iframeContainerScale);

        // The content of the overlay should cover the editing element
        const editingElementRect = section.getBoundingClientRect();
        const overlayContentStyle = getComputedStyle(queryOne(".o_we_overlay_content"));
        expect(parseFloat(overlayContentStyle.left)).toBeCloseTo(
            editingElementRect.left * iframeContainerScale
        );
        expect(parseFloat(overlayContentStyle.top)).toBeCloseTo(
            editingElementRect.top * iframeContainerScale
        );
        expect(parseFloat(overlayContentStyle.width)).toBeCloseTo(
            editingElementRect.width * iframeContainerScale
        );
        expect(parseFloat(overlayContentStyle.height)).toBeCloseTo(
            editingElementRect.height * iframeContainerScale
        );

        // The loading spinner should not be displayed
        expect(":iframe .o_loading_screen").not.toHaveClass("o_we_ui_loading");
    };

    await testLayout(false);
    await contains("button[data-action=mobile]").click();
    await testLayout(true);
});

test("Background position overlay behavior", async () => {
    expect.assertions(8);

    const movement = 50;
    const positionStartDrag = { x: 100, y: 100 };
    const { startDrag, endDrag } = patchDragBackground(
        ".o-overlay-container .o_we_background_dragger",
        positionStartDrag,
        { x: positionStartDrag.x + movement, y: positionStartDrag.y + movement }
    );

    const drag = async () => {
        const dragActions = await startDrag();
        expect(".o-overlay-container .o_we_background_position_overlay").toHaveClass(
            "o_we_grabbing"
        );
        await endDrag(dragActions);
    };

    const getBgPosPercent = (el) => {
        const positions = getComputedStyle(el).backgroundPosition.split(" ");
        return {
            x: parseFloat(positions[0]),
            y: parseFloat(positions[1]),
        };
    };

    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(
        `<section>
            <div class="container">
                <section style="background-image: url('/web/image/123/transparent.png'); width: 500px;">
                </section>
            </div>
        </section>`,
        {
            // Load the CSS related to the Scroll Effect
            loadIframeBundles: true,
        }
    );

    // Force the dimensions of the web client in order to have consistent result
    // values after dragging. The "Fixed" Scroll Effect is applied only when the
    // iframe is wider than 1200px.
    Object.assign(document.querySelector(".o_web_client").style, {
        left: "0px",
        top: "0px",
        width: "2000px",
        height: "900px",
        transform: "none",
    });

    const section = queryOne(":iframe .container section");
    // Make sure we can scroll
    section.style.height = "1000px";

    await openBgPositionOverlay(section, waitSidebarUpdated);

    // Scrolling on the overlay should scroll the iframe
    await scroll(queryOne(".o_we_background_position_overlay"), { y: 50 }, { scrollable: false });
    await animationFrame();
    expect(":iframe body").toHaveProperty("scrollTop", 50);

    // The Scroll Effect should be set to "None"
    expect("[data-label='Scroll Effect'] button").toHaveText("None");
    await openBgPositionOverlay(section, waitSidebarUpdated);
    expect(section).toHaveClass("o_we_background_positioning");

    // Drag and check that the background moves properly
    await drag();
    const sectionRect = section.getBoundingClientRect();
    // Delta X obtained by applying the formula in getBackgroundDelta of BackgroundPositionOverlay
    const deltaX = sectionRect.width - sectionRect.height;
    expect(getBgPosPercent(section).x).toBeCloseTo(
        // Formula derived from the one in onDragBackgroundMove of BackgroundPositionOverlay
        // 50% being the starting position
        50 + (movement / deltaX) * 100,
        {
            message:
                "Background X position should be dragged correctly with Scroll Effect set to None ",
        }
    );

    // Set Scroll Effect to "Fixed"
    await contains("[data-label='Scroll Effect'] button").click();
    await contains("[data-action-value='fixed']").click();
    await openBgPositionOverlay(section, waitSidebarUpdated);
    // The element with the background is not the section when the Scroll Effect is not "None".
    // However the section (i.e. its parent element) needs to have this class set to hide its content.
    expect(section).toHaveClass("o_we_background_positioning");

    // Drag and check that the background moves properly
    await drag();
    const iframe = getEditor().editable.ownerDocument.defaultView.frameElement;
    const iframeRect = iframe.getBoundingClientRect();
    // Delta Y obtained by applying the formula in getBackgroundDelta of BackgroundPositionOverlay
    const deltaY = iframeRect.height - iframeRect.width;
    expect(getBgPosPercent(queryOne(":iframe .s_parallax_bg")).y).toBeCloseTo(
        // Formula derived from the one in onDragBackgroundMove of BackgroundPositionOverlay
        // 50% being the starting position
        50 + (movement / deltaY) * 100,
        {
            message:
                "Background Y position should be dragged correctly with Scroll Effect set to Fixed ",
        }
    );
});

async function openBgPositionOverlay(editingElement, waitSidebarUpdated) {
    await contains(editingElement).click();
    await waitSidebarUpdated();
    await contains("button[data-action-id='backgroundPositionOverlay']").click();
    await waitFor(".o-overlay-container .o_we_background_dragger", { timeout: 2000 });
}

function patchDragBackground(el, from, to) {
    patchWithCleanup(BackgroundPositionOverlay.prototype, {
        onDragBackgroundMove(ev) {
            // Mock the movementX and movementY readonly property
            super.onDragBackgroundMove({
                preventDefault: () => {},
                movementX: ev.clientX === to.x ? to.x - from.x : 0,
                movementY: ev.clientY === to.y ? to.y - from.y : 0,
            });
        },
    });
    const startDrag = () => contains(el).drag({ position: from });
    const endDrag = async (dragActions) => {
        await dragActions.moveTo(el, { position: to });
        await dragActions.drop();
    };
    return { startDrag, endDrag };
}

async function dragAndDropBgImage() {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <section style="background-image: url('/web/image/123/transparent.png'); width: 500px; height:500px">
            <div class="o_we_shape o_html_builder_Connections_01">
                AAAA
            </div>
        </section>`);
    await openBgPositionOverlay(":iframe section", waitSidebarUpdated);
    const { startDrag, endDrag } = patchDragBackground(
        ".o-overlay-container .o_we_background_dragger",
        { x: 199, y: 199 },
        { x: 200, y: 200 }
    );
    const dragActions = await startDrag();
    await endDrag(dragActions);
}

test("change the main color of a background image of type '/html_editor/shape'", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        `
            <section style="background-image: url('/html_editor/shape/http_routing/404.svg?c2=o-color-2');">
                AAAA
            </section>
        `,
        {
            loadIframeBundles: true,
        }
    );
    await contains(":iframe section").click();
    await waitSidebarUpdated();
    await contains("[data-label='Main Color'] .o_we_color_preview").click();
    await contains(
        ".o-main-components-container .o_colorpicker_section [data-color='o-color-5']"
    ).hover();
    expect(":iframe section").toHaveStyle({
        backgroundImage: `url("${window.location.origin}/html_editor/shape/http_routing/404.svg?c2=o-color-5")`,
    });
    await contains(
        ".o-main-components-container .o_colorpicker_section [data-color='o-color-4']"
    ).hover();
    expect(":iframe section").toHaveStyle({
        backgroundImage: `url("${window.location.origin}/html_editor/shape/http_routing/404.svg?c2=o-color-4")`,
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
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <section style="background-image: url('/web/image/123/transparent.png'); width: 500px; height:500px">
            <div class="o_we_shape o_html_builder_Connections_01">
                AAAA
            </div>
        </section>`);
    await contains(":iframe section").click();
    await waitSidebarUpdated();
    expect(":iframe section").toHaveStyle("backgroundImage");
    await contains("[data-action-id='toggleBgImage']").click();
    await waitSidebarUpdated();
    expect(":iframe section").not.toHaveStyle("backgroundImage", { inline: true });
});

test("changing shape's background color doesn't hide the shape itself", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        `<section style="background-image: url('/html_editor/shape/http_routing/404.svg?c2=o-color-2');">
            AAAA
        </section>`,
        {
            loadIframeBundles: true,
        }
    );
    await contains(":iframe section").click();
    await waitSidebarUpdated();
    await contains("button[data-action-id='toggleBgShape']").click();
    await contains(
        ".o_pager_container .o-hb-bg-shape-btn [data-action-value='html_builder/Connections/01'][data-action-id='setBackgroundShape']"
    ).click();
    const backgroundImageValue = getComputedStyle(queryOne(":iframe .o_we_shape")).backgroundImage;
    expect(backgroundImageValue).toMatch(/Connections\/01/);
    await contains("[data-label='Colors'] button:nth-child(2)").click();
    await contains(".o_colorpicker_section button[data-color='o-color-1']").click();
    expect(":iframe .o_we_shape").toHaveStyle({ backgroundImage: backgroundImageValue });
});

test("remove background image removes color filter", async () => {
    await setupWebsiteBuilderWithSnippet("s_cover");
    await contains(":iframe section").click();
    await contains("[data-action-id='toggleBgImage']").click();
    expect(":iframe section .o_we_bg_filter").not.toHaveCount();
});

test("change background size", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <section class="o_bg_img_opt_repeat" style="background-image: url('/web/image/123/transparent.png'); width: 500px; height:500px; background-size: 100px;">
        </section>`);

    const section = await waitFor(":iframe section");
    await contains(section).click();

    await waitSidebarUpdated();

    const widthInput = await waitFor(
        '[data-action-id="setBackgroundSize"][data-action-param="width"] > input'
    );
    const heightInput = await waitFor(
        '[data-action-id="setBackgroundSize"][data-action-param="height"] > input'
    );

    expect(heightInput).toHaveValue("");

    await contains(heightInput).edit("0");
    expect(heightInput).toHaveValue("1", { message: "minimum value is 1" });
    expect(section).toHaveStyle("background-size: 100px 1px");

    await contains(heightInput).edit("");
    expect(heightInput).toHaveValue("");
    expect(section).toHaveStyle("background-size: 100px");

    await contains(widthInput).edit("");
    expect(widthInput).toHaveValue("");
    expect(heightInput).toHaveValue("", { message: "height input should stay empty" });
    expect(section).toHaveStyle("background-size: auto");

    await contains(widthInput).edit("0");
    expect(widthInput).toHaveValue("1", { message: "minimum value is 1" });
    expect(section).toHaveStyle("background-size: 1px");
});

test("background shape detection is compatible with previous ones (web_editor)", async () => {
    await setupWebsiteBuilder(`
        <section data-oe-shape-data='{"shape":"web_editor/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            AAAA
        </section>`);
    await contains(":iframe section").click();
    expect("div[data-label='Shape'] button:first-of-type").toHaveText("Connections 01");
    await contains("div[data-label='Shape'] button:first-of-type").click();
    expect("button.active[data-action-id='setBackgroundShape']").toHaveAttribute(
        "data-action-value",
        "html_builder/Connections/01"
    );
});

test("can customize background shape groups", async () => {
    class CustomBackgroundShapeGroupsPlugin extends Plugin {
        static id = "customBackgroundShapeGroups";
        resources = {
            background_shape_groups_providers: (shapeGroups) => {
                const connections = shapeGroups.basic.subgroups.connections.shapes;
                const customShapes = {
                    "html_builder/Connections/01": {
                        ...connections["html_builder/Connections/01"],
                        selectLabel: "Custom 01",
                    },
                    "html_builder/Connections/02": {
                        ...connections["html_builder/Connections/02"],
                        selectLabel: "Custom 02",
                    },
                };
                const extraShapes = {
                    "html_builder/Connections/03": {
                        ...connections["html_builder/Connections/03"],
                        selectLabel: "Extra 03",
                    },
                };
                delete connections["html_builder/Connections/01"];
                delete connections["html_builder/Connections/02"];
                return {
                    basic: {
                        subgroups: {
                            custom: {
                                label: "Custom",
                                shapes: customShapes,
                            },
                        },
                    },
                    extra: {
                        label: "Extra",
                        subgroups: {
                            extra: {
                                label: "Extra",
                                shapes: extraShapes,
                            },
                        },
                    },
                };
            },
        };
    }
    addPlugin(CustomBackgroundShapeGroupsPlugin);

    await setupWebsiteBuilder(`<section>AAAA</section>`);
    await contains(":iframe section").click();
    await contains("button[data-action-id='toggleBgShape']").click();
    expect(".o_pager_container").toHaveText(/Custom/);
    expect("button.o-hb-select-pager-tab[data-group-id='extra']").toHaveCount(1);
    expect("[data-action-value='html_builder/Connections/01']").toHaveCount(1);
    expect("[data-action-value='html_builder/Connections/02']").toHaveCount(1);
    await contains("[data-action-value='html_builder/Connections/01']").click();
    expect(":iframe section").toHaveAttribute(
        "data-oe-shape-data",
        '{"shape":"html_builder/Connections/01","flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'
    );
    expect("div[data-label='Shape'] button:not([data-action-id])").toHaveText("Custom 01");
});
