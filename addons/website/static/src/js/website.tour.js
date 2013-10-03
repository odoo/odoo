(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.tour.xml');

    function render (template, dict)  {
        return openerp.qweb.render(template, dict);
    };

    website.EditorTour = openerp.Class.extend({
        editor: undefined,
        steps: [],
        tourStorage: window.localStorage,
        init: function (editor) {
            this.editor = editor;
            this.tour = new Tour({
                storage: this.tourStorage,
                keyboard: false,
            });
        },
        reset: function () {
            this.tourStorage.removeItem('tour_current_step');
            this.tourStorage.removeItem('tour_end');
            $('.popover.tour').remove();
        },
        start: function () {
            var self = this;
            self.tour.addSteps(_.map(self.steps, function (step) {
               step.title = render('website.tour_title', { title: step.title });
               return step;
            }));
            if (!self.doNotContinue()) {
                self.tour.start();
            }
        },
        doNotContinue: function () {
            return this.currentStepIndex() > 0 || this.tour.ended();
        },
        currentStepIndex: function () {
            return parseInt(this.tourStorage.getItem('tour_current_step'), 10);
        },
        indexOfStep: function (step_id) {
            var index = -1;
            _.each(this.steps, function (step, i) {
               if (step.step_id === step_id) {
                   index = i;
               }
            });
            return index;
        },
        movetoStep: function (step_id) {
            $('.popover.tour').remove();
            var index = this.indexOfStep(step_id);
            if (index > -1) {
                this.tour.goto(index);
            }
        },
        saveStep: function (step_id) {
            var index = this.indexOfStep(step_id);
            this.tourStorage.setItem('tour_current_step', index);
        },
        stop: function () {
            this.tour.end();
        },
    });

    website.EditorBasicTour = website.EditorTour.extend({
        name: "Add a banner to your page",
        start: function () {
            var self = this;
            self.steps = [
                {
                    step_id: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you through the firsts steps to build your enterprise class website.",
                    template: render('website.tour_confirm', { confirm: "Tell me more!" }),
                },
                {
                    step_id: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'right',
                    reflex: true,
                    title: "Edit this page",
                    content: "Every page of your website can be edited. Click the <b>Edit</b> button to modify your homepage.",
                    template: render('website.tour_simple'),
                },
                {
                    step_id: 'show-bar',
                    element: '#website-top-navbar',
                    placement: 'bottom',
                    title: "Editor bar",
                    content: "This is the <b>Editor Bar</b>, use it to modify your website's pages.",
                    template: render('website.tour_confirm', { confirm: "Got it, now what?" }),
                },
                {
                    step_id: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'right',
                    reflex: true,
                    title: "Add a block to your page",
                    content: "Click on the <b>Insert Blocks</b> button to open the block collection.",
                    template: render('website.tour_simple'),
                },
                {
                    step_id: 'drag-banner',
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
                    step_id: 'edit-title',
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
                    step_id: 'customize-banner',
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
                    step_id: 'save-changes',
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
                    step_id: 'part-2',
                    orphan: true,
                    title: "Welcome to part 2",
                    content: "Congratulations on your first modifications.",
                    template: render('website.tour_end', { confirm: "Thanks :)" }),
                },
            ];
            return this._super();
        },
        doNotContinue: function () {
            var currentStepIndex = this.currentStepIndex();
            var secondPartIndex = this.indexOfStep('part-2');
            return currentStepIndex > 0 && currentStepIndex !== secondPartIndex;
        }
    });

    website.EditorBar.include({
        start: function () {
            website.tutorials = {
                basic: new website.EditorBasicTour(this),
            };
            website.tutorials.basic.start();
            return this._super();
        },
    });

}());