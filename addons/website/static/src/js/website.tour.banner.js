(function () {
    'use strict';

    var website = openerp.website;

    var render = website.tour.render;

    website.EditorBannerTour = website.EditorTour.extend({
        id: 'add_banner_tour',
        name: "Insert a banner",
        init: function (editor) {
            var self = this;
            var $body = $(document.body);
            self.steps = [
                {
                    stepId: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you to build your home page. We will start by adding a banner.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'bottom',
                    title: "Edit this page",
                    content: "Every page of your website can be modified through the <i>Edit</i> button.",
                    template: render('website.tour_popover'),
                    onShow: function () {
                        editor.on('tour:editor_bar_loaded', editor, function() {
                            self.movetoStep('add-block');
                        });
                    },
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Insert building blocks",
                    content: "To add content in a page, you can insert building blocks.",
                    template: render('website.tour_popover'),
                    onShow: function () {
                        $('button[data-action=snippet]').click(function () {
                            self.movetoStep('drag-banner');
                        });
                    }
                },
                {
                    stepId: 'drag-banner',
                    element: '#website-top-navbar [data-snippet-id=carousel].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a Banner",
                    content: "Drag the Banner block and drop it in your page.",
                    template: render('website.tour_popover'),
                    onShow: function () {
                        function beginDrag () {
                            $('.popover.tour').remove();
                            function goToNextStep () {
                                $('#oe_snippets').hide();
                                self.movetoStep('edit-title');
                                $body.off('mouseup', goToNextStep);
                            }
                            $body.off('mousedown', beginDrag);
                            $body.on('mouseup', goToNextStep);
                        }

                        $body.on('mousedown', beginDrag);
                    },
                },
                {
                    stepId: 'edit-title',
                    element: '#wrap [data-snippet-id=carousel]:first .carousel-caption',
                    placement: 'top',
                    title: "Customize banner's text",
                    content: "Click in the text and start editing it. Click continue once it's done.",
                    template: render('website.tour_popover', { next: "Continue" }),
                    onHide: function () {
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
                    template: render('website.tour_popover', { next: "Continue" }),
                    onShow: function () {
                        $('.dropdown-menu [name=carousel-background]').click(function () {
                            self.movetoStep('save-changes');
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
                    template: render('website.tour_popover'),
                    onHide: function () {
                        self.saveStep('part-2');
                    },
                },
                {
                    stepId: 'part-2',
                    orphan: true,
                    title: "Congratulation!",
                    content: "Your homepage have been updated. Now, we suggest you to insert others building blocks like texts and images to structure your page.",
                    template: render('website.tour_popover', { next: "Continue" }),
                },
                {
                    stepId: 'show-tutorials',
                    element: '#help-menu-button',
                    placement: 'left',
                    reflex: true,
                    title: "Help is always available",
                    content: "You can always click here if you want more helps or continue to build and get more tips about your website contents like page menu, ...",
                    template: render('website.tour_popover', { end: "Close" }),
                }
            ];
            return this._super();
        },
        startOfPart2: function () {
            var currentStepIndex = this.currentStepIndex();
            var secondPartIndex = this.indexOfStep('part-2');
            var showTutorialsIndex = this.indexOfStep('show-tutorials');
            return (currentStepIndex === secondPartIndex || currentStepIndex === showTutorialsIndex) && !this.tour.ended();
        },
        canResume: function () {
            return this.startOfPart2() || this._super();
        },
    });

    website.EditorBar.include({
        start: function () {
            var menu = $('#help-menu');
            var bannerTour = new website.EditorBannerTour(this);
            var $menuItem = $($.parseHTML('<li><a href="#">'+bannerTour.name+'</a></li>'));
            $menuItem.click(function () {
                if (url.pathname !== '/' && url.pathname !== '/page/website.homepage') {
                    window.location.replace('/page/website.homepage?banner-tutorial=true');
                }
                bannerTour.reset();
                bannerTour.start();
            });
            menu.append($menuItem);
            var url = new website.UrlParser(window.location.href);
            if (url.search.indexOf('?banner-tutorial=true') === 0 || bannerTour.startOfPart2()) {
                bannerTour.start();
            }
            return this._super();
        },
    });

}());
