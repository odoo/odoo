import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilderWithSnippet } from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("test description option", async () => {
    await setupWebsiteBuilderWithSnippet("s_map");
    await contains(":iframe .s_map").click();

    // toggle description
    await contains("[data-action-id='mapDescription'] input").click();
    expect(":iframe .s_map .description").toBeVisible();

    // Change Description Text
    await contains("[data-action-id='mapDescriptionTextValue'] input").edit("New description");
    expect(":iframe .s_map .description").toHaveText("New description");

    // Check Gradient tab background color
    await contains("div[data-label='Background Color'] .o_we_color_preview").click();
    await contains(".o_popover .o_font_color_selector .btn-tab:contains('Gradient')").click();
    await contains(".o_colorpicker_sections .o_color_button[data-color='linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)']").click();
    expect(":iframe .s_map .description").toHaveStyle({ "background-image": "linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%)" });

    // Check Custom tab background color
    await contains("div[data-label='Background Color'] .o_we_color_preview").click();
    await contains(".o_popover .o_font_color_selector .btn-tab:contains('Custom')").click();
    await contains(".o_popover .o_colorpicker_widget .o_hex_input").edit("#E4F641");
    expect(":iframe .s_map .description").toHaveStyle({ "background-color": "rgb(228, 246, 65)" });

    // Check text color
    await contains("div[data-label='Text Color'] .o_we_color_preview").click();
    await contains(".o_popover .o_colorpicker_widget .o_hex_input").edit("#EB28EB");
    expect(":iframe .s_map .description").toHaveStyle({ "color": "rgb(235, 40, 235)" });
});
