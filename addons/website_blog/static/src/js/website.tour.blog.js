odoo.define('website_blog.tour', function (require) {
'use strict';

var core = require('web.core');
var Tour = require('web.Tour');
var base = require('web_editor.base');

var _t = core._t;

base.ready().done(function () {

    Tour.register({
        id:   'blog',
        name: _t("Create a blog post"),
        steps: [
            {
                title:     _t("New Blog Post"),
                content:   _t("Let's go through the first steps to write beautiful blog posts."),
                popover:   { next: _t("Start Tutorial"), end: _t("Skip") },
            },
            {
                element:   '#content-menu-button',
                placement: 'left',
                title:     _t("Add Content"),
                content:   _t("Use this <em>'Content'</em> menu to create a new blog post like any other document (page, menu, products, event, ...)."),
                popover:   { fixed: true },
            },
            {
                element:   'a[data-action=new_blog_post]',
                placement: 'left',
                title:     _t("New Blog Post"),
                content:   _t("Select this menu item to create a new blog post."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '#o_scroll .oe_snippet',
                title:     _t("Blog Post Created"),
                content:   _t("This is your new blog post. Let's edit it."),
                popover:   { next: _t("Continue") },
            },
            {
                element:   'h1[data-oe-expression="blog_post.name"]',
                placement: 'top',
                title:     _t("Post Headline"),
                sampleText:'Blog Post Title',
                content:   _t("Write a title, the subtitle is optional."),
                popover:   { fixed: true },
            },
            {
                waitNot:   '#wrap h1[data-oe-expression="blog_post.name"]:'+'containsExact("")',
                element:   '#oe_manipulators .oe_overlay.oe_active a.btn.btn-primary.btn-sm',
                placement: 'left',
                title:     _t("Customize Cover"),
                content:   _t("Change and customize your blog post cover."),
                popover:   { fixed: true },
            },
            {
                element:   'a:'+ 'containsExact(' + _t("Change Cover")+ '):eq(1)',
                placement: 'left',
                title:     _t("Cover"),
                content:   _t("Select this menu item to change blog cover."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.modal:has(.existing-attachment-cell:nth(1))',
                element:   '.modal .existing-attachment-cell:nth(1) img',
                placement: 'top',
                title:     _t("Choose an image"),
                content:   _t("Choose an image from the library."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.existing-attachment-cell.media_selected',
                element:   '.modal-content button.save',
                placement: 'top',
                title:     _t("Save"),
                content:   _t("Click on '<em>Save</em>' to set the picture as cover."),
                popover:   { fixed: true },
            },
            {
                waitNot:   '.modal-content:visible',
                element:   '.blog_content section.mt16',
                placement: 'top',
                title:     _t("Content"),
                content:   _t("Start writing your story here. Click on save in the upper left corner when you are done."),
                sampleText: ' ',
                popover:   { fixed: true },
            },
            {
                waitNot:   '.blog_content section.mt16 p:'+'containsExact('+_t('Start writing here...')+')',
                element:   'button[data-action=save]',
                placement: 'right',
                title:     _t("Save Your Blog"),
                content:   _t("Click on '<em>Save</em>' button to record changes on the page."),
                popover:   { fixed: true },
            },
            {
                waitNot:   'button[data-action=save]:visible',
                element:   'a[data-action=show-mobile-preview]',
                placement: 'bottom',
                title:     _t("Mobile Preview"),
                content:   _t("Click on the mobile icon to preview how your blog post will be displayed on a mobile device."),
                popover:   { fixed: true },
            },
            {
                element:   '.modal:has(#mobile-viewport) button[data-dismiss=modal]',
                placement: 'right',
                title:     _t("Check Mobile Preview"),
                content:   _t("Scroll to check rendering and then close the mobile preview."),
                popover:   { fixed: true },
            },
            {
                waitNot:   '.modal:has(#mobile-viewport) button[data-dismiss=modal]:visible',
                element:   'button.btn-danger.js_publish_btn',
                placement: 'top',
                title:     _t("Publishing status"),
                content:   _t(" Click on this button to send your blog post online."),
                popover:   { fixed: true },
            },
            {
                waitFor:   '.js_publish_management button.js_publish_btn.btn-success:visible',
                title:     "Thanks!",
                content:   _t("This tutorial is over. To discover more features and improve the content of this page, go to the upper right customize menu. You can also add some cool content with your text by clicking on 'Insert Blocks' in the edit mode."),
                popover:   { next: _t("Close Tutorial") },
            },
        ]
    });
});

});
