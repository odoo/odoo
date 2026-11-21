import { expect, test } from "@odoo/hoot";
import { generateGMapIframe } from "@website/snippets/s_map/map";
import { contains } from "@web/../tests/web_test_helpers";
import { getIframeInput } from "@html_editor/../tests/_helpers/iframe_input";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

// In tests, the map template has no iframe, so the map has no size and can't be
// clicked: give it one, as a real map with an address.
function setupMap() {
    return setupWebsiteBuilderWithSnippet("s_map", {
        loadIframeBuilderTemplates: true,
        onIframeLoaded: (iframe) => {
            const mapEl = iframe.contentDocument.querySelector(".s_map");
            mapEl.dataset.mapAddress = "Rue de la Loi 16, Brussels";
            mapEl.querySelector(".map_container").prepend(generateGMapIframe());
        },
    });
}

test("test description option", async () => {
    await setupMap();
    await contains(":iframe .s_map").click();

    // toggle description
    await contains("[data-action-id='mapDescription'] input").click();
    expect(":iframe .s_map .description").toBeVisible();

    // Description Text is editable
    expect(":iframe .s_map .description").toHaveAttribute("contenteditable", "true");

    // Check Gradient tab background color
    await contains("div[data-label='Background Color'] .o_we_color_preview").click();
    await contains(".o_popover .o_font_color_selector .btn-tab:contains('Gradient')").click();
    await contains(
        ".o_colorpicker_sections .o_color_button[data-color='linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)']"
    ).click();
    expect(":iframe .s_map .description").toHaveStyle({
        "background-image": "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)",
    });

    // Check Custom tab background color
    await contains("div[data-label='Background Color'] .o_we_color_preview").click();
    await contains(".o_popover .o_font_color_selector .btn-tab:contains('Custom')").click();
    const hexInputEl = await getIframeInput(
        ".o_font_color_selector .o_color_picker_inputs iframe.o_hex_iframe",
        "input[name='hex_input']"
    );
    await contains(hexInputEl).edit("#E4F641");
    expect(":iframe .s_map .description").toHaveStyle({ "background-color": "rgb(228, 246, 65)" });
});

test("clearing the address hides the map, setting one shows it again", async () => {
    await setupMap();
    await contains(":iframe .s_map").click();

    await contains("[data-label='Address'] input").edit("");
    expect(":iframe .s_map").not.toHaveAttribute("data-map-address");
    expect(":iframe .s_map .s_map_embedded").toHaveClass("d-none");

    await contains("[data-label='Address'] input").edit("Grand Place, Brussels");
    expect(":iframe .s_map").toHaveAttribute("data-map-address", "Grand Place, Brussels");
    expect(":iframe .s_map .s_map_embedded").not.toHaveClass("d-none");
});
