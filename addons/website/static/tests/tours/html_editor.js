odoo.define('website.test.html_editor', function (require) {
'use strict';

var tour = require('web_tour.tour');

tour.register('html_editor_multiple_templates', {
    test: true,
    url: '/aboutus',
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
            extra_trigger: '#oe_structure_test_ui.o_dirty',
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
            extra_trigger: '#ace-view-id:contains("website.aboutus_oe_structure_test_ui")', // If no xml_id it should show key
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

tour.register('test_html_editor_scss', {
    test: true,
    url: '/aboutus',
},
    [
        // 1. Open Html Editor and select a scss file
        {
            content: "open customize menu",
            extra_trigger: '#wrap:visible', // ensure state for later
            trigger: '#customize-menu > a',
        },
        {
            content: "open html editor",
            trigger: '#html_editor',
        },
        {
            content: "open type switcher",
            trigger: '.o_ace_type_switcher button',
        },
        {
            content: "select scss files",
            trigger: '.o_ace_type_switcher_choice[data-type="scss"]',
        },
        {
            content: "select 'user_custom_rules'",
            trigger: 'body:has(#ace-scss-list option:contains("user_custom_rules"))',
            run: function () {
                var scssId = $('#ace-scss-list option:contains("user_custom_rules")').val();
                $('#ace-scss-list').val(scssId).trigger('change');
            },
        },
        // 2. Edit that file and ensure it was saved then reset it
        {
            content: "add some scss content in the file",
            trigger: 'div.ace_line .ace_comment:contains("footer {")',
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 2, column: 0}, '#wrap {display: none;}\n');
            },
        },
        {
            content: "save the html editor",
            extra_trigger: 'div.ace_line:contains("#wrap {display: none;}")',
            trigger: ".o_ace_view_editor button[data-action=save]",
        },
         {
            content: "check that the scss modification got applied",
            trigger: 'body:has(#wrap:hidden)',
            run: function () {}, // it's a check
        },
        {
            content: "reset view (after reload, html editor should have been reopened where it was)",
            trigger: '#ace-view-id button[data-action="reset"]',
        },
        {
            content: "confirm reset warning",
            trigger: '.modal-footer .btn-primary',
        },
        {
            content: "check that the scss file was reset correctly, wrap content should now be visible again",
            trigger: '#wrap:visible',
            run: function () {}, // it's a check
        },
    ]
);

});
