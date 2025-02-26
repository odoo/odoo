/** @odoo-module**/
/* global ace */

import wTourUtils from "@website/js/tours/tour_utils";

const adminCssModif = '#wrap {display: none;}';
const demoCssModif = '// demo_edition';

wTourUtils.registerWebsitePreviewTour('html_editor_language', {
    url: '/test_page',
    test: true,
}, () => [{
    content: "open site menu",
    trigger: 'button[data-menu-xmlid="website.menu_site"]',
}, {
    content: "open html editor",
    trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
}, {
    content: "add something in the page's default language version",
    trigger: 'div.ace_line .ace_xml:contains("rommelpot")',
    run: () => {
        ace.edit(document.querySelector('#resource-editor div')).getSession().insert({
            row: 1,
            column: 1,
        }, '<div class="test_language"/>\n');
    },
}, {
    content: "save the html editor",
    extra_trigger: 'div.ace_line .ace_xml:contains("test_language")',
    trigger: ".o_resource_editor .btn-primary",
}, {
    content: "check that the page has the modification",
    trigger: 'iframe #wrapwrap:has(.test_language)',
    isCheck: true,
}, {
    content: "check that the page has not lost the original text",
    trigger: 'iframe #wrapwrap:contains("rommelpot")',
    isCheck: true,
}]
);

wTourUtils.registerWebsitePreviewTour('html_editor_multiple_templates', {
    url: '/generic',
    edition: true,
    test: true,
},
    () => [
        {
            content: "drop a snippet",
            trigger: ".oe_snippet:has(.s_cover) .oe_snippet_thumbnail",
            // id starting by 'oe_structure..' will actually create an inherited view
            run: "drag_and_drop_native iframe #oe_structure_test_ui",
        },
        ...wTourUtils.clickOnSave(),
        // 2. Edit generic view
        {
            content: "open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
        },
        {
            content: "open html editor",
            trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
        },
        {
            content: "add something in the generic view",
            trigger: 'div.ace_line .ace_xml:contains("Generic")',
            run: function () {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 3, column: 1}, '<p>somenewcontent</p>\n');
            },
        },
        // 3. Edit oe_structure specific view
        {
            content: "select oe_structure specific view",
            trigger: 'div.ace_line .ace_xml:contains("somenewcontent")',
            run: function () {},
        },
        {
            content: "open file selector menu",
            trigger: ".o_resource_editor .o_select_menu_toggler",
        },
        {
            content: "open oe_structure_test_ui view",
            trigger: ".o_resource_editor .o_select_menu_item:contains(oe_structure_test_ui)",
        },
        {
            content: "add something in the oe_structure specific view",
            extra_trigger: '.o_resource_editor .o_select_menu_toggler:contains("oe_structure_test_ui")',
            trigger: 'div.ace_line .ace_xml:contains("s_cover")',
            run: function () {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 1}, '<p>anothernewcontent</p>\n');
            },
        },
        {
            content: "save the html editor",
            extra_trigger: 'div.ace_line .ace_xml:contains("anothernewcontent")',
            trigger: ".o_resource_editor button:contains(Save)",
        },
        {
           content: "check that the page has both modification",
           extra_trigger: 'iframe #wrapwrap:contains("anothernewcontent")',
           trigger: 'iframe #wrapwrap:contains("somenewcontent")',
           run: function () {}, // it's a check
       },
    ]
);

wTourUtils.registerWebsitePreviewTour('test_html_editor_scss', {
    url: '/contactus',
    test: true,
},
    () => [
        // 1. Open Html Editor and select a scss file
        {
            content: "open site menu",
            extra_trigger: 'iframe #wrap:visible', // ensure state for later
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
        },
        {
            content: "open html editor",
            trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
        },
        {
            content: "open type switcher",
            trigger: '.o_resource_editor_type_switcher button',
        },
        {
            content: "select scss files",
            trigger: '.o_resource_editor_type_switcher .dropdown-item:contains("SCSS")',
        },
        {
            content: "select 'user_custom_rules'",
            trigger: '.o_resource_editor .o_select_menu_toggler:contains("user_custom_rules")',
            run: () => {},
        },
        // 2. Edit that file and ensure it was saved then reset it
        {
            content: "add some scss content in the file",
            trigger: 'div.ace_line .ace_comment:contains("footer {")',
            run: function () {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 0}, `${adminCssModif}\n`);
            },
        },
        {
            content: "save the html editor",
            extra_trigger: `div.ace_line:contains("${adminCssModif}")`,
            trigger: ".o_resource_editor_title button:contains(Save)",
        },
        {
            content: "check that the scss modification got applied",
            trigger: 'iframe body:has(#wrap:hidden)',
            run: function () {}, // it's a check
            timeout: 30000, // SCSS compilation might take some time
        },
        {
            content: "reset view (after reload, html editor should have been reopened where it was)",
            trigger: '#resource-editor-id button:contains(Reset)',
        },
        {
            content: "confirm reset warning",
            trigger: '.modal-footer .btn-primary',
        },
        {
            content: "check that the scss file was reset correctly, wrap content should now be visible again",
            trigger: 'iframe #wrap:visible',
            run: function () {}, // it's a check
            timeout: 30000, // SCSS compilation might take some time
        },
        // 3. Customize again that file (will be used in second part of the test
        //    to ensure restricted user can still use the HTML Editor)
        {
            content: "add some scss content in the file",
            trigger: 'div.ace_line .ace_comment:contains("footer {")',
            run: function () {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 0}, `${adminCssModif}\n`);
            },
        },
        {
            content: "save the html editor",
            extra_trigger: `div.ace_line:contains("${adminCssModif}")`,
            trigger: ".o_resource_editor_title button:contains(Save)",
        },
        {
            content: "check that the scss modification got applied",
            trigger: 'iframe body:has(#wrap:hidden)',
            run: function () {}, // it's a check
        },
    ]
);

wTourUtils.registerWebsitePreviewTour('test_html_editor_scss_2', {
    url: '/',
    test: true,
},
    () => [
        // This part of the test ensures that a restricted user can still use
        // the HTML Editor if someone else made a customization previously.

        // 4. Open Html Editor and select a scss file
        {
            content: "open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
        },
        {
            content: "open html editor",
            trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
        },
        {
            content: "open type switcher",
            trigger: '.o_resource_editor_type_switcher button',
        },
        {
            content: "select scss files",
            trigger: '.o_resource_editor_type_switcher .dropdown-item:contains("SCSS")',
        },
        {
            content: "select 'user_custom_rules'",
            trigger: '.o_resource_editor .o_select_menu_toggler:contains("user_custom_rules")',
            run: () => {},
        },
        // 5. Edit that file and ensure it was saved then reset it
        {
            content: "add some scss content in the file",
            trigger: `div.ace_line:contains("${adminCssModif}")`, // ensure the admin modification is here
            run: function () {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 0}, `${demoCssModif}\n`);
            },
        },
        {
            content: "save the html editor",
            extra_trigger: `div.ace_line:contains("${demoCssModif}")`,
            trigger: ".o_resource_editor button:contains(Save)",
        },
        {
            content: "reset view (after reload, html editor should have been reopened where it was)",
            trigger: '#resource-editor-id button:contains(Reset)',
            timeout: 30000, // SCSS compilation might take some time
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
