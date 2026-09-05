import { expect, test } from "@odoo/hoot";
import { click, dblclick, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
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

const MS_ICON_SELECTOR = ".font-icons-icons span[data-icon='favorite']:not(.oi-filled)";
const OI_ICON_SELECTOR = ".font-icons-icons span[data-icon^='oi_']";
const SHARP_OPTION_SELECTOR =
    ".o_theme_tab [data-action-param='icon-font-family'][data-action-value='Material Symbols Sharp']";

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

test("Media dialog icons use the icon font selected in the theme options", async () => {
    mockIconFontCustomization();
    await setupWebsiteBuilder(`<i class="oi" data-icon="search"/>`);
    await click(".o-snippets-tabs button[data-name=theme]");
    await click(SHARP_OPTION_SELECTOR);
    await dblclick(":iframe .oi");
    await waitFor(MS_ICON_SELECTOR);
    expect(MS_ICON_SELECTOR).toHaveStyle({ fontFamily: /Material Symbols Sharp/ });
    // Odoo custom icons have their own font, whatever the selected variant.
    expect(OI_ICON_SELECTOR).toHaveCount(null, { message: "Odoo custom icons are listed" });
    expect(OI_ICON_SELECTOR).toHaveStyle({ fontFamily: /odoo_ui_icons/ });
});

test("Media dialog icons use the rounded font with the default theme options", async () => {
    await setupWebsiteBuilder(`<i class="oi" data-icon="search"/>`);
    await dblclick(":iframe .oi");
    await waitFor(MS_ICON_SELECTOR);
    expect(MS_ICON_SELECTOR).toHaveStyle({ fontFamily: /Material Symbols Outlined/ });
    expect(OI_ICON_SELECTOR).toHaveStyle({ fontFamily: /odoo_ui_icons/ });
});
