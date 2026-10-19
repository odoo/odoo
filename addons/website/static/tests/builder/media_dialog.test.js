import { describe, expect, test } from "@odoo/hoot";
import { click, dblclick, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Icon styles should be retained when it is replaced with another icon", async () => {
    const extractClasses = "rounded-circle rounded shadow img-thumbnail";
    await setupWebsiteBuilder(`<i class="oi ${extractClasses}" data-icon="search"/>`);

    await dblclick(":iframe .oi");
    await animationFrame();
    await click("[data-icon=favorite]");
    await animationFrame();
    expect(":iframe [data-icon=favorite]").toHaveClass(extractClasses);
});

function mockIconFontCustomization() {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            // Stand in for the recompiled bundle, which prints the customized
            // SCSS variable as a CSS variable on the website `:root`.
            queryOne(":iframe html").style.setProperty(
                "--icon-font-family",
                `'${changes["icon-font-family"]}'`
            );
        }
    }
    defineModels([WebsiteAssets]);
    onRpc("/website/theme_customize_bundle_reload", () => ({}));
}

describe("Icon styles", () => {
    test("Use the icon font selected in the theme options", async () => {
        mockIconFontCustomization();
        await setupWebsiteBuilder(`<i class="oi" data-icon="search"/>`);
        await contains(".o-snippets-tabs button[data-name=theme]").click();
        await contains(".o_theme_tab [data-action-param='icon-font-family'][data-action-value='Material Symbols Sharp']").click();
        await dblclick(":iframe .oi");
        await waitFor(".font-icons-icons [data-icon='favorite']");
        expect(".font-icons-icons [data-icon='favorite']").toHaveStyle({ fontFamily: /Material Symbols Sharp/ });
        // Odoo custom icons have their own font, whatever the selected variant.
        expect(".font-icons-icons [data-icon^='oi_']").toHaveCount(null, { message: "Odoo custom icons are listed" });
        expect(".font-icons-icons [data-icon^='oi_']").toHaveStyle({ fontFamily: /odoo_ui_icons/ });
    });

    test("Icons use the outlined font with the default theme options", async () => {
        await setupWebsiteBuilder(`<i class="oi" data-icon="search"/>`);
        await dblclick(":iframe .oi");
        await waitFor(".font-icons-icons [data-icon='favorite']");
        expect(".font-icons-icons [data-icon='favorite']").toHaveStyle({ fontFamily: /Material Symbols Outlined/ });
        expect(".font-icons-icons [data-icon^='oi_']").toHaveStyle({ fontFamily: /odoo_ui_icons/ });
    });
});
