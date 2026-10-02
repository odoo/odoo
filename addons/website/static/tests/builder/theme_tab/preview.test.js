import { expect, queryFirst, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const USER_VALUES = "/website/static/src/scss/options/user_values.scss";

function mockThemeRpcs() {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step(`${location} ${JSON.stringify(changes)}`);
        }
    }
    defineModels([WebsiteAssets]);
    onRpc("/website/theme_customize_bundle_reload", () => {
        expect.step("asset reload");
        return "";
    });
}

// The number box of a slider.
function numberInput(variable) {
    return `[data-action-param='${variable}'] input.o-hb-input-number`;
}

function websiteRootStyle() {
    return queryFirst(":iframe html").style;
}

async function save() {
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
}

test("theme tab: a value is previewed, undone, redone and written on save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains(numberInput("paragraph-margin-top")).edit("8");
    expect(websiteRootStyle().getPropertyValue("--paragraph-margin-top")).toBe("8px");

    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(websiteRootStyle().getPropertyValue("--paragraph-margin-top")).toBe("");

    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    expect(websiteRootStyle().getPropertyValue("--paragraph-margin-top")).toBe("8px");
    expect.verifySteps([]);

    await save();
    expect.verifySteps([`${USER_VALUES} {"paragraph-margin-top":"8px"}`]);
});

test("theme tab: discard writes no previewed value", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains(numberInput("paragraph-margin-top")).edit("8");
    await contains(".o-snippets-top-actions [data-action='cancel']").click();
    await contains(".modal-content button.btn-primary").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([]);
});

// A saved value, over the compiled one (which is the default here).
const SAVED_VALUES = `html:root { --body-line-height: 2; --headings-line-height: 2; }`;

test("theme tab: a reset previews the default and is written on save", async () => {
    mockThemeRpcs();
    // The defaults are printed by the compiled CSS.
    await setupWebsiteBuilder(`<p>Text</p>`, {
        loadIframeBundles: true,
        styleContent: SAVED_VALUES,
    });
    await contains("#theme-tab").click();

    expect(":iframe p").toHaveStyle({ "line-height": "32px" });
    await contains(
        `${PARAGRAPH} [data-label='Line Height'] button[title='Reset to default']`
    ).click();
    expect(":iframe p").toHaveStyle({ "line-height": "24px" });
    expect(numberInput("body-line-height")).toHaveValue(1.5);

    await save();
    expect.verifySteps([`${USER_VALUES} {"body-line-height":"null"}`]);
});

test("theme tab: a reset heading level follows the headings value", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder(`<h4 style="font-size: 20px">H4</h4>`, {
        loadIframeBundles: true,
        styleContent: SAVED_VALUES,
    });
    await contains("#theme-tab").click();

    await contains(`${HEADINGS} [data-label='Line Height'] .o_hb_collapse_toggler`).click();
    await contains(numberInput("h4-line-height")).edit("1");
    expect(":iframe h4").toHaveStyle({ "line-height": "20px" });
    // All the line heights, the headings one included.
    await contains(
        `${HEADINGS} [data-label='Line Height'] button[title='Reset to default']`
    ).click();
    expect(":iframe h4").toHaveStyle({ "line-height": "24px" });
    await contains(numberInput("headings-line-height")).edit("2");
    expect(":iframe h4").toHaveStyle({ "line-height": "40px" });
});

test("theme tab: the sliders mark the theme default", async () => {
    // The defaults are printed by the compiled CSS.
    await setupWebsiteBuilder("", { loadIframeBundles: true });
    await contains("#theme-tab").click();

    // The Paragraph block mounts once the page's fonts are ready.
    const mark = await waitFor(`${PARAGRAPH} [data-label='Line Height'] .o-hb-range-default`);
    // 1.5 on the paragraph line height's 1-2.5 range.
    const position = "--o-hb-range-default-position: 0.3333333333333333;";
    expect(mark).toHaveAttribute("style", position);
    // Moving the value does not move the mark.
    await contains(numberInput("body-line-height")).edit("2");
    expect(mark).toHaveAttribute("style", position);
});

// Each value changes the page at once: the compiled CSS reads it from its
// variable. `expand` is the row that holds `option` in its collapse (its
// option, or a selector). `select` is the row of a select, where `value` is
// picked; `input`, the input to edit when it isn't found by its option. Font sizes stay at most 20px, where Bootstrap's rfs doesn't make
// them fluid; the line height probes have a fixed font size. The fonts are the
// system ones, which load nothing.
const PARAGRAPH = "[data-container-title='Paragraph']";
const HEADINGS = "[data-container-title='Headings']";
const BUTTONS = "[data-container-title='Button']";
const INPUTS = "[data-container-title='Input Fields']";
const INPUT = ".form-control:not(.form-control-sm, .form-control-lg)";
const SYSTEM_FONTS =
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Ubuntu, "Noto Sans", Arial, "Odoo Unicode Support Noto", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"';
// prettier-ignore
const PREVIEWED_VALUES = [
    { option: "box-shadow-offset-x", value: "20", expand: "[data-label='Normal']", element: ".shadow", property: "box-shadow", expected: "rgba(0, 0, 0, 0.12) 20px 4px 16px 0px" },
    { option: "box-shadow-color", value: "#FF0000", element: ".shadow", property: "box-shadow", expected: "rgb(255, 0, 0) 0px 4px 16px 0px" },
    { option: "font-size-base", value: "18", element: "p", property: "font-size", expected: "18px" },
    { option: "small-font-size", value: "12", expand: "font-size-base", element: "small", property: "font-size", expected: "12px" },
    { option: "body-line-height", value: "2", element: "p", property: "line-height", expected: "32px" },
    { option: "paragraph-margin-top", value: "10", element: "p", property: "margin-top", expected: "10px" },
    { option: "paragraph-margin-bottom", value: "20", element: "p", property: "margin-bottom", expected: "20px" },
    { option: "h1-font-size", value: "20", element: "h1", property: "font-size", expected: "20px" },
    { option: "h3-font-size", value: "18", expand: "h1-font-size", element: "h3", property: "font-size", expected: "18px" },
    { option: "headings-line-height", value: "2", element: "h4", property: "line-height", expected: "40px" },
    { option: "h4-line-height", value: "2", expand: "headings-line-height", element: "h4", property: "line-height", expected: "40px" },
    { option: "display-2-line-height", value: "2", expand: "headings-line-height", element: ".display-2", property: "line-height", expected: "40px" },
    { option: "headings-margin-top", value: "10", element: "h2", property: "margin-top", expected: "10px" },
    { option: "headings-margin-bottom", value: "6", element: "h2", property: "margin-bottom", expected: "6px" },
    { option: "h5-margin-bottom", value: "12", expand: "headings-margin-bottom", element: "h5", property: "margin-bottom", expected: "12px" },
    { option: "font", value: "'SYSTEM_FONTS'", select: `${PARAGRAPH} [data-label='Font Family']`, element: "p", property: "font-family", expected: SYSTEM_FONTS },
    { option: "headings-font", value: "'SYSTEM_FONTS'", select: `${HEADINGS} [data-label='Font Family']`, element: "h3", property: "font-family", expected: SYSTEM_FONTS },
    { option: "h3-font", value: "'SYSTEM_FONTS'", expand: "headings-font", select: `${HEADINGS} [data-label='Heading 3']`, element: "h3", property: "font-family", expected: SYSTEM_FONTS },
    { option: "font-weight-normal", value: "300", select: `${PARAGRAPH} [data-label='Font Weight']`, element: "p", property: "font-weight", expected: "300" },
    { option: "font-weight-bolder", value: "900", expand: `${PARAGRAPH} [data-label='Font Weight']`, select: `${PARAGRAPH} [data-label='Bold']`, element: "p b", property: "font-weight", expected: "900" },
    { option: "headings-font-weight", value: "700", select: `${HEADINGS} [data-label='Font Weight']`, element: "h2", property: "font-weight", expected: "700" },
    { option: "headings-font-weight-bold", value: "900", expand: `${HEADINGS} [data-label='Font Weight']`, select: `${HEADINGS} [data-label='Bold']`, element: "h2 b", property: "font-weight", expected: "900" },
    { option: "display-2-font", value: "'SYSTEM_FONTS'", expand: "headings-font", select: `${HEADINGS} [data-label='Display 2']`, element: ".display-2", property: "font-family", expected: SYSTEM_FONTS },
    { option: "display-1-margin-top", value: "30", expand: "headings-margin-top", element: ".display-1", property: "margin-top", expected: "30px" },
    { option: "btn-padding-y", value: "10", element: ".btn:not(.btn-lg, .btn-sm)", property: "padding-top", expected: "10px" },
    { option: "btn-padding-x", value: "20", element: ".btn:not(.btn-lg, .btn-sm)", property: "padding-left", expected: "20px" },
    { option: "btn-padding-y-lg", value: "14", expand: "btn-padding-y", element: ".btn-lg", property: "padding-top", expected: "14px" },
    { option: "btn-font-size", value: "18", element: ".btn:not(.btn-lg, .btn-sm)", property: "font-size", expected: "18px" },
    { option: "btn-font-size-sm", value: "12", expand: "btn-font-size", element: ".btn-sm", property: "font-size", expected: "12px" },
    { option: "btn-border-radius", value: "12", element: ".btn:not(.btn-lg, .btn-sm)", property: "border-top-left-radius", expected: "12px" },
    { option: "btn-border-radius-lg", value: "20", expand: "btn-border-radius", element: ".btn-lg", property: "border-top-left-radius", expected: "20px" },
    { option: "buttons-font", value: "'SYSTEM_FONTS'", select: `${BUTTONS} [data-label='Font Family']`, element: ".btn:not(.btn-lg, .btn-sm)", property: "font-family", expected: SYSTEM_FONTS },
    { option: "btn-font-weight", value: "300", select: `${BUTTONS} [data-label='Font Weight']`, element: ".btn:not(.btn-lg, .btn-sm)", property: "font-weight", expected: "300" },
    { option: "input-padding-y", value: "10", element: INPUT, property: "padding-top", expected: "10px" },
    { option: "input-padding-x", value: "20", element: INPUT, property: "padding-left", expected: "20px" },
    { option: "input-padding-y-lg", value: "14", expand: "input-padding-y", element: ".form-control-lg", property: "padding-top", expected: "14px" },
    { option: "input-font-size", value: "18", element: INPUT, property: "font-size", expected: "18px" },
    { option: "input-font-size-sm", value: "12", expand: "input-font-size", element: ".form-control-sm", property: "font-size", expected: "12px" },
    { option: "input-border-width", value: "3", input: `${INPUTS} [data-label='Border Width'] input.o-hb-input-number`, element: INPUT, property: "border-top-width", expected: "3px" },
    { option: "input-border-radius", value: "12", element: INPUT, property: "border-top-left-radius", expected: "12px" },
    { option: "input-border-radius-lg", value: "20", expand: "input-border-radius", element: ".form-control-lg", property: "border-top-left-radius", expected: "20px" },
];

// prettier-ignore
for (const { option, value, expand, select, input, element, property, expected } of PREVIEWED_VALUES) {
    test(`theme tab: ${option} is previewed on the page`, async () => {
        mockThemeRpcs();
        await setupWebsiteBuilder(
            `<p>Text <small>small</small> <b>bold</b></p>
            <h1>H1</h1><h2>H2 <b>bold</b></h2><h3>H3</h3>
            <h4 style="font-size: 20px">H4</h4><h5>H5</h5>
            <div class="display-1">Display 1</div>
            <div class="display-2" style="font-size: 20px">Display 2</div>
            <div class="shadow">Shadow</div>
            <a class="btn btn-primary">Button</a>
            <a class="btn btn-primary btn-lg">Large</a>
            <a class="btn btn-primary btn-sm">Small</a>
            <input class="form-control"/>
            <input class="form-control form-control-sm"/>
            <input class="form-control form-control-lg"/>`,
            {
                loadIframeBundles: true,
                // The page's fonts, with their weights (the page loads none).
                styleContent: `
                    @font-face { font-family: "Inter"; font-weight: 100 900; src: local("Arial"); }
                    @font-face { font-family: "Inter Tight"; font-weight: 100 900; src: local("Arial"); }`,
            }
        );
        await contains("#theme-tab").click();
        if (expand) {
            const optionEl = await waitFor(
                expand.startsWith("[") ? expand : `[data-action-param='${expand}']`
            );
            const rowEl = optionEl.closest("[data-label]");
            await contains(rowEl.querySelector(".o_hb_collapse_toggler")).click();
        }
        expect(`:iframe ${element}`).not.toHaveStyle({ [property]: expected });

        if (value.startsWith("#")) {
            await contains("div[data-label='Normal'] button.o_we_color_preview").click();
            await contains(`.o_popover button.o_color_button[data-color='${value}']`).click();
        } else if (select) {
            await contains(`${select} .o-hb-select-toggle`).click();
            await contains(`.o-dropdown--menu [data-action-value="${value}"]`).click();
        } else {
            await contains(input || numberInput(option)).edit(value);
        }
        expect(`:iframe ${element}`).toHaveStyle({ [property]: expected });
        expect.verifySteps([]);
    });
}

test("theme tab: a display font size is previewed on the page", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder(`<div class="display-1">Display 1</div>`, {
        loadIframeBundles: true,
    });
    await contains("#theme-tab").click();
    await contains(`${HEADINGS} [data-label='Heading 1'] .o_hb_collapse_toggler`).click();
    await contains(numberInput("display-1-font-size")).edit("24");
    // From 24px, Bootstrap's rfs makes it fluid below 1200px: at most 24px,
    // at least 20.4px.
    const fontSize = parseFloat(getComputedStyle(queryFirst(":iframe .display-1")).fontSize);
    expect(fontSize).toBeWithin(20.4, 24);
});

test("theme tab: a border side set apart is previewed", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder(`<input class="form-control"/>`, { loadIframeBundles: true });
    await contains("#theme-tab").click();
    await contains(`${INPUTS} [data-label='Border Width'] input.o-hb-input-number`).edit("2");
    await contains(`${INPUTS} [data-label='Border Width'] .o_hb_collapse_toggler`).click();
    await contains(`${INPUTS} [data-label='Bottom'] input.o-hb-input-number`).edit("5");
    // Its rule is gated on `data-o-theme-gates`.
    expect(":iframe html").toHaveAttribute("data-o-theme-gates", /input-border-bottom-width/);
    expect(":iframe .form-control").toHaveStyle({ "border-top-width": "2px" });
    expect(":iframe .form-control").toHaveStyle({ "border-bottom-width": "5px" });

    await save();
    expect.verifySteps([
        `${USER_VALUES} {"input-border-width":"null","input-border-top-width":"0.125rem","input-border-right-width":"0.125rem","input-border-bottom-width":"0.3125rem","input-border-left-width":"0.125rem"}`,
    ]);
});

test("theme tab: hovering a color previews it, leaving the picker reverts it", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains("div[data-label='Normal'] button.o_we_color_preview").click();
    await contains(".o_popover button.o_color_button[data-color='#FF0000']").hover();
    expect(websiteRootStyle().getPropertyValue("--box-shadow-color")).toBe("#FF0000");

    await contains(".o_popover .o_font_color_selector").hover();
    expect(websiteRootStyle().getPropertyValue("--box-shadow-color")).toBe("");

    await save();
    expect.verifySteps([]);
});
