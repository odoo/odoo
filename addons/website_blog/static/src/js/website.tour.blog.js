(function () {
    'use strict';

    var website = openerp.website;

    var render = website.tour.render;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.BlogTour(this));
            return this._super();
        },
    });

    website.BlogTour = website.Tour.extend({
        id: 'blog-tutorial',
        name: "Create a blog post",
        startPath: '/blog/cat/1/',
        init: function (editor) {
            var self = this;
            var $body = $(document.body);
            self.steps = [
            {
                    stepId: 'welcome-blog',
                    orphan: true,
                    backdrop: true,
                    title: "Blog",
                    content: "We will show how to create a new blog post.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Edit the content",
                    content: "Click here to add content to your site.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'new-post-entry',
                    element: 'a[data-action=new_blog_post]',
                    placement: 'left',
                    title: "New blog post",
                    content: "Click here to create a blog post.",
                    template: render('website.tour_popover'),
                    onShow: function () {
                        $(document).one('shown.bs.modal', function () {
                            $('.modal button.btn-primary').click(function () {
                                self.movetoStep('post-page');
                            });
                            self.movetoStep('choose-category');
                        });
                    },
                },
                {
                    stepId: 'choose-category',
                    element: '.modal select',
                    placement: 'right',
                    title: "Choose the post category",
                    content: "Select the 'News' category and click 'Continue'.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'post-page',
                    orphan: true,
                    backdrop: true,
                    title: "New blog post created",
                    content: "You just created a new blog post. We are now going to edit it.",
                    template: render('website.tour_popover', { next: "OK" }),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    reflex: true,
                    title: "Layout your blog post",
                    content: "Insert blocks like text-image to layout the body of your blog post.",
                    template: render('website.tour_popover'),
                },
            ];
            return this._super();
        },
        continueTour: function () {
            return this.isCurrentStep('post-page') && !this.tour.ended();
        },
        isTriggerUrl: function () {
            return (this.continueTour() && this.testUrl(/^\/blog\/[0-9]+\/\?enable_editor=1/)) || this._super();
        },
    });

}());
