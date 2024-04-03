/* global ace */
odoo.define('test_website.reset_views', function (require) {
'use strict';

const wTourUtils = require('website.tour_utils');

var BROKEN_STEP = {
    // because saving a broken template opens a recovery page with no assets
    // there's no way for the tour to resume on the new page, and thus no way
    // to properly wait for the page to be saved & reloaded in order to fix the
    // race condition of a tour ending on a side-effect (with the possible
    // exception of somehow telling the harness / browser to do it)
    trigger: 'body',
    run: function () {}
};
wTourUtils.registerWebsitePreviewTour('test_reset_page_view_complete_flow_part1', {
    test: true,
    url: '/test_page_view',
    // 1. Edit the page through Edit Mode, it will COW the view
    edition: true,
},
    [
        {
            content: "drop a snippet",
            trigger: ".oe_snippet:has(.s_cover) .oe_snippet_thumbnail",
            // id starting by 'oe_structure..' will actually create an inherited view
            run: "drag_and_drop iframe #oe_structure_test_website_page",
        },
        {
            content: "save the page",
            extra_trigger: 'iframe #oe_structure_test_website_page.o_dirty',
            trigger: "button[data-action=save]",
        },
        // 2. Edit that COW'd view in the HTML editor to break it.
        {
            content: "open site menu",
            extra_trigger: "iframe body:not(.editor_enable)",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
        },
        {
            content: "open html editor",
            trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
        },
        {
            content: "add a broken t-field in page DOM",
            trigger: 'div.ace_line .ace_xml:contains("placeholder")',
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 4, column: 1}, '<t t-field="not.exist"/>\n');
            },
        },
        {
            content: "save the html editor",
            extra_trigger: '.ace_content:contains("not.exist")',
            trigger: ".o_ace_view_editor button[data-action=save]",
        },
        BROKEN_STEP
    ]
);

wTourUtils.registerWebsitePreviewTour('test_reset_page_view_complete_flow_part2', {
    test: true,
    url: '/test_page_view',
},
    [
        {
            content: "check that the view got fixed",
            trigger: 'iframe p:containsExact("Test Page View")',
            run: function () {}, // it's a check
        },
        {
            content: "check that the inherited COW view is still there (created during edit mode)",
            trigger: 'iframe #oe_structure_test_website_page .s_cover',
            run: function () {}, // it's a check
        },
        //4. Now break the inherited view created when dropping a snippet
        {
            content: "open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
        },
        {
            content: "open html editor",
            trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
        },
        {
            content: "select oe_structure view",
            trigger: '#s2id_ace-view-list',  // use select2 version
            run: function () {
                var viewId = $('#ace-view-list option:contains("oe_structure_test_website_page")').val();
                $('#ace-view-list').val(viewId).trigger('change');
            },
        },
        {
            content: "add a broken t-field in page DOM",
            trigger: 'div.ace_line .ace_xml:contains("oe_structure_test_website_page")',
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 4, column: 1}, '<t t-field="not.exist"/>\n');
            },
        },
        {
            content: "save the html editor",
            trigger: ".o_ace_view_editor button[data-action=save]",
        },
        BROKEN_STEP
    ]
);

});
