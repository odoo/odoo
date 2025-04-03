/** @odoo-module**/
/* global ace */

import {clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

const adminCssModif = '#wrap {display: none;}';
const demoCssModif = '// demo_edition';

registerWebsitePreviewTour('html_editor_language', {
    url: '/test_page',
}, () => [
    {
        content: "Wait the content is loaded and html/css editor is in menu before clicking on open site menu",
        trigger: ":iframe main:contains(rommelpot)",
    },
    {
    content: "open site menu",
    trigger: 'button[data-menu-xmlid="website.menu_site"]',
    run: "click",
}, {
    content: "open html editor",
    trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
    run: "click",
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
    trigger: 'body:has(div.ace_line .ace_xml:contains("test_language")) .o_resource_editor .btn-primary',
    run: "click",
}, {
    content: "check that the page has the modification",
    trigger: ':iframe #wrapwrap:has(.test_language)',
}, {
    content: "check that the page has not lost the original text",
    trigger: ':iframe #wrapwrap:contains("rommelpot")',
}]
);

registerWebsitePreviewTour('html_editor_multiple_templates', {
    url: '/generic',
    edition: true,
},
    () => [
        {
            content: "drop a snippet group",
            trigger: "#oe_snippets .oe_snippet[name=Intro].o_we_draggable .oe_snippet_thumbnail",
            // id starting by 'oe_structure..' will actually create an inherited view
            run: "drag_and_drop :iframe #oe_structure_test_ui",
        },
        {
            content: "Click on the s_cover snippet",
            trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_cover"]',
            run: "click",
        },
        ...clickOnSave(),
        // 2. Edit generic view
        {
            content: "open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "open html editor",
            trigger: 'a[data-menu-xmlid="website.menu_ace_editor"]',
            run: "click",
        },
        {
            content: "add something in the generic view",
            trigger: 'div.ace_line .ace_xml:contains("Generic")',
            run() {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 3, column: 1}, '<p>somenewcontent</p>\n');
            },
        },
        // 3. Edit oe_structure specific view
        {
            content: "select oe_structure specific view",
            trigger: 'div.ace_line .ace_xml:contains("somenewcontent")',
        },
        {
            content: "open file selector menu",
            trigger: ".o_resource_editor .o_select_menu_toggler",
            run: "click",
        },
        {
            content: "open oe_structure_test_ui view",
            trigger: ".o-dropdown--menu .o-dropdown-item:contains(oe_structure_test_ui)",
            run: "click",
        },
        {
            trigger: '.o_resource_editor .o_select_menu_toggler:contains("oe_structure_test_ui")',
        },
        {
            content: "add something in the oe_structure specific view",
            trigger: 'div.ace_line .ace_xml:contains("s_cover")',
            run() {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 1}, '<p>anothernewcontent</p>\n');
            },
        },
        {
            trigger: 'div.ace_line .ace_xml:contains("anothernewcontent")',
        },
        {
            content: "save the html editor",
            trigger: ".o_resource_editor button:contains(Save)",
            run: "click",
        },
        {
            trigger: ':iframe #wrapwrap:contains("anothernewcontent")',
        },
        {
           content: "check that the page has both modification",
           trigger: ':iframe #wrapwrap:contains("somenewcontent")',
       },
    ]
);

registerWebsitePreviewTour('test_html_editor_scss', {
    url: '/contactus',
},
    () => [
        // 1. Open Html Editor and select a scss file
        {
            trigger: ":iframe #wrap:visible", // ensure state for later
        },
        {
            trigger: ":iframe h1:contains(contact us)",
        },
        {
            trigger: ":iframe input[name=company]",
        },
        {
            content: "open site menu",
            trigger: 'nav button[data-menu-xmlid="website.menu_site"]:contains(site)',
            run: "click",
        },
        {
            content: "open html editor",
            trigger: '.o_popover a[data-menu-xmlid="website.menu_ace_editor"]:contains(/^HTML/)',
            run: "click",
        },
        {
            content: "open type switcher",
            trigger: '.o_resource_editor_type_switcher button',
            run: "click",
        },
        {
            content: "select scss files",
            trigger: '.o-dropdown--menu .dropdown-item:contains("SCSS")',
            run: "click",
        },
        {
            content: "select 'user_custom_rules'",
            trigger: '.o_resource_editor .o_select_menu_toggler:contains("user_custom_rules")',
        },
        // 2. Edit that file and ensure it was saved then reset it
        {
            content: "add some scss content in the file",
            trigger: 'div.ace_line .ace_comment:contains("footer {")',
            run() {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 0}, `${adminCssModif}\n`);
            },
        },
        {
            trigger: `div.ace_line:contains("${adminCssModif}")`,
        },
        {
            content: "save the html editor",
            trigger: ".o_resource_editor_title button:contains(Save)",
            run: "click",
        },
        {
            content: "check that the scss modification got applied",
            trigger: ':iframe body:has(#wrap:hidden)',
            timeout: 30000, // SCSS compilation might take some time
        },
        {
            content: "reset view (after reload, html editor should have been reopened where it was)",
            trigger: '#resource-editor-id button:contains(Reset)',
            run: "click",
        },
        {
            content: "confirm reset warning",
            trigger: '.modal-footer .btn-primary',
            run: "click",
        },
        {
            content: "check that the scss file was reset correctly, wrap content should now be visible again",
            trigger: ':iframe #wrap:visible',
            timeout: 30000, // SCSS compilation might take some time
        },
        // 3. Customize again that file (will be used in second part of the test
        //    to ensure restricted user can still use the HTML Editor)
        {
            content: "add some scss content in the file",
            trigger: 'div.ace_line .ace_comment:contains("footer {")',
            run() {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 0}, `${adminCssModif}\n`);
            },
        },
        {
            trigger: `div.ace_line:contains("${adminCssModif}")`,
        },
        {
            content: "save the html editor",
            trigger: ".o_resource_editor_title button:contains(Save)",
            run: "click",
        },
        {
            content: "check that the scss modification got applied",
            trigger: ':iframe body:has(#wrap:hidden)',
        },
    ]
);

registerWebsitePreviewTour('test_html_editor_scss_2', {
    url: '/',
},
    () => [
        // This part of the test ensures that a restricted user can still use
        // the HTML Editor if someone else made a customization previously.

        // 4. Open Html Editor and select a scss file
        {
            trigger: "[is-ready=true]:iframe #wrapwrap",
        },
        {
            content: "open site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "open html editor",
            trigger: '.o_popover a[data-menu-xmlid="website.menu_ace_editor"]:contains(/^HTML/)',
            run: "click",
        },
        {
            content: "open type switcher",
            trigger: '.o_resource_editor_type_switcher button',
            run: "click",
        },
        {
            content: "select scss files",
            trigger: '.o-dropdown--menu .dropdown-item:contains("SCSS")',
            run: "click",
        },
        {
            content: "select 'user_custom_rules'",
            trigger: '.o_resource_editor .o_select_menu_toggler:contains("user_custom_rules")',
        },
        // 5. Edit that file and ensure it was saved then reset it
        {
            content: "add some scss content in the file",
            trigger: `div.ace_line:contains("${adminCssModif}")`,
            // ensure the admin modification is here
            run() {
                ace.edit(document.querySelector('#resource-editor div')).getSession().insert({row: 2, column: 0}, `${demoCssModif}\n`);
            },
        },
        {
            trigger: `div.ace_line:contains("${demoCssModif}")`,
        },
        {
            content: "save the html editor",
            trigger: ".o_resource_editor button:contains(Save)",
            run: "click",
        },
        {
            content: "reset view (after reload, html editor should have been reopened where it was)",
            trigger: '#resource-editor-id button:contains(Reset)',
            timeout: 30000, // SCSS compilation might take some time
            run: "click",
        },
        {
            content: "confirm reset warning",
            trigger: ".modal:contains(careful) .modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Wait for the reload of the iframe",
            trigger: "[is-ready=false]:iframe #wrapwrap",
        },
        {
            trigger: "[is-ready=true]:iframe #wrapwrap",
        },
        {
            trigger: `body:not(:has(div.ace_line:contains("${adminCssModif}")))`,
        },
        {
            content: "check that the scss file was reset correctly",
            trigger: `body:not(:has(div.ace_line:contains("${demoCssModif}")))`,
            timeout: 30000, // SCSS compilation might take some time
        },
    ]
);

registerWebsitePreviewTour(
    "website_code_editor_usable",
    {
        // TODO: enable debug mode when failing tests have been fixed (props validation)
        url: "/",
    },
    () => [
        {
            trigger: ":iframe #wrapwrap",
        },
        {
            content: "Open Site menu",
            trigger: 'button[data-menu-xmlid="website.menu_site"]',
            run: "click",
        },
        {
            content: "Open HTML / CSS Editor",
            trigger: '.o_popover a[data-menu-xmlid="website.menu_ace_editor"]:contains(/^HTML/)',
            run: "click",
        },
        {
            content: "Bypass warning",
            trigger: ".o_resource_editor_wrapper div:nth-child(2) button:nth-child(3)",
            run: "click",
        },
        // Test all 3 file type options
        ...[{
            menuItemIndex: 1,
            editorMode: 'qweb',
        }, {
            menuItemIndex: 2,
            editorMode: 'scss',
        }, {
            menuItemIndex: 3,
            editorMode: 'javascript',
        }]
            .map(({ menuItemIndex, editorMode }) => [
                {
                    content: "Open file type dropdown",
                    trigger: ".o_resource_editor_type_switcher .dropdown-toggle",
                    run: "click",
                },
                {
                    content: `Select type ${menuItemIndex}`,
                    trigger: `.o-overlay-container .o-dropdown--menu .dropdown-item:nth-child(${menuItemIndex})`,
                    run: "click",
                },
                {
                    content: "Wait for editor mode to change",
                    trigger: `.ace_editor[data-mode="${editorMode}"]`,
                },
                {
                    content: "Make sure text is being highlighted",
                    trigger: ".ace_content .ace_text-layer .ace_line:first-child span",
                },
            ])
            .flat(),
    ]
);
