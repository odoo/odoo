/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

function fillSelect2(inputID, search) {
    return [
        {
            content: "Click select2 form item",
            trigger: `.o_website_links_utm_forms div:has(+ #${inputID}) > .select2-choice`,
        },
        {
            content: "Enter select2 search query",
            trigger: '.select2-drop .select2-input',
            run: `text ${search}`,
        },
        {
            content: "Select found select2 item",
            trigger: `.select2-drop li:only-child .select2-match:containsExact("${search}")`,
        },
        {
            content: "Check that select2 is properly filled",
            trigger: `.o_website_links_utm_forms div:has(+ #${inputID}) .select2-chosen:containsExact("${search}")`,
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
            run: function () {}, // it's a check
        },
        {
            content: "fill the URL form input",
            trigger: '#o_website_links_link_tracker_form input#url',
            run: function () {
                var url = window.location.host + '/contactus';
                $('#o_website_links_link_tracker_form input#url').val(url);
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
                browser.navigator.clipboard.writeText = () => { console.info('Copy in clipboard ignored!') };
                $('#btn_shorten_url').click();
                browser.navigator.clipboard.writeText = oldWriteText;
            },
        },
        // 2. Visit it
        {
            content: "check that link was created and visit it",
            extra_trigger: '#o_website_links_recent_links .truncate_text:first():contains("Contact Us")',
            trigger: '#o_website_links_link_tracker_form #generated_tracked_link:contains("/r/")',
            run: function () {
                window.location.href = $('#generated_tracked_link').text();
            },
        },
        {
            content: "check that we landed on correct page with correct query strings",
            trigger: '.s_title h1:containsExact("Contact us")',
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
        },
        {
            content: "visit link stats page",
            trigger: '#o_website_links_recent_links a:containsExact("Stats"):first',
        },
        {
            content: "check click number and ensure graphs are initialized",
            extra_trigger: '.website_links_click_chart .title:contains("1 clicks")',
            trigger: 'canvas',
            run: function () {}, // it's a check
        },
        {
            content: "click on Last Month tab",
            trigger: '.o_website_links_chart .graph-tabs a:contains("Last Month")',
        },
        {
            content: "ensure tab is correctly resized",
            trigger: '#last_month_charts #last_month_clicks_chart',
            run: function () {
                var width = $('#last_month_charts #last_month_clicks_chart').width();
                if (width < 50) {
                    console.error("The graphs are probably not resized on tab change.");
                }
            },
        },
    ]
});
