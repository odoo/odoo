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
        id: 'blog-tutorial',
        name: "Create a blog post",
        startPath: '/blog/cat/1/',
        init: function (editor) {
            var self = this;
            self.steps = [
            {
                    stepId: 'welcome-blog',
                    orphan: true,
                    backdrop: true,
                    title: "Blog",
                    content: "We will show how to create a new blog post.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Edit the content",
                    content: "Click here to add content to your site.",
                },
                {
                    stepId: 'new-post-entry',
                    element: 'a[data-action=new_blog_post]',
                    placement: 'left',
                    title: "New blog post",
                    content: "Click here to create a blog post.",
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
                },
                {
                    stepId: 'post-page',
                    orphan: true,
                    backdrop: true,
                    title: "New blog post created",
                    content: "You just created a new blog post. We are now going to edit it.",
                    template: self.popover({ next: "OK" }),
                },
                {
                    stepId: 'post-title',
                    element: 'h1[data-oe-expression="blog_post.name"]',
                    placement: 'top',
                    title: "Pick a title",
                    content: "Choose a catchy title for your blog post.",
                    template: self.popover({ next: "OK" }),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Layout your blog post",
                    content: "Insert blocks like text-image to layout the body of your blog post.",
                    onShow: function () {
                        $('button[data-action=snippet]').click(function () {
                            self.movetoStep('drag-image-text');
                        });
                    }
                },
                {
                    stepId: 'drag-image-text',
                    element: '#website-top-navbar [data-snippet-id=image-text].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Image Text' block and drop it in your page.",
                    onShow: function () {
                        var $body = $(document.body);
                        function beginDrag () {
                            $('.popover.tour').remove();
                            function goToNextStep () {
                                $('#snippets').toggle();
                                self.stop();
                                $body.off('mouseup', goToNextStep);
                            }
                            $body.off('mousedown', beginDrag);
                            $body.on('mouseup', goToNextStep);
                        }
                        $body.on('mousedown', beginDrag);
                    },
                },
            ];
            return this._super();
        },
        continue: function () {
            return this.isCurrentStep('post-page') && !this.tour.ended();
        },
        trigger: function () {
            return (this.continue() && this.testUrl(/^\/blog\/[0-9]+\/\?enable_editor=1/)) || this._super();
        },
    });

}());
