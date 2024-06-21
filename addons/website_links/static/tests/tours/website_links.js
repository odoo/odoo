/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

function fillSelect2(inputID, search) {
    return [
        {
            content: "Click select2 form item",
            trigger: `.o_website_links_utm_forms div.select2-container#s2id_${inputID} > .select2-choice`,
            run: "click",
        },
        {
            content: "Enter select2 search query",
            trigger: '.select2-drop .select2-input',
            run: `edit ${search}`,
        },
        {
            content: "Select found select2 item",
            trigger: `.select2-drop li:only-child .select2-match:contains("/^${search}$/")`,
            run: "click",
        },
        {
            content: "Check that select2 is properly filled",
            trigger: `.o_website_links_utm_forms div.select2-container#s2id_${inputID} .select2-chosen:contains("/^${search}$/")`,
            run: () => null,
        },
    ];
}

const campaignValue = 'Super Specific Campaign';
const mediumValue = 'Super Specific Medium';
const sourceValue = 'Super Specific Source';

registry.category("web_tour.tours").add('website_links_tour', {
    test: true,
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
        ...fillSelect2('campaign-select', campaignValue),
        ...fillSelect2('channel-select', mediumValue),
        ...fillSelect2('source-select', sourceValue),
        {
            content: "Copy tracker link",
            trigger: '#btn_shorten_url',
            run: function () {
                // Patch and ignore write on clipboard in tour as we don't have permissions
                const oldWriteText = browser.navigator.clipboard.writeText;
                browser.navigator.clipboard.writeText = () => {
                    console.info("Copy in clipboard ignored!");
                };
                document.querySelector("#btn_shorten_url").click();
                browser.navigator.clipboard.writeText = oldWriteText;
            },
        },
        // 2. Visit it
        {
            trigger: '#o_website_links_recent_links .truncate_text:first():contains("Contact Us")',
        },
        {
            content: "check that link was created and visit it",
            trigger: '#o_website_links_link_tracker_form #generated_tracked_link:contains("/r/")',
            run: function () {
                window.location.href = $('#generated_tracked_link').text();
            },
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
        },
        // 3. Check that counter got incremented and charts are correctly displayed
        {
            content: "filter recently used links",
            trigger: '#filter-recently-used-links',
            run: "click",
        },
        {
            content: "visit link stats page",
            trigger: "#o_website_links_recent_links a:contains(/^Stats$/):first",
            run: "click",
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
