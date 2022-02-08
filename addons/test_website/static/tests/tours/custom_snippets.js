odoo.define('test_website.custom_snippets', function (require) {
'use strict';

var tour = require('web_tour.tour');

/**
 * The purpose of this tour is to check the custom snippets flow:
 *
 * -> go to edit mode
 * -> drag a banner into page content
 * -> customize banner (set text)
 * -> save banner as custom snippet
 * -> confirm save
 * -> ensure custom snippet is available
 * -> drag custom snippet
 * -> ensure block appears as banner
 * -> ensure block appears as custom banner
 * -> rename custom banner
 * -> verify rename took effect
 * -> delete custom snippet
 * -> confirm delete
 * -> ensure it was deleted
 */

tour.register('test_custom_snippet', {
    url: '/',
    test: true
}, [
    {
        content: "enter edit mode",
        trigger: "a[data-action=edit]"
    },
    {
        content: "drop a snippet",
        trigger: "#oe_snippets .oe_snippet[name='Banner'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        extra_trigger: "body.editor_enable.editor_has_snippets",
        moveTrigger: ".oe_drop_zone",
        run: "drag_and_drop #wrap",
    },
    {
        content: "customize snippet",
        trigger: "#wrapwrap .s_banner h1",
        run: "text",
        consumeEvent: "input",
    },
    {
        content: "save custom snippet",
        trigger: ".snippet-option-SnippetSave we-button",
    },
    {
        content: "confirm reload",
        trigger: ".modal-dialog button span:contains('Save and Reload')",
    },
    {
        content: "ensure custom snippet appeared",
        trigger: "#oe_snippets .oe_snippet[name='Custom Banner']",
        run: function () {
            $("#oe_snippets .oe_snippet[name='Custom Banner'] .o_rename_btn").attr("style", "display: block;");
            // hover is needed for rename button to appear
        },
    },
    {
        content: "rename custom snippet",
        trigger: ".oe_snippet[name='Custom Banner'] we-button.o_rename_btn",
        extra_trigger: ".oe_snippet[name='Custom Banner'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
    },
    {
        content: "set name",
        trigger: ".oe_snippet[name='Custom Banner'] input",
        run: "text Bruce Banner",
    },
    {
        content: "confirm rename",
        trigger: ".oe_snippet[name='Custom Banner'] we-button.o_we_confirm_btn",
    },
    {
        content: "drop custom snippet",
        trigger: ".oe_snippet[name='Bruce Banner'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        extra_trigger: "body.editor_enable.editor_has_snippets",
        moveTrigger: ".oe_drop_zone",
        run: "drag_and_drop #wrap",
    },
    {
        content: "ensure banner section exists",
        trigger: "#wrap section[data-name='Banner']",
        run: function () {}, // check
    },
    {
        content: "ensure custom banner section exists",
        trigger: "#wrap section[data-name='Bruce Banner']",
        run: function () {
            $("#oe_snippets .oe_snippet[name='Bruce Banner'] .o_delete_btn").attr("style", "display: block;");
            // hover is needed for delete button to appear
        },
    },
    {
        content: "delete custom snippet",
        trigger: ".oe_snippet[name='Bruce Banner'] we-button.o_delete_btn",
        extra_trigger: ".oe_snippet[name='Bruce Banner'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
    },
    {
        content: "confirm delete",
        trigger: ".modal-dialog button:has(span:contains('Yes'))",
    },
    {
        content: "ensure custom snippet disappeared",
        trigger: "#oe_snippets",
        extra_trigger: "#oe_snippets:not(:has(.oe_snippet[name='Bruce Banner']))",
        run: function () {}, // check
    },
]);

});
