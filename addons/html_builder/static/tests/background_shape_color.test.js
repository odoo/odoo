import {
    addBuilderOption,
    confirmAddSnippet,
    getSnippetStructure,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BackgroundOption } from "@html_builder/plugins/background_option/background_option";
import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const RGB_RED = "rgb(255, 0, 0)";
const RGB_BLUE = "rgb(0, 0, 255)";
const RGB_GREEN = "rgb(0, 255, 0)";
const HEX_BLUE = "#0000ff";
const HEX_GREEN = "#00ff00";
const HEX_O_CC_4 = "#383e45";
const HEX_O_CC_5 = "#f0f0f0";

function getShapeTestCSS() {
    return `
        /* CSS Variables for theme colors */
        :root {
            --o-color-1: #3aadaa;
            --o-color-2: #7c6576;
            --o-color-3: #dd7777;
            --o-color-4: ${HEX_O_CC_4};
            --o-color-5: ${HEX_O_CC_5};

            --o-cc1-bg: #3aadaa;
            --o-cc2-bg: #7c6576;
            --o-cc3-bg: #dd7777;
            --o-cc4-bg: ${HEX_O_CC_4};
            --o-cc5-bg: ${HEX_O_CC_5};
        }

        .o_cc4 {
            background-color: var(--o-cc4-bg);
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
            background-position: center bottom;
        }

        /* Non-connection shapes used in tests */
        .o_we_shape.o_html_builder_Blobs_02 {
            background-image: url("/html_editor/shape/html_builder/Blobs/02.svg?c1=%23383e45");
            background-position: center bottom;
        }
    `;
}

async function clickOnSnippetAndApplyShape(snippetSelector, waitSidebarUpdated) {
    await contains(`:iframe ${snippetSelector}`).click();
    await contains("[data-label='Shape'] button").click();
    await waitSidebarUpdated();
    await contains(
        "button[data-action-id='setBackgroundShape'][data-action-value='html_builder/Connections/01']"
    ).click();
    await waitSidebarUpdated();
}

function getNoBgShapeSection1(bgColor) {
    return `
        <section id="section1" style="background-color: ${bgColor};" data-snippet="s_snippet">
            Section 1
        </section>
    `;
}
function getNoBgShapeSection2(bgColor) {
    return `
        <section id="section2" style="background-color: ${bgColor};" data-snippet="s_snippet">
            Section 2
        </section>
    `;
}
async function updateBgColor(selector, bgColor, waitSidebarUpdated) {
    await contains(selector).click();
    await contains(".o_we_color_preview").click();
    await contains(`[data-color='${bgColor}']`).click();
    await waitSidebarUpdated();
}

beforeEach(async () => {
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
});

test("Connections shape takes neighbor element's background color", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        ${getNoBgShapeSection1(RGB_RED)}
        ${getNoBgShapeSection2(RGB_BLUE)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await clickOnSnippetAndApplyShape("#section1", waitSidebarUpdated);
    expect(":iframe #section1 .o_we_shape").toHaveCount(1);
    const shapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shapeData.shape).toBe("html_builder/Connections/01");
    expect(shapeData.colors.c5).toBe(HEX_BLUE);
});

test("Flipped Connections shape takes previous element's background color", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        ${getNoBgShapeSection1(RGB_BLUE)}
        <section id="section2" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_O_CC_4}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 2
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await contains(":iframe #section2").click();
    await contains("button[data-action-id='flipShape'][data-action-param='y']").click();
    await waitSidebarUpdated();
    const shapeData = JSON.parse(queryOne(":iframe #section2").dataset.oeShapeData);
    expect(shapeData.colors.c5).toBe(HEX_BLUE);
    expect(shapeData.flip.includes("y")).toBe(true);
});

test("Connections shape uses contrasting color when neighbor has same background", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        ${getNoBgShapeSection1(RGB_RED)}
        ${getNoBgShapeSection2(RGB_RED)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await clickOnSnippetAndApplyShape("#section1", waitSidebarUpdated);
    expect(":iframe #section1 .o_we_shape").toHaveCount(1);
    const shapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shapeData.shape).toBe("html_builder/Connections/01");
    expect(shapeData.colors.c5).toBe(HEX_O_CC_5);
});

test("Non-Connections shapes are not affected by neighbor color changes", async () => {
    const hexYellow = "#ffff00";
    const checkBgShapeSection1 = () => {
        const section1 = queryOne(":iframe #section1");
        const shapeData = JSON.parse(section1.dataset.oeShapeData);
        expect(shapeData.shape).toBe("html_builder/Blobs/02");
        expect(shapeData.colors.c1).toBe(hexYellow);
    };
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Blobs/02","colors":{"c1":"${hexYellow}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Blobs_02"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_BLUE)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    checkBgShapeSection1();
    await updateBgColor(":iframe #section2", "o_cc3", waitSidebarUpdated);
    checkBgShapeSection1();
});

test("Connections shape color updates when neighbor background color changes", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_BLUE}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_BLUE)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await updateBgColor(":iframe #section2", "o_cc5", waitSidebarUpdated);
    const shapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shapeData.shape).toBe("html_builder/Connections/01");
    expect(shapeData.colors.c5).toBe(HEX_O_CC_5);
});

test("User set connections shape color don't update when neighbor background color changes", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_BLUE}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":true}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_GREEN)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await updateBgColor(":iframe #section2", "o_cc5", waitSidebarUpdated);
    const shapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shapeData.colors.c5).toBe(HEX_BLUE);
});

test("Connections shape color updates when snippet is dropped next to it", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_O_CC_4}"},"flip":["y"],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01" style='background-image: url("/html_editor/shape/html_builder/Connections/01.svg?c5=%230000ff")'></div>
            Section 1
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
                        content: `<section class="s_test" data-snippet="s_test" data-name="Test" style ="background-color: ${RGB_BLUE}; height: 19px;">
                <div class="test_a"></div>
                </section>`,
                    }),
                ],
            },
        }
    );
    await contains("#blocks-tab").click();
    const section1 = queryOne(":iframe #section1");
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(section1);
    await drop();
    await confirmAddSnippet();
    await waitSidebarUpdated();
    const updatedShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(updatedShapeData.shape).toBe("html_builder/Connections/01");
    expect(updatedShapeData.colors.c5).toBe(HEX_BLUE);
});

test("Connections shape color updates when adjacent snippet is removed", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_GREEN}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_GREEN)}
        <section id="section3" style="background-color: ${RGB_BLUE}" data-snippet="s_snippet">
            Section 3
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    const initialShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(initialShapeData.shape).toBe("html_builder/Connections/01");
    expect(initialShapeData.colors.c5).toBe(HEX_GREEN);
    await contains(":iframe #section2").click();
    await contains(".oe_snippet_remove").click();
    await waitSidebarUpdated();
    const updatedShapeData = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(updatedShapeData.shape).toBe("html_builder/Connections/01");
    expect(updatedShapeData.colors.c5).toBe(HEX_BLUE);
});

test("Multiple Connections shapes update when middle section color changes", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"#00ff00"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_GREEN)}
        <section id="section3" style="background-color: ${RGB_BLUE}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"#00ff00"},"flip":["y"],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 3
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await updateBgColor(":iframe #section2", "o_cc5", waitSidebarUpdated);
    const updatedShape1Data = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    const updatedShape3Data = JSON.parse(queryOne(":iframe #section3").dataset.oeShapeData);
    expect(updatedShape1Data.shape).toBe("html_builder/Connections/01");
    expect(updatedShape3Data.shape).toBe("html_builder/Connections/01");
    expect(updatedShape1Data.colors.c5).toBe(HEX_O_CC_5);
    expect(updatedShape3Data.colors.c5).toBe(HEX_O_CC_5);
});

test("Connections shapes don't update for old bg shape", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_BLUE}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0"}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_GREEN)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );

    await updateBgColor(":iframe #section2", "o_cc5", waitSidebarUpdated);
    const updatedShape1Data = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(updatedShape1Data.shape).toBe("html_builder/Connections/01");
    expect(updatedShape1Data.colors.c5).toBe(HEX_BLUE);
});

test("Connection shape updates when snippet background color updates", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_O_CC_4}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );
    await updateBgColor(":iframe #section1", "o_cc4", waitSidebarUpdated);
    const shape1Data = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shape1Data.colors.c5).not.toBe(HEX_O_CC_4);
});

test("Connection shape updates to default color when neighbor snippet background color updates to a custom color", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_O_CC_4}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":false}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_GREEN)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );
    await contains(":iframe #section2").click();
    await contains(".o_we_color_preview").click();
    await contains(".o_font_color_selector button:contains(Gradient)").click();
    await contains(".o_gradient_color_button").click();
    await waitSidebarUpdated();
    const shape1Data = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shape1Data.colors).toBe(undefined);
});

test("Connection shape color updates if background shape color and neighbor background color are resynchronized", async () => {
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `
        <section id="section1" style="background-color: ${RGB_RED}" data-snippet="s_snippet"
                 data-oe-shape-data='{"shape":"html_builder/Connections/01","colors":{"c5":"${HEX_O_CC_4}"},"flip":[],"showOnMobile":false,"shapeAnimationSpeed":"0", "selectedColor":true}'>
            <div class="o_we_shape o_html_builder_Connections_01"></div>
            Section 1
        </section>
        ${getNoBgShapeSection2(RGB_GREEN)}
    `,
        {
            styleContent: getShapeTestCSS(),
        }
    );
    await updateBgColor(":iframe #section2", "o_cc4", waitSidebarUpdated);
    await updateBgColor(":iframe #section2", "o_cc5", waitSidebarUpdated);
    const shape1Data = JSON.parse(queryOne(":iframe #section1").dataset.oeShapeData);
    expect(shape1Data.colors.c5).toBe(HEX_O_CC_5);
});
