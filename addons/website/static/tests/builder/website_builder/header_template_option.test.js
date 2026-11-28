import { describe, expect, test } from "@odoo/hoot";
import { queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import { isHeaderBgBlurAvailable } from "@website/builder/plugins/options/header/header_template_option";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const headerContent = `
    <header id="top" data-anchor="true" data-name="Header">
        <nav class="navbar">
            <div id="o_main_nav" class="container o_main_nav"> content </div>
        </nav>
    </header>`;

describe("header blur option", () => {
    test("header blur option is only available when the background is not fully opaque", async () => {
        await setupWebsiteBuilder("", { openEditor: false, headerContent });
        const headerEl = queryOne(":iframe #wrapwrap > header");
        const navEl = headerEl.querySelector("nav");
        // The blur is applied on the nav, so only its background is relevant.
        const expectBlur = (navStyle) => {
            navEl.setAttribute("style", navStyle);
            return expect(isHeaderBgBlurAvailable(headerEl));
        };

        expectBlur("").toBe(true);

        expectBlur("--menu-custom: rgb(255, 0, 0)").toBe(false);
        expectBlur("--menu-custom: #ff0000").toBe(false);
        expectBlur("--menu-custom: #ff0000ff").toBe(false);
        expectBlur("--menu-custom: rgba(255, 0, 0, 0.5)").toBe(true);
        expectBlur("--menu-custom: #ff000080").toBe(true);

        expectBlur("--menu: 3; --o-cc3-bg: rgb(255, 0, 0)").toBe(false);
        expectBlur("--menu: 3; --o-cc3-bg: rgba(255, 0, 0, 0.5)").toBe(true);

        expectBlur("--menu-custom: rgba(255, 0, 0, 0.5); --menu-gradient: none").toBe(true);
        expectBlur("--menu-gradient: linear-gradient(rgba(255,0,0,0.5), blue)").toBe(true);
        expectBlur("--menu-gradient: linear-gradient(rgba(0,0,0,0.5), rgba(255,255,255,1))").toBe(
            true
        );
        expectBlur("--menu-gradient: linear-gradient(#ff000080, #0000ffff)").toBe(true);
        expectBlur("--menu-gradient: linear-gradient(#ff0000, #0000ff)").toBe(false);
        expectBlur("--menu: 3; --o-cc3-bg-gradient: linear-gradient(#ff000080, #0000ffff)").toBe(
            true
        );

        expectBlur(
            "--menu-custom: #ff000080; --menu-gradient: linear-gradient(#ff0000, #0000ff)"
        ).toBe(false);
    });

    test("the blur option is hidden for an opaque header background", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder("", {
            openEditor: true,
            headerContent,
            styleContent: `#wrapwrap > header nav { --menu-custom: rgb(255, 0, 0); }`,
        });
        await contains(":iframe #wrapwrap > header").click();
        await waitSidebarUpdated();
        expect("[data-label='Blur']").not.toHaveCount();
    });

    test("the blur option is shown for a transparent header background", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder("", {
            openEditor: true,
            headerContent,
            styleContent: `#wrapwrap > header nav { --menu-custom: rgba(255, 0, 0, 0.5); }`,
        });
        await contains(":iframe #wrapwrap > header").click();
        await waitSidebarUpdated();
        expect("[data-label='Blur']").toBeVisible();
    });

    test("the header blur is disabled on an opaque background and restored on undo", async () => {
        let htmlStyle;
        class WebsiteAssets extends models.Model {
            _name = "website.assets";
            make_scss_customization(location, changes) {
                expect.step(`${location.split("/").at(-1)} ${JSON.stringify(changes)}`);
                // Simulate the assets reload.
                for (const [key, value] of Object.entries(changes)) {
                    if (["NULL", "null"].includes(value)) {
                        htmlStyle.removeProperty(`--${key}`);
                    } else {
                        htmlStyle.setProperty(`--${key}`, value);
                    }
                }
            }
        }
        defineModels([WebsiteAssets]);
        onRpc("/website/theme_customize_bundle_reload", () => "");
        await setupWebsiteBuilder("", {
            headerContent,
            styleContent: `:root { --400: #CED4DA; }`,
        });
        // Retrieved now, as the custom color tab adds another iframe.
        htmlStyle = queryOne(":iframe html").style;
        htmlStyle.setProperty("--menu-custom", "rgba(255, 0, 0, 0.5)");
        htmlStyle.setProperty("--header-bg-blur", "5");
        await contains(":iframe #wrapwrap > header").click();
        await waitFor("[data-label='Blur']");

        await contains("[data-label='Background'] button.o_we_color_preview").click();
        await contains("button.custom-tab").click();
        await contains("button[data-color='400']").click();
        await expect.waitForSteps([
            'user_color_palette.scss {"menu-custom":"#CED4DA"}',
            'user_values.scss {"menu-gradient":"NULL"}',
            'user_values.scss {"header-bg-blur":"null"}',
        ]);
        await waitForNone("[data-label='Blur']");

        await contains(".o-snippets-menu button[data-icon='undo']").click();
        await expect.waitForSteps([
            'user_color_palette.scss {"menu-custom":"#FF000080"}',
            'user_values.scss {"menu-gradient":"NULL"}',
            'user_values.scss {"header-bg-blur":"5"}',
        ]);
        await waitFor("[data-label='Blur']");
    });
});

describe("header width option", () => {
    test("width preview is disabled on incompatible templates", async () => {
        onRpc("/website/theme_customize_data_get", async () => [
            "website.header_navbar_pills_style",
            "website.template_header_boxed",
        ]);
        await setupWebsiteBuilder("", { headerContent });
        await contains(":iframe #wrapwrap > header").click();
        await waitFor("[data-label='Content Width']");
        expect("[data-label='Content Width'] [data-action-id='websiteConfig']").toHaveCount(3);
        expect(
            "[data-label='Content Width'] [data-action-id='previewableWebsiteConfig']"
        ).toHaveCount(0);
    });

    test("width preview is enabled by default", async () => {
        await setupWebsiteBuilder("", { headerContent });
        await contains(":iframe #wrapwrap > header").click();
        await waitFor("[data-label='Content Width']");
        expect(
            "[data-label='Content Width'] [data-action-id='previewableWebsiteConfig']"
        ).toHaveCount(3);
        expect("[data-label='Content Width'] [data-action-id='websiteConfig']").toHaveCount(0);
    });
});
