import { registry } from "@web/core/registry";

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
        // Description screen
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
            content: "choose from the positioning list",
            trigger: "button.o_change_website_purpose",
            run: "click",
        },
        // Palette screen
        {
            content: "chose a palette card",
            trigger: ".palette_card",
            run: "click",
        },
        {
            content: "Go to the next configurator step",
            trigger: "button.o_configurator_next:not(:disabled)",
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
        ...["Home", "Events", "Courses", "Blog"].map((menu) => ({
            content: `Check menu ${menu} is there`,
            trigger: `:iframe .top_menu a:contains(${menu}):not(:visible)`,
        })),
        ...["/", "/event", "/slides", "/blog"].map((url) => ({
            content: `Check url ${url} is there`,
            trigger: `:iframe .top_menu a[href^='${url}']:not(:visible)`,
        })),
        {
            trigger: ":iframe h1:contains(your journey starts here)",
        },
    ],
});
