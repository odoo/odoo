(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.tour.xml');

    function render (template, dict)  {
        return openerp.qweb.render(template, dict);
    }

    website.EditorTour = openerp.Class.extend({
        tour: undefined,
        steps: [],
        tourStorage: window.localStorage,
        init: function () {
            this.tour = new Tour({
                name: this.id,
                storage: this.tourStorage,
                keyboard: false,
            });
            this.tour.addSteps(_.map(this.steps, function (step) {
               step.title = render('website.tour_title', { title: step.title });
               return step;
            }));
        },
        reset: function () {
            this.tourStorage.removeItem(this.id+'_current_step');
            this.tourStorage.removeItem(this.id+'_end');
            $('.popover.tour').remove();
        },
        start: function () {
            if (this.canResume()) {
                this.tour.start();
            }
        },
        canResume: function () {
            return this.currentStepIndex() === 0 && !this.tour.ended();
        },
        currentStepIndex: function () {
            var index = this.tourStorage.getItem(this.id+'_current_step') || 0;
            return parseInt(index, 10);
        },
        indexOfStep: function (stepId) {
            var index = -1;
            _.each(this.steps, function (step, i) {
               if (step.stepId === stepId) {
                   index = i;
               }
            });
            return index;
        },
        movetoStep: function (stepId) {
            $('.popover.tour').remove();
            var index = this.indexOfStep(stepId);
            if (index > -1) {
                this.tour.goto(index);
            }
        },
        saveStep: function (stepId) {
            var index = this.indexOfStep(stepId);
            this.tourStorage.setItem(this.id+'_current_step', index);
        },
        stop: function () {
            this.tour.end();
        },
    });

    website.EditorBasicTour = website.EditorTour.extend({
        id: 'add_banner_tour',
        name: "How to add a banner",
        init: function () {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you through the firsts steps to build your enterprise class website.",
                    template: render('website.tour_full', { next: "OK", end: "Close" }),
                },
                {
                    stepId: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'right',
                    reflex: true,
                    title: "Edit this page",
                    content: "Every page of your website can be edited. Click the <b>Edit</b> button to modify your homepage.",
                    template: render('website.tour_simple'),
                },
                {
                    stepId: 'show-bar',
                    element: '#website-top-navbar',
                    placement: 'bottom',
                    title: "Editor bar",
                    content: "This is the <b>Editor Bar</b>, use it to modify your website's pages.",
                    template: render('website.tour_confirm', { next: "OK" }),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'right',
                    reflex: true,
                    title: "Add a block to your page",
                    content: "Click on the <b>Insert Blocks</b> button to open the block collection.",
                    template: render('website.tour_simple'),
                },
                {
                    stepId: 'drag-banner',
                    element: '#website-top-navbar [data-snippet-id=carousel]',
                    placement: 'bottom',
                    title: "Add a banner to your page",
                    content: "Drag the <b>Banner</b> block to the body of the page and drop it on a purple zone.",
                    template: render('website.tour_simple'),
                    onShown: function () {
                        function beginDrag () {
                            $('.popover.tour').remove();
                            $('body').off('mousedown', beginDrag);
                            function goToNextStep () {
                                $('#oe_snippets').hide();
                                self.movetoStep('edit-title');
                                $('body').off('mouseup', goToNextStep);
                            }
                            $('body').on('mouseup', goToNextStep);
                        }
                        $('body').on('mousedown', beginDrag);
                    },
                },
                {
                    stepId: 'edit-title',
                    element: '#wrap [data-snippet-id=carousel]:first .carousel-caption',
                    placement: 'top',
                    title: "Change the title",
                    content: "Click on the title and modify it to fit your needs then click <b>Done</b>.",
                    template: render('website.tour_confirm', { next: "Done" }),
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
                    content: "Click on <b>Customize</b> and change the background of your banner.",
                    template: render('website.tour_confirm', { next: "Not now" }),
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
                    content: "Click the <b>Save</b> button to apply modifications on your website.",
                    template: render('website.tour_simple'),
                    onHide: function () {
                        self.saveStep('part-2');
                    },

                },
                {
                    stepId: 'part-2',
                    orphan: true,
                    title: "Congratutaltions!",
                    content: "Congratulations on your first modifications.",
                    template: render('website.tour_confirm', { next: "OK" }),
                },
                {
                    stepId: 'show-tutorials',
                    element: '#help-menu-button',
                    placement: 'left',
                    title: "Help is always available",
                    content: "You can find more tutorials in the <b>Help</b> menu.",
                    template: render('website.tour_end', { end: "Close" }),
                },
            ];
            return this._super();
        },
        startOfPart2: function () {
            var currentStepIndex = this.currentStepIndex();
            var secondPartIndex = this.indexOfStep('part-2');
            return currentStepIndex === secondPartIndex && !this.tour.ended();
        },
        canResume: function () {
            return this.startOfPart2() || this._super();
        },
    });

    website.UrlParser = openerp.Class.extend({
        init: function (url) {
            var a = document.createElement('a');
            a.href = url;
            this.href = a.href;
            this.host = a.host;
            this.protocol = a.protocol;
            this.port = a.port;
            this.hostname = a.hostname;
            this.pathname = a.pathname;
            this.origin = a.origin;
            this.search = a.search;
        },
    });

    website.EditorBar.include({
        start: function () {
            website.tutorials = {
                basic: new website.EditorBasicTour(),
            };
            var menu = $('#help-menu');
            _.each(website.tutorials, function (tutorial) {
                var $menuItem = $($.parseHTML('<li><a href="#">'+tutorial.name+'</a></li>'));
                $menuItem.click(function () {
                    tutorial.reset();
                    tutorial.start();
                })
                menu.append($menuItem);
            });
            var url = new website.UrlParser(window.location.href);
            if (url.search === '?tutorial=true' || website.tutorials.basic.startOfPart2()) {
                website.tutorials.basic.start();
            }
            return this._super();
        },
    });

}());