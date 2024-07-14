/** @odoo-module */

import { registry } from "@web/core/registry";
import { assertEqual } from "@web_studio/../tests/tours/tour_helpers";

registry.category("web_tour.tours").add("website_studio_listing_and_page", {
    url: "/web?debug=1#action=studio&mode=home_menu",
    test: true,
    steps: () => [
        {
            trigger: "a.o_menuitem:contains('StudioApp')",
        },
        {
            trigger: ".o_menu_sections a:contains('Website')",
        },
        {
            trigger: ".o_website_studio_listing",
        },
        {
            content: "Create a listing page",
            trigger: ".o_website_studio_listing .o-website-studio-item-card",
        },
        {
            content: "Set the name of the page",
            trigger: "div[name='page_name'] input",
            run: "text_blur MyCustom Name"
        },
        {
            trigger: "div[name='name_slugified']",
            run: () => {
                assertEqual(document.querySelector( "div[name='name_slugified']").textContent, "mycustom-name");
                // listing is displayed in the menu by default
                assertEqual(document.querySelector("div[name='use_menu'] input").checked, true);
                // creating a listing automatically creates a detailed page for each record to be consulted separately
                assertEqual(document.querySelector("div[name='auto_single_page'] input").checked, true);
            }
        },
        {
            trigger: ".o_form_button_save",
        },
        {
            trigger: "body",
            run: () => {
                const listingCount = [...document.querySelectorAll(".o_website_studio_listing .o-website-studio-item-card:not(.o_website_studio_new_card)")].length;
                assertEqual(listingCount, 1);
                const pagesCount = [...document.querySelectorAll(".o_website_studio_single .o-website-studio-item-card:not(.o_website_studio_new_card)")].length;
                assertEqual(pagesCount, 1);
                // the listing has the right name
                assertEqual(document.querySelector(".o_website_studio_listing .o-website-studio-item-card:not(.o_website_studio_new_card)").textContent, "MyCustom Name");
                // the page has the right name
                assertEqual(document.querySelector(".o_website_studio_single .o-website-studio-item-card:not(.o_website_studio_new_card)").textContent, "MyCustom Name");
            }
        },
    ],
});

registry.category("web_tour.tours").add("website_studio_listing_without_page", {
    url: "/web?debug=1#action=studio&mode=home_menu",
    test: true,
    steps: () => [
        {
            trigger: "a.o_menuitem:contains('StudioApp')",
        },
        {
            trigger: ".o_menu_sections a:contains('Website')",
        },
        {
            trigger: ".o_website_studio_listing",
        },
        {
            content: "Create a listing page",
            trigger: ".o_website_studio_listing .fa-plus",
        },
        {
            content: "Set the name of the page",
            trigger: "div[name='page_name'] input",
            run: "text_blur MyCustom Name"
        },
        {
            trigger: "div[name='name_slugified']",
            run: () => {
                assertEqual(document.querySelector( "div[name='name_slugified']").textContent, "mycustom-name");
                // listing is displayed in the menu by default
                assertEqual(document.querySelector("div[name='use_menu'] input").checked, true);
                // creating a listing automatically creates a detailed page for each record to be consulted separately
                assertEqual(document.querySelector("div[name='auto_single_page'] input").checked, true);
            }
        },
        {
            content: "Uncheck the toggle and only create the listing",
            trigger: "div[name='auto_single_page'] input"
        },
        {
            trigger: ".o_form_button_save",
        },
        {
            trigger: "body",
            run: () => {
                const listingCount = [...document.querySelectorAll(".o_website_studio_listing .o-website-studio-item-card:not(.o_website_studio_new_card)")].length;
                assertEqual(listingCount, 1);
                const pagesCount = [...document.querySelectorAll(".o_website_studio_single .o-website-studio-item-card:not(.o_website_studio_new_card)")].length;
                assertEqual(pagesCount, 0);
                // the listing has the right name
                assertEqual(document.querySelector(".o_website_studio_listing .o-website-studio-item-card:not(.o_website_studio_new_card)").textContent, "MyCustom Name");
            }
        },
    ],
});
