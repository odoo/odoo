(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.BlogTour(this));
            return this._super();
        },
    });

    website.BlogTour = website.Tour.extend({
        id: 'blog',
        name: "Create a blog post",
        testPath: /\/blogpost\/[0-9]+\//,
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    title:     "New Blog Post",
                    content:   "Let's go through the first steps to write beautiful blog posts.",
                    template:  self.popover({ next: "Start Tutorial", end: "Skip" }),
                },
                {
                    element:   '#content-menu-button',
                    placement: 'left',
                    title:     "Add Content",
                    content:   "Create new pages, blogs, menu items and products through the <em>'Content'</em> menu.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   'a[data-action=new_blog_post]',
                    placement: 'left',
                    title:     "New Blog Post",
                    content:   "Select this menu item to create a new blog post.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   '.modal button.btn-primary',
                    placement: 'bottom',
                    title:     "Create Blog Post",
                    content:   "Click <em>Continue</em> to create the blog post.",
                },
                {
                    waitNot:   '.modal',
                    title:     "Blog Post Created",
                    content:   "This is your new blog post. Let's edit it.",
                    template:  self.popover({ next: "Continue" }),
                },
                {
                    element:   'h1[data-oe-expression="blog_post.name"]',
                    placement: 'bottom',
                    sampleText: 'New Blog',
                    title:     "Set a Title",
                    content:   "Click on this area and set a catchy title for your blog post.",
                },
                {
                    waitNot:   '#wrap h1[data-oe-model="blog.post"]:contains("Blog Post Title")',
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Layout Your Blog Post",
                    content:   "Use well designed building blocks to structure the content of your blog. Click 'Insert Blocks' to add new content.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    snippet:   'image-text',
                    placement: 'bottom',
                    title:     "Drag & Drop a Block",
                    content:   "Drag the <em>'Image-Text'</em> block and drop it in your page.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   'button[data-action=snippet]',
                    placement: 'bottom',
                    title:     "Add Another Block",
                    content:   "Let's add another block to your post.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    snippet:   'text-block',
                    placement: 'bottom',
                    title:     "Drag & Drop a block",
                    content:   "Drag the <em>'Text Block'</em> block and drop it below the image block.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    element:   '.oe_active .oe_snippet_remove',
                    placement: 'top',
                    title:     "Delete the Title",
                    content:   "From this toolbar you can move, duplicate or delete the selected zone. Click on the garbage can image to delete the title.",
                },
                {
                    waitNot:   '.oe_active .oe_snippet_remove:visible',
                    element:   'button[data-action=save]',
                    placement: 'right',
                    title:     "Save Your Blog",
                    content:   "Click the <em>Save</em> button to record changes on the page.",
                    template:  self.popover({ fixed: true }),
                },
                {
                    waitFor:   'button[data-action=edit]:visible',
                    element:   'button.btn-danger.js_publish_btn',
                    placement: 'top',
                    title:     "Publish Your Post",
                    content:   "Your blog post is not yet published. You can update this draft version and publish it once you are ready.",
                },
                {
                    waitFor:   '.js_publish_management button.js_publish_btn.btn-success:visible',
                    title:     "Thanks!",
                    content:   "This tutorial is finished. To discover more features, improve the content of this page and try the <em>Promote</em> button in the top right menu.",
                    template:  self.popover({ end: "Close Tutorial" }),
                },
            ];
            return this._super();
        },
    });

}());
