import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { waitFor, queryOne } from "@odoo/hoot-dom";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("Floating toolbar visual consistency and usability", async () => {
    // Initialize the builder with sample content to trigger toolbars and popovers
    await setupWebsiteBuilder(`<p>Test floating toolbar UI</p>`);
    const paragraph = queryOne(":iframe p");
    setSelection({
        anchorNode: paragraph.firstChild,
        anchorOffset: 0,
        focusOffset: 4,
    });

    await waitFor(".o-we-toolbar");
    await expandToolbar();

    // Verify animation option dropdown matches font style popover design
    await contains(".o-we-toolbar button[title='Animate Text']").click();
    await waitFor(".o_popover:has(> .o_animate_text_popover)");
    await contains(".o_animate_text_popover .hb-row-content button").click();
    await waitFor(".o_popover:has([data-action-value='onAppearance'])");

    const animationDropdown = await waitFor(".o_popover:has([data-action-value='onAppearance']");
    expect(animationDropdown).not.toHaveClass("o-hb-select-dropdown");

    // Verify highlight text configurator
    await contains(".o-we-toolbar button[title='Apply highlight']").click();
    await waitFor(".o_popover:has(> .o_highlight_picker_grid)");

    // Assert highlight picker grid is scrollable and scrollbar is hidden
    const textHighlightDropdown = await waitFor(".o_highlight_picker_grid");
    expect(textHighlightDropdown).toHaveStyle({ overflow: "auto", scrollbarWidth: "none" });

    // Select underline highlight option
    await contains(".o_highlight_picker_grid .o_text_highlight_underline").click();

    // Assert highlight color picker has sublevel rows for hierarchy
    const colorLabel = await waitFor(".o_highlight_picker_grid label[for='colorButton']");
    const sublevelRow = colorLabel.closest(".hb-row-sublevel-1");
    expect(sublevelRow).toHaveClass("hb-row-sublevel-1");
});
