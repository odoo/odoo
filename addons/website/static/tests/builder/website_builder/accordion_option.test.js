import { expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("replace the custom icons of an accordion from the icon picker", async () => {
    await setupWebsiteBuilderWithSnippet("s_accordion");
    await contains(":iframe .s_accordion").click();
    await contains("[data-label='Icons'] .dropdown-toggle").click();
    await contains(".o_popover [data-action-value='custom']").click();
    expect(":iframe .s_accordion .accordion").toHaveAttribute(
        "data-active-custom-icon",
        "arrow_upward"
    );

    await contains("[data-action-id='defineCustomIcon']:first").click();
    await contains(".o-IconPicker-icon[data-icon='favorite'].oi-filled").click();
    expect(".o-IconPicker").toHaveCount(0);
    expect(":iframe .s_accordion .accordion").toHaveAttribute(
        "data-active-custom-icon",
        "favorite"
    );
    expect(":iframe .s_accordion .o_custom_icon_active i").toHaveAttribute("data-icon", "favorite");
    expect(":iframe .s_accordion .o_custom_icon_active i").toHaveClass("oi-filled");
    expect(":iframe .s_accordion .accordion").toHaveAttribute(
        "data-inactive-custom-icon",
        "arrow_downward"
    );

    // The current icon is highlighted when replacing it again
    await contains("[data-action-id='defineCustomIcon']:first").click();
    expect(".o-IconPicker-icon.o-selected").toHaveAttribute("data-icon", "favorite");
    await press("Escape");
    await animationFrame();
    expect(".o-IconPicker").toHaveCount(0);
    expect(":iframe .s_accordion .accordion").toHaveAttribute(
        "data-active-custom-icon",
        "favorite"
    );
});
