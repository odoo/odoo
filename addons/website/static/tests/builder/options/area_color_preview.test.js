import { expect, queryFirst, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import { getIframeInput } from "@html_editor/../tests/_helpers/iframe_input";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

const PALETTE = "/website/static/src/scss/options/colors/user_color_palette.scss";
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
    onRpc("/website/theme_computed_colors", () => ({ values: {}, gates: {} }));
}

// A page breadcrumb as the server renders it: its color preset as a class.
async function setupBreadcrumb() {
    await setupWebsiteBuilder("", {
        styleContent: ":root { --breadcrumb: 1; }",
        onIframeLoaded: (iframe) => {
            const doc = iframe.contentDocument;
            const main = doc.createElement("main");
            main.innerHTML = `<div class="o_page_breadcrumb" data-name="Breadcrumb">
                <nav class="o_cc1" data-o-cc-area="breadcrumb">Breadcrumb</nav></div>`;
            doc.querySelector("#wrap").before(main);
        },
    });
    await contains(":iframe .o_page_breadcrumb").click();
    await contains("[data-label='Background Color'] button.o_we_color_preview").click();
}

async function save() {
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
}

test("an area's color preset is previewed as its class, written on save", async () => {
    mockThemeRpcs();
    await setupBreadcrumb();
    await contains(".o_popover [data-color='o_cc3']").click();
    expect(":iframe .o_page_breadcrumb nav").toHaveClass("o_cc3");
    expect(":iframe .o_page_breadcrumb nav").not.toHaveClass("o_cc1");
    expect.verifySteps([]);
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"breadcrumb-gradient":"NULL"}`,
        `${PALETTE} {"breadcrumb-custom":"NULL","breadcrumb":"3"}`,
    ]);
});

test("an area's custom color and gradient switch their rules on", async () => {
    mockThemeRpcs();
    await setupBreadcrumb();
    const gates = () => queryFirst(":iframe html").dataset.oThemeGates || "";
    await contains(".o_popover .custom-tab").click();
    const hexInputEl = await getIframeInput(
        ".o_font_color_selector .o_color_picker_inputs iframe.o_hex_iframe",
        "input[name='hex_input']"
    );
    await contains(hexInputEl).edit("#FF0000");
    expect(gates()).toInclude("breadcrumb-custom");
    expect(queryFirst(":iframe html").style.getPropertyValue("--breadcrumb-custom")).toBe(
        "#FF0000"
    );
    await contains(".o_popover .gradient-tab").click();
    await contains(".o_popover .o_colorpicker_sections .o_color_button").click();
    expect(gates()).toInclude("breadcrumb-gradient");
    expect(gates()).not.toInclude("breadcrumb-custom");
    expect.verifySteps([]);
});
