import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

const PALETTE_COLOR_KEY = "configurator_flow_palette_color";

function getBgColor(element) {
    return element.ownerDocument.defaultView.getComputedStyle(element).backgroundColor;
}

function assertBgColor(element, expectedColor) {
    const currentColor = getBgColor(element);
    if (currentColor !== expectedColor) {
        throw new Error(
            `Expected the header CTA background to be ${expectedColor}, got ${currentColor}`
        );
    }
}

registry.category("web_tour.tours").add("configurator_flow", {
    steps: () => [
        {
            content: "click on create new website",
            trigger: 'button[name="action_website_create_new"]',
            run: "click",
        },
        {
            content: "insert website name",
            trigger: '[name="name"] input',
            run: "edit Website Test",
        },
        {
            content: "validate the website creation modal",
            trigger: 'button.btn-primary:contains("Create")',
            run: "click",
            expectUnloadPage: true,
        },
        // Configurator first screen
        {
            content: "select a website type",
            trigger: "button.o_change_website_type",
            run: "click",
            timeout: 20000 /* previous step create a new website, this could take a long time */,
        },
        {
            content: "insert a website industry",
            trigger: ".o_configurator_industry input",
            run: "edit ab",
        },
        {
            content: "select a website industry from the autocomplete",
            trigger: ".o_configurator_industry ul li a",
            run: "click",
        },
        {
            content: "choose from the objective list",
            trigger: "button.o_change_website_purpose",
            run: "click",
        },
        // Set up style screen
        {
            content: "loader should be shown",
            trigger: ".o_configurator_preview_loader",
        },
        {
            content: "loader should be hidden",
            trigger: ".o_configurator_screen_content:not(:has(.o_configurator_preview_loader))",
            timeout: 20000 /* previous step install the theme, this could take a long time */,
        },
        {
            content: 'the preview should be fully loaded',
            trigger:
                ":iframe body.o_website_theme_configurator_preview #wrapwrap" +
                ":has([data-name='Header'])" +
                ":has(main #wrap > section:nth-of-type(3))" +
                ":has(footer#bottom)",
        },
        {
            content: "the header CTA should match the selected palette",
            // The runbot screen is not wide enough to display the page in
            // desktop mode, so we added "":not(:visible)"".
            trigger: ":iframe header .btn_cta:not(:visible)",
            run: function () {
                const expectedColor = getComputedStyle(
                    document.querySelector(".o_setup_style_screen_color_palette.active span")
                ).backgroundColor;
                assertBgColor(this.anchor, expectedColor);
            },
        },
        {
            content: "open the color panel",
            trigger: 'a[data-bs-target="#colorPanel"]',
            run: "click",
        },
        {
            content: "select the second palette",
            trigger: "#colorPanel.show .offcanvas-body .o_setup_style_screen_color_palette:eq(1) span:first-child",
            async run({ click }) {
                browser.localStorage.setItem(
                    PALETTE_COLOR_KEY,
                    getComputedStyle(this.anchor).backgroundColor
                );
                await click();
            },
        },
        {
            content: "the header CTA should match the new palette",
            // The runbot screen is not wide enough to display the page in
            // desktop mode, so we added "":not(:visible)"".
            trigger: ":iframe header .btn_cta:not(:visible)",
            async run({ anchor, waitUntil }) {
                const selectedPaletteColor = browser.localStorage.getItem(PALETTE_COLOR_KEY);
                try {
                    await waitUntil(() => getBgColor(anchor) === selectedPaletteColor, {
                        timeout: 9000,
                    });
                } catch {
                    assertBgColor(anchor, selectedPaletteColor);
                }
            },
        },
        {
            content: "close the color panel",
            trigger: 'button[data-bs-dismiss="offcanvas"]',
            run: "click",
        },
        {
            content: "click the 'Start Building' button",
            trigger: ".o_setup_style_screen_footer button.btn.btn-primary",
            run: "click",
        },
        // Online catalog screen
        {
            content: "Choose a shop page style",
            trigger: ".o_configurator_screen:contains(online catalog) .button_area",
            run: "click",
        },
        // Product page Screen
        {
            content: "Choose a product page style",
            trigger: ".o_configurator_screen:contains(product page) .button_area",
            run: "click",
        },
        {
            content: "Loader should be shown",
            trigger: ".o_website_loader_container",
            expectUnloadPage: true,
        },
        {
            content: "Wait until the configurator is finished",
            trigger: ":iframe [data-view-xmlid='website.homepage']",
            timeout: 30000,
        },
        {
            content: "check menu and footer links are correct",
            trigger: "body:not(.editor_enable)", // edit mode left
        },
        ...["Contact us", "Privacy Policy"].map((menu) => ({
            content: `Check footer menu ${menu} is there`,
            trigger: `:iframe footer a:contains(${menu})`,
        })),
        ...["Home", "Events", "Courses"].map((menu) => ({
            content: `Check menu ${menu} is there`,
            trigger: `:iframe .top_menu a:contains(${menu}):not(:visible)`,
        })),
        ...["/", "/event", "/slides"].map((url) => ({
            content: `Check url ${url} is there`,
            trigger: `:iframe .top_menu a[href^='${url}']:not(:visible)`,
        })),
        {
            trigger: ":iframe #wrap > section.s_cover",
        },
        {
            content: "the final header CTA should keep the selected palette",
            trigger: ":iframe header .btn_cta:not(:visible)",
            run() {
                assertBgColor(this.anchor, browser.localStorage.getItem(PALETTE_COLOR_KEY));
                browser.localStorage.removeItem(PALETTE_COLOR_KEY);
            },
        },
    ],
});
