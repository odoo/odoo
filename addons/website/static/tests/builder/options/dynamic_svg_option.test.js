import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";

defineWebsiteModels();

test("can change the dynamic color", async () => {
    await setupWebsiteBuilder(
        "<img src='/html_editor/shape/test.svg?c1=rgba(0,0,0,.25)&c2=rgba(0,0,0,.5)' class='testSvg'/>"
    );
    await contains(":iframe img.testSvg").click();
    await contains(
        ".hb-row[data-label='Dynamic Colors'] button.o_we_color_preview:first-child"
    ).click();
    await contains(".o_popover .o_color_button[data-color='#FF0000']").click();
    await animationFrame();
    const searchParams = new URL(queryOne(":iframe img.testSvg").src, window.location.origin)
        .searchParams;
    expect(searchParams.get("c1")).toBe("#FF0000");
    expect(searchParams.get("c2")).toBe("rgba(0,0,0,.5)");
});

test("can change the dynamic color to a var color", async () => {
    await setupWebsiteBuilder(
        `<img src='/html_editor/shape/test.svg?c1=rgba(0,0,0,.25)&c2=rgba(0,0,0,.5)' class='testSvg'/>`,
        { loadIframeBundles: true }
    );
    const color = getCSSVariableValue("o-color-1", getHtmlStyle(document));
    await contains(":iframe img.testSvg").click();
    await contains(
        ".hb-row[data-label='Dynamic Colors'] button.o_we_color_preview:nth-child(2)"
    ).click();
    await contains(".o_popover .o_color_button[data-color='o-color-1']").click();
    await animationFrame();
    const searchParams = new URL(queryOne(":iframe img.testSvg").src, window.location.origin)
        .searchParams;
    expect(searchParams.get("c2")).toBe(color);
});
