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
// variable. `expand` is the option of the row that holds `option` in its
// collapse. Font sizes stay at most 20px, where Bootstrap's rfs doesn't make
// them fluid; the line height probes have a fixed font size.
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
];

for (const { option, value, expand, element, property, expected } of PREVIEWED_VALUES) {
    test(`theme tab: ${option} is previewed on the page`, async () => {
        mockThemeRpcs();
        await setupWebsiteBuilder(
            `<p>Text <small>small</small></p>
            <h1>H1</h1><h2>H2</h2><h3>H3</h3>
            <h4 style="font-size: 20px">H4</h4><h5>H5</h5>
            <div class="display-1">Display 1</div>
            <div class="display-2" style="font-size: 20px">Display 2</div>
            <div class="shadow">Shadow</div>`,
            { loadIframeBundles: true }
        );
        await contains("#theme-tab").click();
        if (expand) {
            const inputEl = await waitFor(`[data-action-param='${expand}']`);
            const rowEl = inputEl.closest("[data-label]");
            await contains(rowEl.querySelector(".o_hb_collapse_toggler")).click();
        }
        expect(`:iframe ${element}`).not.toHaveStyle({ [property]: expected });

        if (value.startsWith("#")) {
            await contains("div[data-label='Color'] button.o_we_color_preview").click();
            await contains(`.o_popover button.o_color_button[data-color='${value}']`).click();
        } else {
            await contains(`[data-action-param='${option}'] input`).edit(value);
        }
        expect(`:iframe ${element}`).toHaveStyle({ [property]: expected });
        expect.verifySteps([]);
    });
}

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
