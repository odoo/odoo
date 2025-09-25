import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { expect, test } from "@odoo/hoot";
import { queryFirst, queryOne, scroll, waitFor, waitUntil } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { animationFrame } from "@odoo/hoot-mock";

defineWebsiteModels();

test("Popovers scroll with iframe", async () => {
    // Top margin to have room to scroll while keeping the popovers visible
    await setupWebsiteBuilder(`<p style="margin-top: 200px">plop</p>`);
    const body = queryFirst(":iframe body");
    const p = queryOne(":iframe p");
    // Make sure we can scroll
    p.style.height = "1000px";
    setSelection({
        anchorNode: p.firstChild,
        anchorOffset: 0,
        focusOffset: 4,
    });

    await waitFor(".o-we-toolbar");
    await expandToolbar();

    const expectScroll = async (popoverSelector) => {
        const popover = await waitFor(popoverSelector);
        const previousTop = parseFloat(popover.style.top);
        popover.style.top = "0px";
        // Wait for the initial call of `reposition`
        await waitUntil(() => popover.style.top !== "0px", { timeout: 500 });

        const delta = 100;
        await scroll(body, { y: delta }, { scrollable: false, force: true });
        await animationFrame();
        expect(popover).toHaveStyle({
            top: `${previousTop - delta}px`,
        });
        await scroll(body, { y: 0 }, { scrollable: false });
        await animationFrame();
        expect(popover).toHaveStyle({
            top: `${previousTop}px`,
        });
    };

    await contains(".o-we-toolbar button.o-select-color-background").click();
    await expectScroll(".o_popover:has(> .o_font_color_selector)");

    await contains(".o-we-toolbar div[name=websiteDecoration] > button").click();
    await expectScroll(".o_popover");

    await contains(".o-we-toolbar button.o-select-highlight").click();
    await expectScroll(".o_popover");

    await contains(".o-we-toolbar button[title='Animate Text']").click();
    await expectScroll(".o_popover:has(> .o_animate_text_popover)");

    await contains(".o-we-toolbar button[name=link]").click();
    await contains(".o-we-linkpopover select[name=link_type]").select("custom");
    await contains(".o-we-linkpopover button.custom-text-picker").click();
    await expectScroll(".o_popover:has(> .o_font_color_selector)");
});
