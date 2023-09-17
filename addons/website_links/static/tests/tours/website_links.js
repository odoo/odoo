/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

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
            content: "fill the form and submit it",
            trigger: '#o_website_links_link_tracker_form input#url',
            run: function () {
                var url = window.location.host + '/contactus';
                $('#o_website_links_link_tracker_form input#url').val(url);
                $('.o_website_links_utm_forms input#campaign-select').val(1).change();
                $('.o_website_links_utm_forms input#channel-select').val(1).change();
                $('.o_website_links_utm_forms input#source-select').val(1).change();
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
                var expectedUrl = "/contactus?utm_campaign=Sale&utm_source=Search+engine&utm_medium=Website";
                if (window.location.pathname + window.location.search !== expectedUrl) {
                    console.error("The link was not correctly created.");
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
