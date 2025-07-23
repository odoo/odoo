import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryFirst, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { delay } from "@web/core/utils/concurrency";
import { imageShapeDefinitions } from "@html_builder/plugins/image/image_shapes_definition";
import { testImg } from "./image_test_helpers";

defineWebsiteModels();

const testImgWithShapeAndClass = `
<img src='/web/image/website.s_text_image_default_image'
    data-attachment-id="1" data-original-id="1"
    data-original-src="/website/static/src/img/snippets_demo/s_text_image.webp"
    data-mimetype-before-conversion="image/webp"
    data-mimetype="image/webp"
    data-shape="html_builder/geometric/geo_shuriken"
    data-image-shape-class="o_class_one o_class_two"
    data-file-name="s_text_image.webp"
    class="o_class_one o_class_two"
    >
`;
const testImgShapeWithOnlyClass = `
<img src='/web/image/website.s_text_image_default_image'
    class="o_class_one o_class_two"
    >
`;
const testImgShapeWithOnlyShape = `
<img src='/web/image/website.s_text_image_default_image'
    data-shape="html_builder/geometric/geo_shuriken"
    >
`;
test("Applying shape with imageShapeClass should not generate an SVG and clear border radius", async () => {
    // Update geo_shuriken to apply shape through imageShapeClass
    imageShapeDefinitions.basic.subgroups.geometrics.shapes[
        "html_builder/geometric/geo_shuriken"
    ].imageShapeClass = "o_class_one o_class_two";
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await contains(
        "[data-container-title='Image'] [data-label='Round Corners'] [data-action-id='styleAction'] input"
    ).edit("10");

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    const img = queryFirst(":iframe .test-options-target img");
    expect(":iframe .test-options-target img").toHaveAttribute("data-attachment-id", "1");
    expect(":iframe .test-options-target img").toHaveAttribute("data-original-id", "1");
    expect(":iframe .test-options-target img").toHaveAttribute("data-mimetype", "image/webp");
    expect(img.src.startsWith("data:image/webp;base64,")).toBe(true);
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
        "s_text_image.webp"
    );
    expect(":iframe .test-options-target img").toHaveAttribute("data-shape-colors", ";;;;");
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-image-shape-class",
        "o_class_one o_class_two"
    );
    expect(":iframe .test-options-target img").not.toHaveAttribute(
        "style",
        "--box-border-bottom-left-radius: 10px; --box-border-bottom-right-radius: 10px; --box-border-top-right-radius: 10px; --box-border-top-left-radius: 10px;"
    );
    expect(":iframe .test-options-target img").toHaveClass(["o_class_one", "o_class_two"]);
    // ensure the image shape class is applied
    await animationFrame();
    await animationFrame();
    expect("[data-container-title='Image'] [data-label='Round Corners']").toHaveCount(0);
    delete imageShapeDefinitions.basic.subgroups.geometrics.shapes[
        "html_builder/geometric/geo_shuriken"
    ].imageShapeClass;
});
test("Should remove shape classes when clearing a imageShapeClass-applied shape", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImgWithShapeAndClass}
        </div>
    `);
    expect(":iframe .test-options-target img").toHaveClass("o_class_one o_class_two");
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();
    await waitFor("[data-label='Shape'] .dropdown:contains(Shuriken)");
    await contains("[data-action-id='setImageShape']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    expect(":iframe .test-options-target img").not.toHaveAttribute("data-image-shape-class");
    expect(":iframe .test-options-target img").not.toHaveClass("o_class_one o_class_two");
});
test("Selects shape option when image classes match a shape definition", async () => {
    // Update geo_shuriken to select shape through imageShapeClass
    imageShapeDefinitions.basic.subgroups.geometrics.shapes[
        "html_builder/geometric/geo_shuriken"
    ].imageShapeClass = "o_class_one o_class_two";
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImgShapeWithOnlyClass}
        </div>
    `);
    expect(":iframe .test-options-target img").toHaveClass("o_class_one o_class_two");

    await contains(":iframe .test-options-target img").click();
    await waitFor("[data-label='Shape'] .dropdown:contains(Shuriken)");
    delete imageShapeDefinitions.basic.subgroups.geometrics.shapes[
        "html_builder/geometric/geo_shuriken"
    ].imageShapeClass;
});
test("Should set dataset shape and apply classes when image matches imageShapeClass", async () => {
    // Update geo_shuriken to apply class through shape key
    imageShapeDefinitions.basic.subgroups.geometrics.shapes[
        "html_builder/geometric/geo_shuriken"
    ].imageShapeClass = "o_class_one o_class_two";
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImgShapeWithOnlyShape}
        </div>
    `);
    expect(":iframe .test-options-target img").toHaveAttribute(
        "data-shape",
        "html_builder/geometric/geo_shuriken"
    );

    await contains(":iframe .test-options-target img").click();
    await waitFor("[data-label='Shape'] .dropdown:contains(Shuriken)");
    expect(":iframe .test-options-target img").toHaveClass("o_class_one o_class_two");
    delete imageShapeDefinitions.basic.subgroups.geometrics.shapes[
        "html_builder/geometric/geo_shuriken"
    ].imageShapeClass;
});
test("Should set a shape on an image", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

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
test("Should change the shape color of an image", async () => {
    const { getEditor, waitDomUpdated } = await setupWebsiteBuilder(
        `<div class="test-options-target">
            ${testImg}
        </div>`,
        {
            loadIframeBundles: true,
        }
    );
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});
    await waitDomUpdated();

    await waitFor(`[data-label="Colors"] .o_we_color_preview`);

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

    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});
    await waitDomUpdated();

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
    const { getEditor, waitDomUpdated } = await setupWebsiteBuilder(
        `<div class="test-options-target">
            ${testImg}
        </div>`,
        {
            loadIframeBundles: true,
        }
    );
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    await waitFor(`[data-label="Colors"] .o_we_color_preview`);

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

    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});
    // wait for owl to update the dom
    await waitDomUpdated();

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
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});
    await animationFrame();

    expect(`[data-action-id="flipImageShape"]`).not.toHaveCount();
    expect(`[data-action-id="rotateImageShape"]`).not.toHaveCount();
});
describe("flip shape axis", () => {
    test("Should flip the shape X axis", async () => {
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        await waitFor(`[data-action-id="flipImageShape"]`);

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
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        await waitFor(`[data-action-id="flipImageShape"]`);

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
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        await waitFor(`[data-action-id="flipImageShape"]`);

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
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        await waitFor(`[data-action-id="flipImageShape"]`);

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
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        await waitFor(`[data-action-id="rotateImageShape"]`);

        expect(`:iframe .test-options-target img`).toHaveAttribute(
            "data-shape",
            "html_builder/geometric/geo_tetris"
        );

        await contains(`[data-action-id="rotateImageShape"]:has(.fa-rotate-left)`).click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-rotate", "270");
    });
    test("Should remove rotate data when there is no rotation", async () => {
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        await waitFor(`[data-action-id="rotateImageShape"]`);

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
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});

        await waitFor(`[data-action-id="rotateImageShape"]`);

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
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/geometric/geo_tetris']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});
    await animationFrame();

    expect(`[data-action-id="setImageShapeSpeed"]`).not.toHaveCount();
});
test("Should change the speed of an animated shape", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();

    await contains("[data-label='Shape'] .dropdown").click();
    await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    const originalSrc = queryFirst(":iframe .test-options-target img").src;

    await waitFor(`[data-action-id="setImageShapeSpeed"]`);
    const rangeInput = queryFirst(`[data-action-id="setImageShapeSpeed"] input`);
    rangeInput.value = 2;
    rangeInput.dispatchEvent(new Event("input"));
    await delay();
    rangeInput.dispatchEvent(new Event("change"));
    await delay();

    // ensure the shape action has been applied
    await editor.shared.operation.next(() => {});

    expect(`:iframe .test-options-target img`).toHaveAttribute("data-shape-animation-speed", "2");
    expect(`:iframe .test-options-target img`).not.toHaveAttribute("src", originalSrc);
});
describe("toggle ratio", () => {
    test("Should not be able to toggle the ratio of a pattern_wave_4", async () => {
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/pattern/pattern_wave_4']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});
        await animationFrame();

        expect(`[data-action-id="toggleImageShapeRatio"]`).not.toHaveCount();
    });
    test("A shape with togglable ratio should be added cropped and crop when clicked", async () => {
        const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
        const editor = getEditor();
        await contains(":iframe .test-options-target img").click();

        await contains("[data-label='Shape'] .dropdown").click();
        await contains("[data-action-value='html_builder/geometric/geo_shuriken']").click();
        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});
        await animationFrame();
        await new Promise((resolve) => setTimeout(resolve, 1000));

        const croppedSrc = queryFirst(":iframe .test-options-target img").src;

        await contains(`[data-action-id="toggleImageShapeRatio"] input`).click();

        // ensure the shape action has been applied
        await editor.shared.operation.next(() => {});
        await animationFrame();

        expect(`:iframe .test-options-target img`).not.toHaveAttribute("src", croppedSrc);
    });
});
