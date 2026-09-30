import { expect, queryFirst, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
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
