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
                    title: "New Blog Post",
                    content: "Let's go through the first steps to write beautiful blog posts.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip" }),
                },
                {
                    stepId: 'content-menu',
                    element: '#content-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Add Content",
                    content: "Create new pages, blogs, menu items and products through the <em>'Content'</em> menu.",
                },
                {
                    stepId: 'new-post-entry',
                    element: 'a[data-action=new_blog_post]',
                    placement: 'left',
                    title: "New Blog Post",
                    content: "Select this entry to create a new blog post.",
                    triggers: function () {
                        var $doc = $(document);
                        function stopNewBlog () {
                            self.stop();
                        }
                        $doc.on('hide.bs.modal', stopNewBlog);
                        $doc.one('shown.bs.modal', function () {
                            $('.modal button.btn-primary').one('click', function () {
                                $doc.off('hide.bs.modal', stopNewBlog);
                                self.moveToStep('post-page');
                            });
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'choose-category',
                    element: '.modal select',
                    placement: 'right',
                    title: "Which Blog?",
                    content: "Blog posts are organized in multiple categories (news, job offers, events, etc). Select <em>News</em> and click <em>Continue</em>.",
                    triggers: function () {
                        function newsSelected () {
                            var $this = $(this);
                            if ($this.find('[value='+$this.val()+']').text().toLowerCase() === 'news') {
                                self.moveToNextStep();
                                $('.modal select').off('change', newsSelected);
                            }
                        }
                        $('.modal select').on('change', newsSelected);
                    },
                },
                {
                    stepId: 'continue-category',
                    element: '.modal button.btn-primary',
                    placement: 'right',
                    title: "Create Blog Post",
                    content: "Click <em>Continue</em> to create the blog post.",
                },
                {
                    stepId: 'post-page',
                    orphan: true,
                    title: "Blog Post Created",
                    content: "This is your new blog post. We will edit your pages inline. What You See Is What You Get. No need for a complex backend.",
                    template: self.popover({ next: "Continue" }),
                },
                {
                    stepId: 'post-title',
                    element: 'h1[data-oe-expression="blog_post.name"]',
                    placement: 'top',
                    title: "Pick a Title",
                    content: "Click on this area and set a catchy title.",
                    template: self.popover({ next: "OK" }),
                },
                {
                    stepId: 'add-image-text',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Layout Your Blog Post",
                    content: "Use well designed building blocks to structure the content of your blog.",
                    triggers: function () {
                        $('button[data-action=snippet]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'drag-image-text',
                    element: '#website-top-navbar [data-snippet-id=image-text].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a Block",
                    content: "Drag the <em>'Image-Text'</em> block and drop it in your page.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('image-text');
                    },
                },
                {
                    stepId: 'add-text-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Add Another Block",
                    content: "Let's add another block to your post.",
                    triggers: function () {
                        $('button[data-action=snippet]').on('click', function () {
                            self.moveToNextStep();
                        });
                    }
                },
                {
                    stepId: 'drag-text-block',
                    element: '#website-top-navbar [data-snippet-id=text-block].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a block",
                    content: "Drag the <em>'Text Block'</em> block and drop it below the image block.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('text-block');
                    },
                },
                {
                    stepId: 'activate-text-block-title',
                    element: '#wrap [data-snippet-id=text-block] .text-center[data-snippet-id=colmd]',
                    placement: 'top',
                    title: "Edit an Area",
                    content: "Select any area of the page to modify it. Click on this subtitle.",
                    triggers: function () {
                        $('#wrap [data-snippet-id=text-block] .text-center[data-snippet-id=colmd]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'remove-text-block-title',
                    element: '.oe_snippet_remove:last',
                    placement: 'top',
                    reflex: true,
                    title: "Delete the Title",
                    content: "From this toolbar you can move, duplicate or delete the selected zone. Click on the cross to delete the title.",
                },
                {
                    stepId: 'publish-post',
                    element: 'button.js_publish_btn',
                    placement: 'right',
                    reflex: true,
                    title: "Publish Your Post",
                    content: "Your blog post is not yet published. You can update this draft version and publish it once you are ready.",
                },
                {
                    stepId: 'save-changes',
                    element: 'button[data-action=save]',
                    placement: 'right',
                    reflex: true,
                    title: "Save Your Blog",
                    content: "Click the <em>Save</em> button to record changes on the page.",
                },
                {
                    stepId: 'end-tutorial',
                    orphan: true,
                    backdrop: true,
                    title: "Thanks!",
                    content: "This tutorial is finished. To discover more features, improve the content of this page and try the <em>Promote</em> button in the top right menu.",
                    template: self.popover({ next: "Close Tutorial" }),
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
