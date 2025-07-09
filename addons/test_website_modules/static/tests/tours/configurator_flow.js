import { delay } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("configurator_flow", {
    url: "/odoo/action-website.action_website_configuration",
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
            content: "click next",
            trigger: "button.o_configurator_show",
            run: "click",
            timeout: 20000,  /* previous step create a new website, this could take a long time */
        },
        // Description screen
        {
            content: "select a website type",
            trigger: "a.o_change_website_type",
            run: "click",
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
            content: "select an objective",
            trigger: ".o_configurator_purpose_dd a",
            run: "click",
        },
        {
            content: "choose from the objective list",
            trigger: "a.o_change_website_purpose",
            run: "click",
        },
        // Palette screen
        {
            content: "chose a palette card",
            trigger: ".palette_card",
            run: "click",
        },
        // Features screen
        {
            content: "select Pricing",
            trigger: '.card:contains("Pricing")',
            run: "click",
        },
        {
            trigger: '.card.border-success:contains("Pricing")',
        },
        {
            content: "Events should be selected (module already installed)",
            trigger: '.card.card_installed:contains("Events")',
        },
        {
            content: "Slides should be selected (module already installed)",
            trigger: '.card.card_installed:contains("eLearning")',
        },
        {
            trigger: '.card.card_installed:contains("Success Stories")',
        },
        {
            content:
                "Success Stories (Blog) and News (Blog) should be selected (module already installed)",
            trigger: '.card.card_installed:contains("News")',
        },
        {
            content: "Click on build my website",
            trigger: "button.btn-primary",
            run: "click",
        },
        // Online catalog screen
        {
            content: "Choose a shop page style",
            trigger: ".o_configurator_screen:contains(online catalog) .theme_preview",
            run: "click",
        },
        // Product page Screen
        {
            content: "Choose a product page style",
            trigger: ".o_configurator_screen:contains(product page) .theme_preview",
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
        ...["Home", "Events", "Courses", "Pricing", "News", "Success Stories", "Contact us"].map(
            (menu) => ({
                content: `Check menu ${menu} is there`,
                trigger: `:iframe .top_menu a:contains(${menu}):not(:visible)`,
            })
        ),
        ...["/", "/event", "/slides", "/pricing", "/blog/", "/blog/", "/contactus"].map((url) => ({
            content: `Check url ${url} is there`,
            trigger: `:iframe .top_menu a[href^='${url}']:not(:visible)`,
        })),
        {
            trigger: ":iframe h1:contains(your journey starts here)",
            async run() {
                //Wait assets are loaded
                await delay(1000);
            },
        },
    ],
});
