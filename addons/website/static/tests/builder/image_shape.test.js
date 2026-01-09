import { describe, expect, test } from "@odoo/hoot";
import { queryFirst, setInputRange } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { Plugin } from "@html_editor/plugin";
import { addPlugin, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { testImg } from "./image_test_helpers";

defineWebsiteModels();

test("Should set a shape on an image", async () => {
    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    const img = queryFirst(":iframe .test-options-target img");
    expect(":iframe .test-options-target img").toHaveAttribute("data-attachment-id", "1");
    expect(":iframe .test-options-target img").toHaveAttribute("data-original-id", "1");
    expect(":iframe .test-options-target img").toHaveAttribute("data-mimetype", "image/svg+xml");
    expect(img.src.startsWith("data:image/svg+xml;base64,")).toBe(true);
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-original-src",
        "/website/static/src/img/snippets_demo/s_text_image.webp"
    );
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-mimetype-before-conversion",
        "image/webp"
    );
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-shape",
        "html_builder/geometric/geo_shuriken"
    );
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-file-name",
        "s_text_image.svg"
    );
    expect(":iframe .test-options-target img").toHaveAttribute("data-shape-colors", ";;;;");
});

test("Should set a shape on a GIF", async () => {
    // Define the img tag using the specified GIF path.
    const testGif = `<img
        src="/web/image/456-test/test.gif"
        class="img-fluid o_we_custom_image"
    >`;

    // Set up the website builder with the test GIF.
    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testGif}
        </div>
        `);
    const editor = getEditor();

    // Click the GIF to activate the image options in the sidebar.
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    // Select and apply a shape.
    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    // Wait for the editor to process the change.
    await editor.shared.operation.next(() => {});

    const gif = queryFirst(":iframe .test-options-target img");

    // ## Assertions: Verify the shape was applied correctly.

    // 1. The image source should now be an SVG mask, not the original GIF path.
    expect(gif.src.startsWith("data:image/svg+xml;base64,")).toBe(true);

    // 2. The new MIME type for the element is 'image/svg+xml'.
    expect(":iframe .test-options-target img").toHaveAttribute("data-mimetype", "image/svg+xml");

    // 3. The system correctly remembers the original source was a GIF.
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-mimetype-before-conversion",
        "image/gif"
    );

    // 4. The original source path is preserved in 'data-original-src'.
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-original-src",
        "/website/static/src/img/snippets_options/header_effect_fade_out.gif"
    );

    // 5. The shape data attribute is correctly set.
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-shape",
        "html_builder/geometric/geo_shuriken"
    );
});

test("Should change the shape color of an image", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        `<div class="test-options-target">
            ${testImg}
        </div>`,
        {
            loadIframeBundles: true,
        }
    );
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
    await waitSidebarUpdated();

    expect(`[data-label="Colors"] .o_we_color_preview`).toHaveCount(4);

    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).toHaveAttribute(
        "style",
        `background-color: #714B67`
    );
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(2)`).toHaveAttribute(
        "style",
        `background-color: #F0CDA8`
    );
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(3)`).toHaveAttribute(
        "style",
        `background-color: #F6F5F4`
    );
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(4)`).toHaveAttribute(
        "style",
        `background-color: #1B1319`
    );

    expect(`:iframe .test-options-target img`).toHaveAttribute(
        "data-shape",
        "html_builder/pattern/pattern_wave_4"
    );
    expect(`:iframe .test-options-target img`).toHaveAttribute(
        "data-shape-colors",
        "#714B67;#F0CDA8;#F6F5F4;;#1B1319"
    );

    await contains(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).click();
    await contains(`.o_font_color_selector [data-color="#FF0000"]`).click();

    await waitSidebarUpdated();

    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).toHaveAttribute(
        "style",
        `background-color: #FF0000`
    );
    expect(`:iframe .test-options-target img`).toHaveAttribute(
        "data-shape-colors",
        "#FF0000;#F0CDA8;#F6F5F4;;#1B1319"
    );
});
test("Should change the shape color of an image with a class color", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        `<div class="test-options-target">
            ${testImg}
        </div>`,
        {
            loadIframeBundles: true,
        }
    );
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
    await waitSidebarUpdated();

    expect(`[data-label="Colors"] .o_we_color_preview`).toHaveCount(4);

    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).toHaveAttribute(
        "style",
        `background-color: #714B67`
    );
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(2)`).toHaveAttribute(
        "style",
        `background-color: #F0CDA8`
    );
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(3)`).toHaveAttribute(
        "style",
        `background-color: #F6F5F4`
    );
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(4)`).toHaveAttribute(
        "style",
        `background-color: #1B1319`
    );

    expect(`:iframe .test-options-target img`).toHaveAttribute(
        "data-shape",
        "html_builder/pattern/pattern_wave_4"
    );
    expect(`:iframe .test-options-target img`).toHaveAttribute(
        "data-shape-colors",
        "#714B67;#F0CDA8;#F6F5F4;;#1B1319"
    );

    await contains(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).click();
    await contains(`.o_font_color_selector [data-color="o-color-2"]`).click();

    await waitSidebarUpdated();

    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).toHaveAttribute(
        "style",
        `background-color: #F0CDA8`
    );
    expect(`:iframe .test-options-target img`).toHaveAttribute(
        "data-shape-colors",
        "#F0CDA8;#F0CDA8;#F6F5F4;;#1B1319"
    );
});
test("Should not show transform action on shape that cannot bet transformed", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    await waitSidebarUpdated();
    expect(`[data-action-id="flipImageShape"]`).not.toHaveCount();
    expect(`[data-action-id="rotateImageShape"]`).not.toHaveCount();
});
describe("flip shape axis", () => {
    test("Should flip the shape X axis", async () => {
        const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        await waitSidebarUpdated();

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="flipImageShape"]:has(.oi-arrows-h)`).click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-flip", "x");
    });
    test("Should unflip the shape X axis", async () => {
        const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        await waitSidebarUpdated();

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="flipImageShape"]:has(.oi-arrows-h)`).click();
        await contains(`[data-action-id="flipImageShape"]:has(.oi-arrows-h)`).click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(`:iframe .test-options-target img`).not.toHaveAttribute("data-shape-flip");
    });
    test("Should flip the shape Y axis", async () => {
        const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        await waitSidebarUpdated();

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="flipImageShape"]:has(.oi-arrows-v)`).click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-flip", "y");
    });
    test("Should flip the shape XY axis", async () => {
        const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        await waitSidebarUpdated();

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="flipImageShape"]:has(.oi-arrows-h)`).click();
        await contains(`[data-action-id="flipImageShape"]:has(.oi-arrows-v)`).click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-flip", "xy");
    });
});
describe("rotate shape", () => {
    test("Should rotate the shape to the left", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await waitSidebarUpdated();

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="rotateImageShape"]:has(.fa-rotate-left)`).click();
        // ensure the shape action has been applied
        await waitSidebarUpdated();
        expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-rotate", "270");
    });
    test("Should remove rotate data when there is no rotation", async () => {
        const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        await waitSidebarUpdated();

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="rotateImageShape"]:has(.fa-rotate-left)`).click();
        await contains(`[data-action-id="rotateImageShape"]:has(.fa-rotate-right)`).click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(`:iframe .test-options-target img`).not.toHaveAttribute("data-shape-rotate");
    });
    test("Should rotate the shape to the right", async () => {
        const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await waitSidebarUpdated();

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="rotateImageShape"]:has(.fa-rotate-right)`).click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-rotate", "90");
    });
});
test("Should not show animate speed if the shape is not animated", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
    await waitSidebarUpdated();
    expect(`[data-action-id="setImageShapeSpeed"]`).not.toHaveCount();
});
test("Should change the speed of an animated shape", async () => {
    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
    // ensure the shape action has been applied
    await waitSidebarUpdated();

    const originalSrc = queryFirst(":iframe .test-options-target img").src;

    await setInputRange(`[data-action-id="setImageShapeSpeed"] input`, 2);
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-animation-speed", "2");
    expect(`:iframe .test-options-target img`).not.toHaveAttribute("src", originalSrc);
});
describe("toggle ratio", () => {
    test("Should not be able to toggle the ratio of a pattern_wave_4", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
        await waitSidebarUpdated();

        expect(`[data-action-id="toggleImageShapeRatio"]`).not.toHaveCount();
    });
    test("A shape with togglable ratio should be added cropped and crop when clicked", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
        // ensure the shape action has been applied
        await waitSidebarUpdated();
        const croppedSrc = queryFirst(":iframe .test-options-target img").src;

        await contains(`[data-action-id="toggleImageShapeRatio"] input`).click();
        await waitSidebarUpdated();
        expect(`:iframe .test-options-target img`).not.toHaveAttribute("src", croppedSrc);
    });
});

test("Should reset crop when removing shape with ratio", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    await waitSidebarUpdated();
    expect(`:iframe .test-options-target img`).toHaveAttribute("data-aspect-ratio");
    // Remove the shape.
    await contains("[data-action-id='setImageShape']").click();
    await waitSidebarUpdated();
    expect(`:iframe .test-options-target img`).not.toHaveAttribute("data-aspect-ratio");
});

test("Should have the correct active shape in the image shape selector", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);

    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
    await waitSidebarUpdated();
    await contains("[data-label='Shape'] .dropdown").click();
    expect("[data-action-value='html_builder/geometric/geo_tetris']").toHaveClass("active");
});

test("Should keep colors when changing speed and vice versa", async () => {
    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(
        `<div class="test-options-target">
            ${testImg}
        </div>`,
        {
            loadIframeBundles: true,
        }
    );
    const editor = getEditor();

    // Select image and apply shape
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
    await waitSidebarUpdated();

    const imgSelector = ":iframe .test-options-target img";
    const initialColors = [
        queryFirst(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).style.backgroundColor,
        queryFirst(`[data-label="Colors"] .o_we_color_preview:nth-child(2)`).style.backgroundColor,
        queryFirst(`[data-label="Colors"] .o_we_color_preview:nth-child(3)`).style.backgroundColor,
        queryFirst(`[data-label="Colors"] .o_we_color_preview:nth-child(4)`).style.backgroundColor,
    ];

    // Change speed
    await setInputRange(`[data-action-id="setImageShapeSpeed"] input`, -1);
    await editor.shared.operation.next(() => {});

    // Change first color and verify speed unchanged
    await contains(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).click();
    await contains(`.o_font_color_selector [data-color="#FF0000"]`).click();
    await waitSidebarUpdated();

    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).toHaveStyle({
        backgroundColor: "rgb(255, 0, 0)",
    });
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(2)`).toHaveStyle({
        backgroundColor: initialColors[1],
    });
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(3)`).toHaveStyle({
        backgroundColor: initialColors[2],
    });
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(4)`).toHaveStyle({
        backgroundColor: initialColors[3],
    });

    expect(imgSelector).toHaveAttribute("data-shape-animation-speed", "-1");

    // Change speed and verify colors unchanged
    await setInputRange(`[data-action-id="setImageShapeSpeed"] input`, 2);
    await editor.shared.operation.next(() => {});

    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(1)`).toHaveStyle({
        backgroundColor: "rgb(255, 0, 0)",
    });
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(2)`).toHaveStyle({
        backgroundColor: initialColors[1],
    });
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(3)`).toHaveStyle({
        backgroundColor: initialColors[2],
    });
    expect(`[data-label="Colors"] .o_we_color_preview:nth-child(4)`).toHaveStyle({
        backgroundColor: initialColors[3],
    });

    expect(imgSelector).toHaveAttribute("data-shape-animation-speed", "2");
});

test("Be able to add and remove shape from custom groups", async () => {
    class CustomImageShapeGroupsPlugin extends Plugin {
        static id = "customImageShapeGroups";
        resources = {
            image_shape_groups_providers: (shapeGroups) => {
                const geometrics = shapeGroups.basic.subgroups.geometrics.shapes;
                const customShapes = {
                    "html_builder/geometric/geo_shuriken": {
                        ...geometrics["html_builder/geometric/geo_shuriken"],
                        selectLabel: "Custom Shuriken",
                    },
                    "html_builder/geometric/geo_diamond": {
                        ...geometrics["html_builder/geometric/geo_diamond"],
                        selectLabel: "Custom Diamond",
                    },
                };
                const extraShapes = {
                    "html_builder/geometric/geo_triangle": {
                        ...geometrics["html_builder/geometric/geo_triangle"],
                        selectLabel: "Extra Triangle",
                    },
                };
                delete geometrics["html_builder/geometric/geo_shuriken"];
                delete geometrics["html_builder/geometric/geo_diamond"];
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
    addPlugin(CustomImageShapeGroupsPlugin);

    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains("[data-label='Shape'] .dropdown").click();
    expect(".o_pager_container").toHaveText(/Custom/);
    expect("button.o-hb-select-pager-tab[data-group-id='extra']").toHaveCount(1);
    expect("[data-action-value='html_builder/geometric/geo_shuriken']").toHaveCount(1);
    expect("[data-action-value='html_builder/geometric/geo_diamond']").toHaveCount(1);
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    await waitSidebarUpdated();
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-shape",
        "html_builder/geometric/geo_shuriken"
    );
    expect("div[data-label='Shape'] .dropdown").toHaveText("Custom Shuriken");
});
