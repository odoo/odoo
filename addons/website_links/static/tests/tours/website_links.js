/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

function fillSelectMenu(inputID, search) {
    return [
        {
            content: "Click selectMenu form item",
            trigger: `.o_website_links_utm_forms div#${inputID} .o_select_menu_toggler`,
            run: "click",
        },
        {
            content: "Enter selectMenu search query",
            trigger: ".o_popover input.o_select_menu_sticky",
            run: `edit ${search}`,
        },
        {
            content: "Select found selectMenu item",
            trigger: `.o_popover span.o_select_menu_item div.o_select_menu_item_label:contains("/^${search}$/")`,
            run: "click",
        },
        {
            content: "Check that selectMenu is properly filled",
            trigger: `#${inputID} .o_select_menu_toggler span.o_select_menu_toggler_slot:contains('/^${search}$/')`,
            run: () => null,
        },
    ];
}

const campaignValue = 'Super Specific Campaign';
const mediumValue = 'Super Specific Medium';
const sourceValue = 'Super Specific Source';

registry.category("web_tour.tours").add('website_links_tour', {
    url: '/r',
    steps: () => [
        // 1. Create a tracked URL
        {
            content: "check that existing links are shown",
            trigger: '#o_website_links_recent_links .btn_shorten_url_clipboard',
        },
        {
            content: "fill the URL form input",
            trigger: '#o_website_links_link_tracker_form input#url',
            run: function () {
                var url = window.location.host + '/contactus';
                document.querySelector("#o_website_links_link_tracker_form input#url").value = url;
            },
        },
        // First try to create a new UTM campaign from the UI
        {
            content: "Click select menu form item",
            trigger: ".o_website_links_utm_forms div#campaign-select-wrapper .o_select_menu_toggler",
            run: "click",
        },
        {
            content: "Enter select menu search query",
            trigger: '.o_popover input.o_select_menu_sticky',
            run: "edit Some new campaign",
        },
        {
            content: "Select found select menu item",
            trigger: ".o_popover.o_select_menu_menu .o_select_menu_item span:contains('Some new campaign')",
            run: 'click',
        },
        {
            content: "Check that select menu is properly filled",
            trigger: "#campaign-select-wrapper .o_select_menu_toggler span.o_select_menu_toggler_slot:contains('Some new campaign')"
        },
        // Then proceed by using existing ones
        ...fillSelectMenu("campaign-select-wrapper", campaignValue),
        ...fillSelectMenu("channel-select-wrapper", mediumValue),
        ...fillSelectMenu("source-select-wrapper", sourceValue),
        {
            content: "Copy tracker link",
            trigger: '#btn_shorten_url',
            run: function () {
                // Patch and ignore write on clipboard in tour as we don't have permissions
                const oldWriteText = browser.navigator.clipboard.writeText;
                browser.navigator.clipboard.writeText = () => {
                    console.info("Copy in clipboard ignored!");
                };
                browser.navigator.clipboard.writeText = oldWriteText;
            },
        },
        {
            content: "Generate Link Tracker",
            trigger: "#btn_shorten_url",
            run: "click",
        },
        // 2. Visit it
        {
            trigger: '#o_website_links_recent_links .o_website_links_title:first():contains("Contact Us")',
        },
        {
            content: "check that link was created and visit it",
            trigger: '.o_website_links_create_tracked_url #generated_tracked_link .o_website_links_short_url:contains("/r/")',
            run: function () {
                window.location.href = $('#generated_tracked_link .o_website_links_short_url').text();
            },
            expectUnloadPage: true,
        },
        {
            content: "check that we landed on correct page with correct query strings",
            trigger: ".s_title h1:contains(/^Contact us$/)",
            run: function () {
                const enc = c => encodeURIComponent(c).replace(/%20/g, '+');
                const expectedUrl = `/contactus?utm_campaign=${enc(campaignValue)}&utm_source=${enc(sourceValue)}&utm_medium=${enc(mediumValue)}`;
                if (window.location.pathname + window.location.search !== expectedUrl) {
                    console.error("The link was not correctly created. " + window.location.search);
                }
                window.location.href = '/r';
            },
            expectUnloadPage: true,
        },
        // 3. Check that counter got incremented and charts are correctly displayed
        {
            content: "Sort the recent links",
            trigger: ".o_website_links_sort_by",
            run: "click",
        },
        {
            content: "Sort by last clicked links",
            trigger: "#recent_links_sort_by a[data-filter='recently-used']",
            run: "click",
        },
        {
            content: "visit link stats page",
            trigger: ".o_website_links_card",
            run: "click",
            expectUnloadPage: true,
        },
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
});
