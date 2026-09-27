/* global ace */

import { registry } from "@web/core/registry";
import { clickOnSave } from "@website/js/tours/tour_utils";

const resetView = (mode) => [
    {
        content: "Set iframe as ready to allow tour to run",
        trigger: ".o_iframe_container :iframe",
        async run({ waitFor }) {
            const errorEl = await waitFor(":iframe #error_message", { timeout: 2000 });
            // Without this, is-ready is never set to true on the error page,
            // and the trigger can only work if is-ready is not false.
            errorEl.ownerDocument.body.setAttribute("is-ready", "true");
        },
    },
    {
        content: "Soft reset the view",
        trigger: `:iframe .reset_templates_button[data-mode='${mode}']`,
        run: "click",
    },
    {
        content: "Type 'yes' in modal",
        trigger: ":iframe .modal-dialog input#page-name",
        run: "edit yes",
    },
    {
        content: "Confirm modal",
        trigger: ":iframe .modal-dialog input[value='Confirm']",
        run: "click",
    },
    {
        content: "check that the view got fixed",
        trigger: ":iframe p:text(Test Page View)",
    },
    {
        content: "check that the inherited COW view is still there (created during edit mode)",
        trigger: ":iframe #oe_structure_test_website_page .s_cover",
    },
];

registry.category("web_tour.tours").add("test_reset_page_view_complete_flow", {
    steps: () => [
        {
            content: "Drag the Intro snippet group and drop it in #oe_structure_test_website_page.",
            trigger:
                ".o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name='Intro'] .o_snippet_thumbnail .o_snippet_thumbnail_area",
            // id starting by 'oe_structure..' will actually create an inherited view
            run: "drag_and_drop :iframe #oe_structure_test_website_page",
        },
        {
            content: "Click on the s_cover snippet.",
            trigger: ':iframe .o_snippet_preview_wrap[data-snippet-id="s_cover"]',
            run: "click",
        },
        ...clickOnSave(),
        // 2. Edit that COW'd view in the HTML editor to break it.
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
            content: "add a broken t-field in page DOM",
            trigger: 'div.ace_line .ace_xml:contains("placeholder")',
            run() {
                ace.edit(document.querySelector("#resource-editor div"))
                    .getSession()
                    .insert({ row: 4, column: 1 }, '<t t-field="not.exist"/>\n');
            },
        },
        {
            trigger: '.ace_content:contains("not.exist")',
        },
        {
            content: "save the html editor",
            trigger: ".o_resource_editor button:contains(Save)",
            run: "click",
        },
        ...resetView("soft"),
        //4. Now break the inherited view created when dropping a snippet
        {
            content: "select oe_structure view",
            trigger: ".o_resource_editor_title .o_select_menu_toggler",
            run: "click",
        },
        {
            content: "select oe_structure view",
            trigger: ".o_select_menu_menu .o_select_menu_item:contains(Test Page View)",
            run: "click",
        },
        {
            content: "add a broken t-field in page DOM",
            trigger: 'div.ace_line .ace_xml:contains("oe_structure_test_website_page")',
            run() {
                ace.edit(document.querySelector("#resource-editor div"))
                    .getSession()
                    .insert({ row: 4, column: 1 }, '<t t-field="not.exist"/>\n');
            },
        },
        {
            content: "save the html editor",
            trigger: ".o_resource_editor button:contains(Save)",
            run: "click",
        },
        ...resetView("hard"),
    ],
});
