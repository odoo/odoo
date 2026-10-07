import { expect, queryFirst, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getIframeInput } from "@html_editor/../tests/_helpers/iframe_input";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

const PALETTE = "/website/static/src/scss/options/colors/user_color_palette.scss";
const USER_VALUES = "/website/static/src/scss/options/user_values.scss";

function mockThemeRpcs({ stepComputedColors = false } = {}) {
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
    onRpc("/website/theme_computed_colors", () => {
        if (stepComputedColors) {
            expect.step("computed colors");
        }
        return { values: {}, gates: {} };
    });
}

// A page breadcrumb (its color preset is compiled in).
async function setupBreadcrumb(styleContent = ":root { --breadcrumb: 1; }") {
    await setupWebsiteBuilder("", {
        styleContent,
        onIframeLoaded: (iframe) => {
            const doc = iframe.contentDocument;
            const main = doc.createElement("main");
            main.innerHTML = `<div class="o_page_breadcrumb" data-name="Breadcrumb">
                <nav>Breadcrumb</nav></div>`;
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
    expect(":iframe .o_page_breadcrumb nav").toHaveAttribute("data-o-cc-area", "breadcrumb");
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(":iframe .o_page_breadcrumb nav").not.toHaveClass("o_cc3");
    expect(":iframe .o_page_breadcrumb nav").not.toHaveAttribute("data-o-cc-area");
    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    expect(":iframe .o_page_breadcrumb nav").toHaveClass("o_cc3");
    expect.verifySteps([]);
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"breadcrumb-gradient":"NULL"}`,
        `${PALETTE} {"breadcrumb-custom":"NULL","breadcrumb":"3"}`,
    ]);
});

test("hovering an area's color preset keeps the applied one selected", async () => {
    mockThemeRpcs({ stepComputedColors: true });
    await setupBreadcrumb();
    expect(".o_popover [data-color='o_cc1']").toHaveClass("selected");
    await contains(".o_popover [data-color='o_cc3']").hover();
    // The computed colors arrive while previewing, and update the options.
    await expect.waitForSteps(["computed colors"]);
    await animationFrame();
    expect(".o_popover [data-color='o_cc1']").toHaveClass("selected");
    expect(".o_popover [data-color='o_cc3']").not.toHaveClass("selected");
    // Back to the saved colors: nothing left to compute.
    await contains(".o-snippets-top-actions").hover();
    await animationFrame();
    expect.verifySteps([]);
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

test("resetting a saved area color previews it unset", async () => {
    mockThemeRpcs();
    await setupBreadcrumb(":root { --breadcrumb: 1; --breadcrumb-custom: #FF0000; }");
    const htmlEl = queryFirst(":iframe html");
    await contains(".o_popover .o_color_picker_reset").click();
    // Unset, as the compile leaves a null value: not the saved one.
    expect(htmlEl.style.getPropertyValue("--breadcrumb-custom")).toBe("initial");
    expect(getComputedStyle(htmlEl).getPropertyValue("--breadcrumb-custom")).toBe("");
    expect("[data-label='Background Color'] button.o_we_color_preview").not.toHaveAttribute(
        "style",
        /255, 0, 0/
    );
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"breadcrumb-gradient":"NULL"}`,
        `${PALETTE} {"breadcrumb-custom":"NULL","breadcrumb":"NULL"}`,
    ]);
});

test("the portal cards' color preset is previewed as their class", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("", {
        styleContent: ":root { --portal-card: 1; }",
        onIframeLoaded: (iframe) => {
            const main = iframe.contentDocument.createElement("main");
            main.innerHTML = `<div class="o_portal_index_card"><a href="#">Card</a></div>`;
            iframe.contentDocument.querySelector("#wrap").before(main);
        },
    });
    await contains(":iframe .o_portal_index_card > a").click();
    await contains("[data-label='Background Color'] button.o_we_color_preview").click();
    await contains(".o_popover [data-color='o_cc4']").click();
    expect(":iframe .o_portal_index_card > a").toHaveClass("o_cc4");
    expect(":iframe .o_portal_index_card > a").toHaveAttribute("data-o-cc-area", "portal-card");
    await save();
    expect.verifySteps([
        `${USER_VALUES} {"portal-gradient":"NULL"}`,
        `${PALETTE} {"portal-card-custom":"NULL","portal-card":"4"}`,
    ]);
});
