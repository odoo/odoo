(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.tour.xml');

    function render (template, dict)  {
        return openerp.qweb.render(template, dict);
    }

    website.EditorTour = openerp.Class.extend({
        editor: undefined,
        tour: undefined,
        steps: [],
        tourStorage: window.localStorage,
        init: function (editor) {
            this.editor = editor;
        },
        reset: function () {
            this.tourStorage.removeItem(this.id+'_current_step');
            this.tourStorage.removeItem(this.id+'_end');
            $('.popover.tour').remove();
        },
        start: function () {
            var self = this;
            self.tour = new Tour({
                name: self.id,
                storage: this.tourStorage,
                keyboard: false,
            });
            self.tour.addSteps(_.map(self.steps, function (step) {
               step.title = render('website.tour_title', { title: step.title });
               return step;
            }));
            if (self.canResume()) {
                self.tour.start();
            }
        },
        canResume: function () {
            return this.currentStepIndex() === 0 && !this.tour.ended();
        },
        currentStepIndex: function () {
            return parseInt(this.tourStorage.getItem(this.id+'_current_step'), 10);
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
        start: function () {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you through the firsts steps to build your enterprise class website.",
                    template: render('website.tour_confirm', { confirm: "Tell me more!" }),
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
                    template: render('website.tour_confirm', { confirm: "Got it, now what?" }),
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
                    content: "Click on the title and modify it to fit your needs.",
                    template: render('website.tour_confirm', { confirm: "Done!" }),
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
                    template: render('website.tour_simple'),
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
                    }
                },
                {
                    stepId: 'part-2',
                    orphan: true,
                    title: "Welcome to part 2",
                    content: "Congratulations on your first modifications.",
                    template: render('website.tour_confirm', { confirm: "Thanks :)" }),
                },
                {
                    stepId: 'show-tutorials',
                    element: '#help-menu-button',
                    placement: 'left',
                    title: "Help is always available",
                    content: "You can find more tutorials in the <b>Help</b> menu.",
                    template: render('website.tour_end', { confirm: "See you next time..." }),
                },
            ];
            return this._super();
        },
        canResume: function () {
            var currentStepIndex = this.currentStepIndex();
            var secondPartIndex = this.indexOfStep('part-2');
            return currentStepIndex === 0 || currentStepIndex === secondPartIndex;
        }
    });

    website.EditorBar.include({
        start: function () {
            website.tutorials = {
                basic: new website.EditorBasicTour(this),
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
            website.tutorials.basic.start();
            return this._super();
        },
    });

}());