import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

function fillSelectMenu(fieldName, search) {
    return [
        {
            content: `Select field name ${fieldName}`,
            trigger: `.o_field_widget[name=${fieldName}] input`,
            run: `edit ${search}`,
        },
        {
            trigger: `ul.ui-autocomplete > li > a:contains("${search}")`,
            run: "click",
        },
    ];
}

function ClickOnMenus() {
    return [
        {
            content: "Click on the reporting menu",
            trigger: "button[data-menu-xmlid='website.menu_reporting']",
            run: "click",
        },
        {
            content: "Click on the Tracked links menu",
            trigger: "a[data-menu-xmlid='website_links.menu_tracked_links_view_menu']",
            run: "click",
        },
        {
            content: "Click on cell to open chart",
            trigger: "tr td.o_data_cell.o_field_cell",
            run: "click",
            expectUnloadPage: true,
        },
    ];
}

const campaignValue = 'Super Specific Campaign';
const mediumValue = 'Super Specific Medium';
const sourceValue = 'Super Specific Source';

registerWebsitePreviewTour("website_links_tour", {
        url: "/",
    },
    () => [
        // 1. Create a tracked URL
        {
            content: "Wait for page",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
        },
        {
            content: "Click on the site menu",
            trigger: "button[data-menu-xmlid='website.menu_site']",
            run: "click",
        },
        {
            content: "Click on the link_tracker menu",
            trigger: "a[data-menu-xmlid='website_links.menu_link_tracker']",
            run: "click",
        },
        {
            content: "Add page URL",
            trigger: "div.o_field_widget[name='url'] .o_input",
            run: function () {
                const url = window.location.host + "/contactus";
                document.querySelector("div.o_field_widget[name='url'] .o_input").value = url;
            },
        },
        // First try to create a new UTM campaign from the UI
        ...fillSelectMenu("campaign_id", "Some new campaign"),
        // Then proceed by using existing ones
        ...fillSelectMenu("campaign_id", campaignValue),
        ...fillSelectMenu("medium_id", mediumValue),
        ...fillSelectMenu("source_id", sourceValue),
        {
            content: "Click on the 'Create & Copy' button",
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            content: "Wait until the modal is closed",
            trigger: "body:not(.modal-open)",
        },
        ...ClickOnMenus(),
        // 2. Visit it
        {
            content: "Check that link was created and visit it",
            trigger: ".o_website_links_chart .o_website_links_short_url:contains('/r/')",
            run() {
                const url = document.querySelector(
                    "div.o_website_links_chart .o_website_links_short_url"
                ).textContent;
                window.location.href = url;
            },
            expectUnloadPage: true,
        },
        {
            content: "Check that we landed on correct page with correct query strings",
            trigger: ".s_form_aside h1:text(Contact us)",
            run: function () {
                const enc = (c) => encodeURIComponent(c).replace(/%20/g, "+");
                const expectedUrl = `/contactus?utm_campaign=${enc(campaignValue)}&utm_source=${enc(
                    sourceValue
                )}&utm_medium=${enc(mediumValue)}`;
                if (window.location.pathname + window.location.search !== expectedUrl) {
                    console.error("The link was not correctly created. " + window.location.search);
                }
                window.location.href = "/odoo/website";
            },
            expectUnloadPage: true,
        },
        // 3. Check that counter got incremented and charts are correctly displayed
        ...ClickOnMenus(),
        {
            trigger: '.website_links_click_chart .title:contains("1 clicks")',
        },
        {
            content: "check click number and ensure graphs are initialized",
            trigger: 'canvas',
        },
        {
            content: "click on Last Month tab",
            trigger: '.o_website_links_chart .graph-tabs a:contains("Last Month")',
            run: "click",
        },
        {
            content: "ensure tab is correctly resized",
            trigger: '#last_month_charts #last_month_clicks_chart',
            run: function () {
                var width = document
                    .querySelector("#last_month_charts #last_month_clicks_chart")
                    .getBoundingClientRect().width;
                if (width < 50) {
                    console.error("The graphs are probably not resized on tab change.");
                }
            },
        },
    ]
);
