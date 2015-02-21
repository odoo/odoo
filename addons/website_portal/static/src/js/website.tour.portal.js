(function () {
    'use strict';

    var _t = openerp._t;

    openerp.Tour.register({
        id:   'portal',
        name: _t("Create a portal post"),
        steps: [
            {
                title:     _t("New Portal Post"),
                content:   _t("Let's go through the first steps to write beautiful portal posts."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip") },
            },
            {
                element:   '#content-menu-button',
                placement: 'left',
                title:     _t("Add Content"),
                content:   _t("Use this <em>'Content'</em> menu to create a new portal post like any other document (page, menu, products, event, ...)."),
                popover:   { fixed: true },
            },
            {
                element:   'a[data-action=new_portal_post]',
                placement: 'left',
                title:     _t("New Portal Post"),
                content:   _t("Select this menu item to create a new portal post."),
                popover:   { fixed: true },
            },
            {
                element:   '.modal:has(#editor_new_portal) button.btn-primary',
                placement: 'right',
                title:     _t("Create Portal Post"),
                content:   _t("Click <em>Continue</em> to create the portal post."),
            },
            {
                waitFor:   'body:has(button[data-action=save]:visible):has(.js_portal)',
                title:     _t("Portal Post Created"),
                content:   _t("This is your new portal post. Let's edit it."),
                popover:   { next: _t("Continue") },
            },
            {
                element:   'h1[data-oe-expression="portal_post.name"]',
                placement: 'bottom',
                sampleText: 'New Portal',
                title:     _t("Set a Title"),
                content:   _t("Click on this area and set a catchy title for your portal post."),
            },
            {
                waitNot:   '#wrap h1[data-oe-model="portal.post"]:contains("Portal Post Title")',
                element:   'button[data-action=snippet]',
                placement: 'left',
                title:     _t("Layout Your Portal Post"),
                content:   _t("Use well designed building blocks to structure the content of your portal. Click 'Insert Blocks' to add new content."),
                popover:   { fixed: true },
            },
            {
                snippet:   '#snippet_structure .oe_snippet:eq(2)',
                placement: 'bottom',
                title:     _t("Drag & Drop a Block"),
                content:   _t("Drag this block and drop it in your page."),
                popover:   { fixed: true },
            },
            {
                element:   'button[data-action=snippet]',
                placement: 'bottom',
                title:     _t("Add Another Block"),
                content:   _t("Let's add another block to your post."),
                popover:   { fixed: true },
            },
            {
                snippet:   '#snippet_structure .oe_snippet:eq(4)',
                placement: 'bottom',
                title:     _t("Drag & Drop a block"),
                content:   _t("Drag this block and drop it below the image block."),
                popover:   { fixed: true },
            },
            {
                element:   '.oe_active .oe_snippet_remove',
                placement: 'top',
                title:     _t("Delete the block"),
                content:   _t("From this toolbar you can move, duplicate or delete the selected zone. Click on the garbage can image to delete the block. Or click on the Title and delete it."),
            },
            {
                waitNot:   '.oe_active .oe_snippet_remove:visible',
                element:   'button[data-action=save]',
                placement: 'right',
                title:     _t("Save Your Portal"),
                content:   _t("Click the <em>Save</em> button to record changes on the page."),
                popover:   { fixed: true },
            },
            {
                waitFor:   'button[data-action=edit]:visible',
                element:   'button.btn-danger.js_publish_btn',
                placement: 'top',
                title:     _t("Publish Your Post"),
                content:   _t("Your portal post is not yet published. You can update this draft version and publish it once you are ready."),
            },
            {
                waitFor:   '.js_publish_management button.js_publish_btn.btn-success:visible',
                title:     "Thanks!",
                content:   _t("This tutorial is finished. To discover more features, improve the content of this page and try the <em>Promote</em> button in the top right menu."),
                popover:   { next: _t("Close Tutorial") },
            },
        ]
    });

}());
