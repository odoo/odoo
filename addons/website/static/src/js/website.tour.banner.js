(function () {
    'use strict';

    var website = openerp.website;

    website.EditorBar.include({
        start: function () {
            this.registerTour(new website.BannerTour(this));
            return this._super();
        },
    });

    website.BannerTour = website.Tour.extend({
        id: 'banner-tutorial',
        name: "Insert a banner",
        startPath: '/page/website.homepage',
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you to build your home page. We will start by adding a banner.",
                    template: self.popover({ next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'bottom',
                    title: "Edit this page",
                    content: "Every page of your website can be modified through the <i>Edit</i> button.",
                    triggers: function () {
                        editor.on('tour:editor_bar_loaded', self, self.moveToNextStep);
                    },
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Insert building blocks",
                    content: "To add content in a page, you can insert building blocks.",
                    triggers: function () {
                        $('button[data-action=snippet]').one('click', function () {
                            self.moveToNextStep();
                        });
                    }
                },
                {
                    stepId: 'drag-banner',
                    element: '#website-top-navbar [data-snippet-id=carousel].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a Banner",
                    content: "Drag the Banner block and drop it in your page.",
                    triggers: function () {
                        self.onSnippetDraggedAdvance('carousel');
                    },
                },
                {
                    stepId: 'edit-title',
                    element: '#wrap [data-snippet-id=carousel]:first .carousel-caption',
                    placement: 'top',
                    title: "Customize banner's text",
                    content: "Click in the text and start editing it. Click continue once it's done.",
                    template: self.popover({ next: "Continue" }),
                    triggers: function () {
                        var $banner = $("#wrap [data-snippet-id=carousel]:first");
                        if ($banner.length) {
                            $banner.click();
                        }
                    },
                },
                {
                    stepId: 'customize-banner',
                    element: '.oe_overlay_options .oe_options',
                    placement: 'left',
                    title: "Customize the banner",
                    content: "You can customize characteristic of any blocks through the Customize menu. For instance, change the background of the banner.",
                    template: self.popover({ next: "Continue" }),
                    triggers: function () {
                        $('.dropdown-menu [name=carousel-background]').one('click', function () {
                            self.moveToNextStep();
                        });
                    },
                },
                {
                    stepId: 'save-changes',
                    element: 'button[data-action=save]',
                    placement: 'right',
                    reflex: true,
                    title: "Save your modifications",
                    content: "Once you click on save, your website page is updated.",
                },
                {
                    stepId: 'part-2',
                    orphan: true,
                    title: "Congratulation!",
                    content: "Your homepage have been updated. Now, we suggest you insert another snippet to overview possible customization.",
                    template: self.popover({ next: "Continue" }),
                },
                {
                    stepId: 'show-tutorials',
                    element: '#help-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Help is always available",
                    content: "You can always click here if you want more helps or continue to build and get more tips about your website contents like page menu, ...",
                    template: self.popover({ end: "Close" }),
                }
            ];
            return this._super();
        },
        resume: function () {
            return (this.isCurrentStep('part-2') || this.isCurrentStep('show-tutorials')) && !this.tour.ended();
        },
    });

}());
