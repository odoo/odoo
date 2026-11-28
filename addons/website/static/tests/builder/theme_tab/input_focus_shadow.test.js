import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Bottom shadow checkbox sets/clears the input-focus-shadow variable", async () => {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step(`${location} ${JSON.stringify(changes)}`);
            const root = document.querySelector("iframe").contentDocument.documentElement;
            for (const [k, v] of Object.entries(changes)) {
                root.style.setProperty(`--${k}`, v ?? "");
            }
        }
    }
    defineModels([WebsiteAssets]);
    onRpc("/website/theme_customize_bundle_reload", async () => {
        expect.step("asset reload");
        return "";
    });
    await setupWebsiteBuilder("");

    await contains("#theme-tab").click();
    await contains("[data-action-param='input-focus-shadow'] input").click();
    await expect.waitForSteps([
        '/website/static/src/scss/options/user_values.scss {"input-focus-shadow":"bottom"}',
        "asset reload",
    ]);

    await contains("[data-action-param='input-focus-shadow'] input").click();
    await expect.waitForSteps([
        '/website/static/src/scss/options/user_values.scss {"input-focus-shadow":"null"}',
        "asset reload",
    ]);
});
