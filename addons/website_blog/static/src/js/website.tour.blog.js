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
                    triggers: function () {
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
                    triggers: function () {
                        $('.modal select').change(function () {
                            var $this = $(this);
                            var selected = $this.find("[value="+$this.val()+"]").text();
                            if (selected.toLowerCase() === 'news') {
                                self.movetoStep('continue-category');
                            }
                        });
                    },
                },
                {
                    stepId: 'continue-category',
                    element: '.modal button.btn-primary',
                    placement: 'right',
                    title: "Choose the post category",
                    content: "Click 'Continue' to create the post.",
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
                    stepId: 'add-image-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Layout your blog post",
                    content: "Insert blocks like text-image to layout the body of your blog post.",
                    triggers: function () {
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
                    triggers: function () {
                        self.onSnippetDraggedMoveTo('add-text-block');
                    },
                },
                {
                    stepId: 'add-text-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Add another block",
                    content: "Let's add another blog to your post.",
                    triggers: function () {
                        $('button[data-action=snippet]').click(function () {
                            self.movetoStep('drag-text-block');
                        });
                    }
                },
                {
                    stepId: 'drag-text-block',
                    element: '#website-top-navbar [data-snippet-id=text-block].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the 'Text Block' block and drop it below the image block.",
                    triggers: function () {
                        self.onSnippetDraggedMoveTo('activate-text-block-title');
                    },
                },
                {
                    stepId: 'activate-text-block-title',
                    element: '#wrap [data-snippet-id=text-block] .text-center[data-snippet-id=colmd]',
                    placement: 'top',
                    title: "Activate on the title",
                    content: "Click on the title to activate it.",
                    triggers: function () {
                        $('#wrap [data-snippet-id=text-block] .text-center[data-snippet-id=colmd]').click(function () {
                            self.movetoStep('remove-text-block-title');
                        });
                    },
                },
                {
                    stepId: 'remove-text-block-title',
                    element: '.oe_snippet_remove:last',
                    placement: 'top',
                    reflex: true,
                    title: "Delete the title",
                    content: "Click on the cross to delete the title.",
                },
                {
                    stepId: 'publish-post',
                    element: 'button.js_publish_btn',
                    placement: 'right',
                    reflex: true,
                    title: "Publish your blog post",
                    content: "Click to publish your blog post.",
                },
                {
                    stepId: 'save-changes',
                    element: 'button[data-action=save]',
                    placement: 'right',
                    reflex: true,
                    title: "Save your modifications",
                    content: "Once you click on save, your post is updated.",
                },
            ];
            return this._super();
        },
        resume: function () {
            return this.isCurrentStep('post-page') && !this.tour.ended();
        },
        trigger: function () {
            return (this.resume() && this.testUrl(/^\/blog\/[0-9]+\/\?enable_editor=1/)) || this._super();
        },
    });

}());
