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

    await contains("[data-action-param='box-shadow-offset-x'] input").edit("20");
    expect(websiteRootStyle().getPropertyValue("--box-shadow-offset-x")).toBe("1.25rem");

    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(websiteRootStyle().getPropertyValue("--box-shadow-offset-x")).toBe("");

    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    expect(websiteRootStyle().getPropertyValue("--box-shadow-offset-x")).toBe("1.25rem");
    expect.verifySteps([]);

    await save();
    expect.verifySteps([`${USER_VALUES} {"box-shadow-offset-x":"1.25rem"}`]);
});

test("theme tab: discard writes no previewed value", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains("[data-action-param='box-shadow-offset-x'] input").edit("20");
    await contains(".o-snippets-top-actions [data-action='cancel']").click();
    await contains(".modal-content button.btn-primary").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([]);
});

test("theme tab: an emptied value removes the preview and is reset on save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains("[data-action-param='body-line-height'] input").edit("2");
    expect(websiteRootStyle().getPropertyValue("--body-line-height")).toBe("2");
    await contains("[data-action-param='body-line-height'] input").clear();
    expect(websiteRootStyle().getPropertyValue("--body-line-height")).toBe("");

    await save();
    expect.verifySteps([`${USER_VALUES} {"body-line-height":"null"}`]);
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
    { option: "box-shadow-offset-x", value: "20", element: ".shadow", property: "box-shadow", expected: "rgba(0, 0, 0, 0.12) 20px 4px 16px 0px" },
    { option: "box-shadow-color", value: "#FF0000", expand: "box-shadow-offset-x", element: ".shadow", property: "box-shadow", expected: "rgb(255, 0, 0) 0px 4px 16px 0px" },
    { option: "font-size-base", value: "18", element: "p", property: "font-size", expected: "18px" },
    { option: "small-font-size", value: "12", expand: "font-size-base", element: "small", property: "font-size", expected: "12px" },
    { option: "body-line-height", value: "2", element: "p", property: "line-height", expected: "32px" },
    { option: "paragraph-margin-top", value: "10", element: "p", property: "margin-top", expected: "10px" },
    { option: "paragraph-margin-bottom", value: "20", element: "p", property: "margin-bottom", expected: "20px" },
    { option: "h1-font-size", value: "20", element: "h1", property: "font-size", expected: "20px" },
    { option: "h3-font-size", value: "18", expand: "h1-font-size", element: "h3", property: "font-size", expected: "18px" },
    { option: "display-1-font-size", value: "20", expand: "h1-font-size", element: ".display-1", property: "font-size", expected: "20px" },
    { option: "headings-line-height", value: "2", element: "h4", property: "line-height", expected: "40px" },
    { option: "h4-line-height", value: "2", expand: "headings-line-height", element: "h4", property: "line-height", expected: "40px" },
    { option: "display-2-line-height", value: "2", expand: "headings-line-height", element: ".display-2", property: "line-height", expected: "40px" },
    { option: "headings-margin-top", value: "10", element: "h2", property: "margin-top", expected: "10px" },
    { option: "headings-margin-bottom", value: "6", element: "h2", property: "margin-bottom", expected: "6px" },
    { option: "h5-margin-bottom", value: "12", expand: "headings-margin-top", element: "h5", property: "margin-bottom", expected: "12px" },
    { option: "font", value: "'SYSTEM_FONTS'", select: `${PARAGRAPH} [data-label='Font Family']`, element: "p", property: "font-family", expected: SYSTEM_FONTS },
    { option: "headings-font", value: "'SYSTEM_FONTS'", select: `${HEADINGS} [data-label='Font Family']`, element: "h3", property: "font-family", expected: SYSTEM_FONTS },
    { option: "h3-font", value: "'SYSTEM_FONTS'", expand: "headings-font", select: `${HEADINGS} [data-label='Heading 3']`, element: "h3", property: "font-family", expected: SYSTEM_FONTS },
    { option: "font-weight-normal", value: "300", select: `${PARAGRAPH} [data-label='Font Weight']`, element: "p", property: "font-weight", expected: "300" },
    { option: "font-weight-bolder", value: "900", expand: `${PARAGRAPH} [data-label='Font Weight']`, select: `${PARAGRAPH} [data-label='Bold']`, element: "p b", property: "font-weight", expected: "900" },
    { option: "headings-font-weight", value: "700", select: `${HEADINGS} [data-label='Font Weight']`, element: "h2", property: "font-weight", expected: "700" },
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
    { option: "input-border-width", value: "3", input: `${INPUTS} [data-label='Border Width'] input`, element: INPUT, property: "border-top-width", expected: "3px" },
    { option: "input-border-radius", value: "12", element: INPUT, property: "border-top-left-radius", expected: "12px" },
    { option: "input-border-radius-lg", value: "20", expand: "input-border-radius", element: ".form-control-lg", property: "border-top-left-radius", expected: "20px" },
];

// prettier-ignore
for (const { option, value, expand, select, input, element, property, expected } of PREVIEWED_VALUES) {
    test(`theme tab: ${option} is previewed on the page`, async () => {
        mockThemeRpcs();
        await setupWebsiteBuilder(
            `<p>Text <small>small</small> <b>bold</b></p>
            <h1>H1</h1><h2>H2</h2><h3>H3</h3>
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
            await contains("div[data-label='Color'] button.o_we_color_preview").click();
            await contains(`.o_popover button.o_color_button[data-color='${value}']`).click();
        } else if (select) {
            await contains(`${select} .o-hb-select-toggle`).click();
            await contains(`.o-dropdown--menu [data-action-value="${value}"]`).click();
        } else {
            await contains(input || `[data-action-param='${option}'] input`).edit(value);
        }
        expect(`:iframe ${element}`).toHaveStyle({ [property]: expected });
        expect.verifySteps([]);
    });
}

test("theme tab: a border side set apart keeps the widths shown until save", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder(`<input class="form-control"/>`, { loadIframeBundles: true });
    await contains("#theme-tab").click();
    await contains(`${INPUTS} [data-label='Border Width'] input`).edit("2");
    await contains(`${INPUTS} [data-label='Border Width'] .o_hb_collapse_toggler`).click();
    await contains(`${INPUTS} [data-label='Bottom'] input`).edit("5");
    // The side applies on save: the compiled CSS has no rule for it before.
    expect(":iframe .form-control").toHaveStyle({ "border-top-width": "2px" });
    expect(":iframe .form-control").toHaveStyle({ "border-bottom-width": "2px" });

    await save();
    expect.verifySteps([
        `${USER_VALUES} {"input-border-width":"null","input-border-top-width":"0.125rem","input-border-right-width":"0.125rem","input-border-bottom-width":"0.3125rem","input-border-left-width":"0.125rem"}`,
    ]);
});

test("theme tab: hovering a color previews it, leaving the picker reverts it", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();

    await contains("div.hb-row-label:contains('Normal')").click();
    await contains("div[data-label='Color'] button.o_we_color_preview").click();
    await contains(".o_popover button.o_color_button[data-color='#FF0000']").hover();
    expect(websiteRootStyle().getPropertyValue("--box-shadow-color")).toBe("#FF0000");

    await contains(".o_popover .o_font_color_selector").hover();
    expect(websiteRootStyle().getPropertyValue("--box-shadow-color")).toBe("");

    await save();
    expect.verifySteps([]);
});
