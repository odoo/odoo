odoo.define('website.test.html_editor', function (require) {
'use strict';

var tour = require('web_tour.tour');
var base = require('web_editor.base');

tour.register('html_editor_multiple_templates', {
    test: true,
    url: '/aboutus',
    wait_for: base.ready(),
},
    [
        // 1. Edit the page through Edit Mode, it will COW the view
        {
            content: "enter edit mode",
            trigger: 'a[data-action=edit]',
        },
        {
            content: "drop a snippet",
            trigger: '#oe_snippets .oe_snippet:has(.s_cover) .oe_snippet_thumbnail',
            // id starting by 'oe_structure..' will actually create an inherited view
            run: "drag_and_drop #oe_structure_test_ui",
        },
        {
            content: "save the page",
            extra_trigger: '#wrapwrap .s_cover',
            trigger: "#web_editor-top-edit button[data-action=save]",
        },
        // 2. Edit generic aboutus view
        {
            content: "open customize menu",
            extra_trigger: "body:not(.editor_enable)",
            trigger: '#customize-menu > a',
        },
        {
            content: "open html editor",
            trigger: '#html_editor',
        },
        {
            content: "add something in the aboutus view",
            trigger: 'div.ace_line .ace_xml:contains("aboutus")',
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 3, column: 1}, '<p>somenewcontent</p>\n');
            },
        },
        // 3. Edit oe_structure specific view
        {
            content: "select oe_structure specific view",
            trigger: 'div.ace_line .ace_xml:contains("somenewcontent")',
            run: function () {
                var viewId = $('#ace-view-list option:contains("oe_structure")').val();
                $('#ace-view-list').val(viewId).trigger('change');
            },
        },
        {
            content: "add something in the oe_structure specific view",
            trigger: 'div.ace_line .ace_xml:contains("s_cover")',
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 2, column: 1}, '<p>anothernewcontent</p>\n');
            },
        },
        {
            content: "save the html editor",
            extra_trigger: 'div.ace_line .ace_xml:contains("anothernewcontent")',
            trigger: ".o_ace_view_editor button[data-action=save]",
        },
        {
           content: "check that the page has both modification",
           extra_trigger: '#wrapwrap:contains("anothernewcontent")',
           trigger: '#wrapwrap:contains("somenewcontent")',
           run: function () {}, // it's a check
       },
    ]
);
});
