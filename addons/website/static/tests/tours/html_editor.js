/* global ace */
odoo.define('website.test.html_editor', function (require) {
'use strict';

var tour = require('web_tour.tour');

const adminCssModif = '#wrap {display: none;}';
const demoCssModif = '// demo_edition';

tour.register('html_editor_multiple_templates', {
    test: true,
    url: '/generic',
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
            trigger: "button[data-action=save]",
        },
        // 2. Edit generic view
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
            content: "add something in the generic view",
            trigger: 'div.ace_line .ace_xml:contains("Generic")',
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 3, column: 1}, '<p>somenewcontent</p>\n');
            },
        },
        // 3. Edit oe_structure specific view
        {
            content: "select oe_structure specific view",
            trigger: 'div.ace_line .ace_xml:contains("somenewcontent")',
            run: function () {
                var viewId = $('#ace-view-list option:contains("oe_structure_test_ui")').val();
                $('#ace-view-list').val(viewId).trigger('change');
            },
        },
        {
            content: "add something in the oe_structure specific view",
            extra_trigger: '#ace-view-id:contains("test.generic_view_oe_structure_test_ui")', // If no xml_id it should show key
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
    url: '/contactus',
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
                ace.edit('ace-view-editor').getSession().insert({row: 2, column: 0}, `${adminCssModif}\n`);
            },
        },
        {
            content: "save the html editor",
            extra_trigger: `div.ace_line:contains("${adminCssModif}")`,
            trigger: ".o_ace_view_editor button[data-action=save]",
        },
         {
            content: "check that the scss modification got applied",
            trigger: 'body:has(#wrap:hidden)',
            run: function () {}, // it's a check
            timeout: 30000, // SCSS compilation might take some time
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
            timeout: 30000, // SCSS compilation might take some time
        },
        // 3. Customize again that file (will be used in second part of the test
        //    to ensure restricted user can still use the HTML Editor)
        {
            content: "add some scss content in the file",
            trigger: 'div.ace_line .ace_comment:contains("footer {")',
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 2, column: 0}, `${adminCssModif}\n`);
            },
        },
        {
            content: "save the html editor",
            extra_trigger: `div.ace_line:contains("${adminCssModif}")`,
            trigger: '.o_ace_view_editor button[data-action=save]',
        },
        {
            content: "check that the scss modification got applied",
            trigger: 'body:has(#wrap:hidden)',
            run: function () {
                window.location.href = '/web/session/logout?redirect=/web/login';
            },
            timeout: 30000, // SCSS compilation might take some time
        },

        // This part of the test ensures that a restricted user can still use
        // the HTML Editor if someone else made a customization previously.

        {
            content: "Submit login",
            trigger: '.oe_login_form',
            run: function () {
                $('.oe_login_form input[name="login"]').val("demo");
                $('.oe_login_form input[name="password"]').val("demo");
                $('.oe_login_form input[name="redirect"]').val("/");
                $('.oe_login_form').submit();
            },
        },
        // 4. Open Html Editor and select a scss file
        {
            content: "open customize menu",
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
        // 5. Edit that file and ensure it was saved then reset it
        {
            content: "add some scss content in the file",
            trigger: `div.ace_line:contains("${adminCssModif}")`, // ensure the admin modification is here
            run: function () {
                ace.edit('ace-view-editor').getSession().insert({row: 2, column: 0}, `${demoCssModif}\n`);
            },
        },
        {
            content: "save the html editor",
            extra_trigger: `div.ace_line:contains("${demoCssModif}")`,
            trigger: ".o_ace_view_editor button[data-action=save]",
        },
        {
            content: "wait for reload",
            trigger: "body:not(:has(div.o_ace_view_editor))",
            run: function () {}, // it's a check
            timeout: 30000, // SCSS compilation might take some time
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
            content: "check that the scss file was reset correctly",
            extra_trigger: `body:not(:has(div.ace_line:contains("${adminCssModif}")))`,
            trigger: `body:not(:has(div.ace_line:contains("${demoCssModif}")))`,
            run: function () {}, // it's a check
            timeout: 30000, // SCSS compilation might take some time
        },
    ]
);

});
