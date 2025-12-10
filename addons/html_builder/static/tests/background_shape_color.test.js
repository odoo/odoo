import {
    addBuilderOption,
    setupHTMLBuilder,
    waitForEndOfOperation,
    confirmAddSnippet,
    getSnippetStructure,
} from "@html_builder/../tests/helpers";
import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

function getShapeTestCSS() {
    return `
        /* CSS Variables for theme colors */
        :root {
            --o-color-1: #3aadaa;
            --o-color-2: #7c6576;
            --o-color-3: #dd7777;
            --o-color-4: #383e45;
            --o-color-5: #f0f0f0;

            --o-cc1-bg: #3aadaa;
            --o-cc2-bg: #7c6576;
            --o-cc3-bg: #dd7777;
            --o-cc4-bg: #383e45;
            --o-cc5-bg: #f0f0f0;
        }

        .o_cc5 {
            background-color: var(--o-cc5-bg);
        }

        /* Base shape styles - required for positioning and layout */
        .o_we_shape {
            position: absolute !important;
            top: 0;
            right: 0;
            bottom: 0;
            left: 0;
            display: block;
            overflow: hidden;
            pointer-events: none;
        }

        /* Connections shapes */
        .o_we_shape.o_html_builder_Connections_01 {
            background-image: url("/html_editor/shape/html_builder/Connections/01.svg?c5=%23383e45");
            background-position: 50% 100%;
            background-size: 100% auto;
            background-repeat: no-repeat;
        }

        .o_we_shape.o_html_builder_Connections_02 {
            background-image: url("/html_editor/shape/html_builder/Connections/02.svg?c5=%23383e45");
            background-position: 50% 100%;
            background-size: 100% auto;
            background-repeat: no-repeat;
        }

        /* Non-connection shapes used in tests */
        .o_we_shape.o_html_builder_Blobs_02 {
            background-image: url("/html_editor/shape/html_builder/Blobs/02.svg?c1=%23383e45");
            background-position: 50% 50%;
            background-size: 100% 100%;
            background-repeat: no-repeat;
        }

        .o_we_shape.o_html_builder_Containers_01 {
            background-image: url("/html_editor/shape/html_builder/Containers/01.svg?c5=%23383e45");
            background-position: 50% 100%;
            background-size: 100% auto;
            background-repeat: no-repeat;
        }

        .o_we_shape.o_html_builder_Bold_16 {
            background-image: url("/html_editor/shape/html_builder/Bold/16.svg?c5=%23383e45");
            background-position: 50% 100%;
            background-size: 100% auto;
            background-repeat: no-repeat;
        }
    `;
}

test("Connections shape takes neighbor element's background color", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet">
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(0, 0, 255);" data-snippet="s_snippet">
            Section 2
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await contains(":iframe #section1").click();
    await contains("[data-label='Shape'] button").click();
    await animationFrame();
    await contains(
        "button[data-action-id='setBackgroundShape'][data-action-value='html_builder/Connections/01']"
    ).click();
    await animationFrame();
    expect(":iframe #section1 .o_we_shape").toHaveCount(1);
    const shapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shapeData.shape).toBe("html_builder/Connections/01");
    expect(shapeData.colors.c5).toBe("#0000ff");
});

test("Flipped Connections shape takes previous element's background color", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet">
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(0, 0, 255);" data-snippet="s_snippet">
            Section 2
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await contains(":iframe #section2").click();
    await contains("[data-label='Shape'] button").click();
    await animationFrame();
    await contains(
        "button[data-action-id='setBackgroundShape'][data-action-value='html_builder/Connections/01']"
    ).click();
    await animationFrame();
    await contains("button[data-action-id='flipShape'][data-action-param='y']").click();
    expect(":iframe #section2 .o_we_shape").toHaveCount(1);
    const shapeData = JSON.parse(queryOne(":iframe #section2").dataset.oeShapeData);
    expect(shapeData.shape).toBe("html_builder/Connections/01");
    expect(shapeData.colors.c5).toBe("#ff0000");
    expect(shapeData.flip.includes("y")).toBe(true);
});

test("Connections shape uses contrasting color when neighbor has same background", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet">
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet">
            Section 2
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await contains(":iframe #section1").click();
    await contains("[data-label='Shape'] button").click();
    await animationFrame();
    await contains(
        "button[data-action-id='setBackgroundShape'][data-action-value='html_builder/Connections/01']"
    ).click();
    await animationFrame();
    expect(":iframe #section1 .o_we_shape").toHaveCount(1);
    const shapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shapeData.shape).toBe("html_builder/Connections/01");
    expect(shapeData.colors.c5).toBe("#f0f0f0");
});

test("Non-Connections shapes are not affected by neighbor color changes", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Blobs/02","colors":{"c1":"#ffff00"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Blobs_02"></div>
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(0, 0, 255);" data-snippet="s_snippet">
            Section 2
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    const section1 = queryOne(":iframe #section1");
    const initialShapeData = JSON.parse(section1.dataset.oeShapeData);
    expect(initialShapeData.shape).toBe("html_builder/Blobs/02");
    expect(initialShapeData.colors.c1).toBe("#ffff00");
    await contains(":iframe #section2").click();
    await contains(".o_we_color_preview").click();
    await contains("[data-color='o_cc3']").click();
    await animationFrame();
    const updatedShapeData = JSON.parse(section1.dataset.oeShapeData);
    expect(updatedShapeData.shape).toBe("html_builder/Blobs/02");
    expect(updatedShapeData.colors.c1).toBe("#ffff00");
});

test("Connections shape color updates when neighbor background color changes", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"#0000ff"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(0, 0, 255);" data-snippet="s_snippet">
            Section 2
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await contains(":iframe #section2").click();
    await contains(".o_we_color_preview").click();
    await contains("[data-color='o_cc5']").click();
    await animationFrame();
    const shapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shapeData.shape).toBe("html_builder/Connections/01");
    expect(shapeData.colors.c5).toBe("#f0f0f0");
});

test("Connections shape color updates when snippet is dropped next to it", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"#0000ff"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Connections_01" style='background-image: url("/html_editor/shape/html_builder/Connections/01.svg?c5=%230000ff")'></div>
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(0, 0, 255);" data-snippet="s_snippet">
            Section 2
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
            snippets: {
                snippet_groups: [
                    '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                ],
                snippet_structure: [
                    getSnippetStructure({
                        name: "Test",
                        groupName: "a",
                        content: `<section class="s_test" data-snippet="s_test" data-name="Test" style ="background-color: rgb(0,255,0); height: 19px;">
                <div class="test_a"></div>
                </section>`,
                    }),
                ],
            },
        }
    );

    const initialShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(initialShapeData.shape).toBe("html_builder/Connections/01");
    expect(initialShapeData.colors.c5).toBe("#0000ff");
    await contains(":iframe #section1").click();
    await contains("[data-action-param='y']").click();
    await contains("#blocks-tab").click();
    const section1 = queryOne(":iframe #section1");
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(section1);
    await drop();
    await confirmAddSnippet();
    await waitForEndOfOperation();
    const updatedShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(updatedShapeData.shape).toBe("html_builder/Connections/01");
    expect(updatedShapeData.colors.c5).toBe("#00ff00");
});

test("Connections shape color updates when adjacent snippet is removed", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"#00ff00"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(0, 255, 0);" data-snippet="s_snippet">
            Section 2
        </section>
        <section id="section3" style="background-color: rgb(0, 0, 255);" data-snippet="s_snippet">
            Section 3
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    const initialShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(initialShapeData.shape).toBe("html_builder/Connections/01");
    expect(initialShapeData.colors.c5).toBe("#00ff00");
    await contains(":iframe #section2").click();
    await contains(".oe_snippet_remove").click();
    await animationFrame();
    const updatedShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(updatedShapeData.shape).toBe("html_builder/Connections/01");
    expect(updatedShapeData.colors.c5).toBe("#0000ff");
});

test("Multiple Connections shapes update when middle section color changes", async () => {
    addBuilderOption(
        class TestBackgroundOption extends BackgroundOption {
            static selector = "section";
            static props = {
                ...BackgroundOption.props,
                withColors: { type: Boolean, optional: true },
                withImages: { type: Boolean, optional: true },
                withColorCombinations: { type: Boolean, optional: true },
            };
            static defaultProps = {
                withColors: true,
                withImages: true,
                withShapes: true,
                withColorCombinations: false,
            };
        }
    );

    await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: rgb(255, 0, 0);" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"#00ff00"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        <section id="section2" style="background-color: rgb(0, 255, 0);" data-snippet="s_snippet">
            Section 2
        </section>
        <section id="section3" style="background-color: rgb(0, 0, 255);" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"#00ff00"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 3
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await contains(":iframe #section3").click();
    await contains("[data-action-param='y']").click();
    await contains(":iframe #section2").click();
    await contains(".o_we_color_preview").click();
    await contains("[data-color='o_cc5']").click();
    await animationFrame();
    const updatedShape1Data = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    const updatedShape3Data = JSON.parse(queryOne(":iframe #section3").dataset.oeShapeData);
    expect(updatedShape1Data.shape).toBe("html_builder/Connections/01");
    expect(updatedShape3Data.shape).toBe("html_builder/Connections/01");
    expect(updatedShape1Data.colors.c5).toBe("#f0f0f0");
    expect(updatedShape3Data.colors.c5).toBe("#f0f0f0");
});
