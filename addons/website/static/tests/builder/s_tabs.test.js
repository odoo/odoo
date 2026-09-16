import { expect, test } from "@odoo/hoot";
import { edit, queryAll, queryFirst, queryOne } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilderWithSnippet } from "./website_helpers";

defineWebsiteModels();

async function setupWebsiteBuilderWithButtonsTabs() {
    const websiteBuilderObject = await setupWebsiteBuilderWithSnippet("s_tabs", {
        loadIframeBundles: true,
    });
    await contains(":iframe .s_tabs .s_tabs_nav").click();
    await contains(".o-hb-select-toggle:contains('Underline')").click();
    await contains(
        ".o-hb-select-dropdown-item[data-action-id='setStyle'][data-action-value='nav-buttons']"
    ).click();
    await websiteBuilderObject.waitSidebarUpdated();
    return websiteBuilderObject;
}

test("set a theme (color combination) background on .s_tabs tabs", async () => {
    await setupWebsiteBuilderWithButtonsTabs();
    await contains(".o_we_color_preview:eq(1)").click();
    await contains(".color-combination-button.o_cc4").click();
    expect(".o_we_color_preview:eq(1)").toHaveStyle({ backgroundColor: "rgb(113, 75, 103)" });
    expect(":iframe .s_tabs_nav .nav-link.active").toHaveStyle({
        backgroundColor: "rgb(27, 19, 25)",
    });
});

test("set a theme (color combination) background on .s_tabs tabs with a custom link color", async () => {
    await setupWebsiteBuilderWithButtonsTabs();
    await contains(".o_we_color_preview:eq(1)").click();
    await contains(".color-combination-button.o_cc4").click();
    await contains(".o_we_color_preview:eq(2)").click();
    await contains(".o_color_button[data-color='#FFFF00']").click();
    expect(".o_we_color_preview:eq(2)").toHaveStyle({ backgroundColor: "rgb(255, 255, 0)" });
    // The active link's color is set from the o_cc class.
    expect(":iframe .s_tabs_nav .nav-link.active").toHaveStyle({ color: "rgb(255, 255, 255)" });
    // The inactive links use the custom color.
    expect(":iframe .s_tabs_nav .nav-link:not(.active)").toHaveStyle({
        color: "rgb(255, 255, 0)",
    });
});

test("setting a dark background uses white as link color to contrast", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilderWithButtonsTabs();
    const navLinksSel = queryAll(":iframe .s_tabs_nav .nav-link");
    expect(navLinksSel).toHaveStyle({ color: "rgb(33, 37, 41)" });
    await contains(".o_we_color_preview:eq(1)").click();
    await contains(".btn-tab.custom-tab").click();
    await contains(".o_hex_iframe:iframe [name='hex_input']").click();
    await edit("#0000FF", { confirm: "enter" });
    await waitSidebarUpdated();
    expect(".o_colorpicker_section .o_color_button.o_color_picker_button:eq(0)").toHaveStyle({
        backgroundColor: "rgb(0, 0, 255)",
    });
    expect(navLinksSel).toHaveStyle({ color: "rgb(255, 255, 255)" });
});

test("setting the link color updates the active tab background to contrast", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilderWithButtonsTabs();
    await contains(".o_we_color_preview:eq(1)").click();
    await contains(".btn-tab.custom-tab").click();
    await contains(".o_color_button[data-color='400']").click();
    await waitSidebarUpdated();
    expect(".o_we_color_preview:eq(1)").toHaveStyle({ backgroundColor: "rgb(206, 212, 218)" });
    expect(":iframe .s_tabs_nav .nav-link.active").toHaveStyle({
        color: "rgb(0, 0, 0)",
        backgroundColor: "rgba(255, 255, 255, 0.5)",
    });
    expect(":iframe .s_tabs_nav .nav-link:not(.active)").toHaveStyle({
        color: "rgb(0, 0, 0)",
        backgroundColor: "rgba(0, 0, 0, 0)",
    });
});

test("switching from buttons tabs to tabs tabs keeps custom colors", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilderWithButtonsTabs();
    await contains(".o_we_color_preview:eq(1)").click();
    await contains(".btn-tab.custom-tab").click();
    await contains(".o_color_button[data-color='400']").click();
    await waitSidebarUpdated();
    expect(".o_we_color_preview:eq(1)").toHaveStyle({ backgroundColor: "rgb(206, 212, 218)" });
    expect(":iframe .s_tabs_nav .nav-link.active").toHaveStyle({
        color: "rgb(0, 0, 0)",
        backgroundColor: "rgba(255, 255, 255, 0.5)",
    });
    expect(":iframe .s_tabs_nav .nav-link:not(.active)").toHaveStyle({
        color: "rgb(0, 0, 0)",
        backgroundColor: "rgba(0, 0, 0, 0)",
    });
    // Switch to tabs tabs
    await contains(":iframe .s_tabs .s_tabs_nav").click();
    await contains(".o-hb-select-toggle:contains('Buttons')").click();
    await contains(
        ".o-hb-select-dropdown-item[data-action-id='setStyle'][data-action-value='nav-tabs']"
    ).click();
    await waitSidebarUpdated();
    expect(".o_we_color_preview:eq(1)").toHaveStyle({ backgroundColor: "rgb(206, 212, 218)" });
    expect(":iframe .s_tabs_nav .nav-link.active").toHaveStyle({
        color: "rgb(0, 0, 0)",
        backgroundColor: "rgba(255, 255, 255, 0.5)",
    });
    expect(":iframe .s_tabs_nav .nav-link:not(.active)").toHaveStyle({
        color: "rgb(0, 0, 0)",
        backgroundColor: "rgba(0, 0, 0, 0)",
    });
});

test("switching back from buttons tabs to underline or pills erases custom colors", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilderWithSnippet("s_tabs", {
        loadIframeBundles: true,
    });
    const tabsNavEl = queryOne(":iframe .s_tabs_nav");
    const activeTabEl = queryOne(":iframe .s_tabs_nav .nav-link.active");
    const inactiveTabEl = queryFirst(":iframe .s_tabs_nav .nav-link:not(.active)");
    const getElStyle = (el, prop) => el.ownerDocument.defaultView.getComputedStyle(el)[prop];
    const tabsNavBackground = getElStyle(tabsNavEl, "backgroundColor");
    const activeTabColor = getElStyle(activeTabEl, "color");
    const inactiveTabColor = getElStyle(inactiveTabEl, "color");
    const activeTabBackground = getElStyle(activeTabEl, "backgroundColor");
    await contains(":iframe .s_tabs .s_tabs_nav").click();
    await contains(".o-hb-select-toggle:contains('Underline')").click();
    await contains(
        ".o-hb-select-dropdown-item[data-action-id='setStyle'][data-action-value='nav-buttons']"
    ).click();
    await waitSidebarUpdated();
    // Update background
    await contains(".o_we_color_preview:eq(1)").click();
    await contains(".btn-tab.custom-tab").click();
    await contains(".o_color_button[data-color='400']").click();
    // Update links
    await contains(".o_we_color_preview:eq(2)").click();
    await contains(".o_color_button[data-color='#FFFF00']").click();
    await waitSidebarUpdated();
    expect(".o_we_color_preview:eq(1)").toHaveStyle({ backgroundColor: "rgb(206, 212, 218)" });
    expect(getElStyle(tabsNavEl, "backgroundColor")).not.toBe(tabsNavBackground);
    expect(getElStyle(activeTabEl, "color")).not.toBe(activeTabColor);
    expect(getElStyle(activeTabEl, "backgroundColor")).not.toBe(activeTabBackground);
    expect(getElStyle(inactiveTabEl, "color")).not.toBe(inactiveTabColor);
    // Switch back to underline tabs
    await contains(":iframe .s_tabs .s_tabs_nav").click();
    await contains(".o-hb-select-toggle:contains('Buttons')").click();
    await contains(
        ".o-hb-select-dropdown-item[data-action-id='setStyle'][data-action-value='nav-underline']"
    ).click();
    await waitSidebarUpdated();
    // The option is not available anymore.
    expect(".hb-row.hb-row-sublevel-1[data-label='Background']").not.toHaveCount();
    // The tabs are back to standard styles.
    expect(tabsNavEl).toHaveStyle({ backgroundColor: tabsNavBackground });
    expect(":iframe .s_tabs_nav .nav-link.active").toHaveStyle({
        color: activeTabColor,
        backgroundColor: activeTabBackground,
    });
    expect(":iframe .s_tabs_nav .nav-link:not(.active)").toHaveStyle({ color: inactiveTabColor });
});
