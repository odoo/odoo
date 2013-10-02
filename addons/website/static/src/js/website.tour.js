(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.tour.xml');

    website.EditorTour = openerp.Class.extend({
        editor: undefined,
        reset: true,
        observers: [],
        steps: [],
        tourStorage: window.localStorage,
        init: function (editor) {
            this.editor = editor;
            if (this.reset) {
                this.tourStorage.removeItem('tour_current_step');
                this.tourStorage.removeItem('tour_end');
                $('.popover.tour').remove();
            }
            this.tour = new Tour({
                storage: this.tourStorage,
                keyboard: false,
            });
        },
        start: function () {
            var self = this;
            self.tour.addSteps(_.map(self.steps, function (step) {
               step.title = openerp.qweb.render ('website.tour_title', { title: step.title });
               return step;
            }));
            self.tour.start(self.reset);
        },
        movetoStep: function (step_id) {
            $('.popover.tour').remove();
            var index = -1;
            _.each(this.steps, function (step, i) {
               if (step.step_id === step_id) {
                   index = i;
               }
            });
            if (index > -1) {
                this.tour.goto(index);
            }
        },
        onDomMutation: function (selector, callback) {
            var target = document.querySelector(selector);
            var observer = new MutationObserver(function(mutations) {
                _.each(mutations, function(mutation) {
                    callback(mutation);
                });
            });
            var config = {
                attributes: true,
                childList: true,
                characterData: true,
            };
            observer.observe(target, config);
            this.observers.push(observer);
        },
        stop: function () {
            this.tour.end();
            _.each(this.observers, function (observer) {
                observer.disconnect();
            });
        },
    });

    website.EditorBasicTour = website.EditorTour.extend({
        start: function () {
            var self = this;
            self.steps = [
                {
                    step_id: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you through the firsts steps to build your enterprise class website.",
                    template: openerp.qweb.render('website.tour_confirm', { confirm: "Ok, tell me more!" }),
                },
                {
                    step_id: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'right',
                    reflex: true,
                    title: "Edit this page",
                    content: "Every page of your website can be edited. Click the <b>Edit</b> button to modify your homepage.",
                    template: openerp.qweb.render('website.tour_simple'),
                },
                {
                    step_id: 'show-bar',
                    element: '#website-top-navbar',
                    placement: 'bottom',
                    title: "Editor bar",
                    content: "This is the <b>Editor Bar</b>, use it to modify your homepage.",
                    template: openerp.qweb.render('website.tour_confirm', { confirm: "Got it, now what?" }),
                },
                {
                    step_id: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'right',
                    reflex: true,
                    title: "Add a block to your page",
                    content: "Click on the <b>Insert Blocks</b> button to open the block collection.",
                    template: openerp.qweb.render('website.tour_simple'),
                },
                {
                    step_id: 'drag-banner',
                    element: '[data-snippet-id=carousel]',
                    placement: 'bottom',
                    title: "Add a banner to your page",
                    content: "Drag the <b>Banner</b> block to the body of the page and drop it on a purple zone.",
                    template: openerp.qweb.render('website.tour_simple'),
                    onShown: function () {
                        function beginDrag () {
                            $('.popover.tour').remove();
                            $('body').off('mousedown', beginDrag);
                            function goToNextStep () {
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
                    element: '#wrap [data-snippet-id=carousel] .carousel-caption',
                    placement: 'top',
                    title: "Change the title",
                    content: "Click on the title and modify it to fit your needs.",
                    template: openerp.qweb.render('website.tour_confirm', { confirm: "Ok, done!" }),
                },
                {
                    step_id: 'save-changes',
                    element: 'button[data-action=save]',
                    placement: 'right',
                    reflex: true,
                    title: "Save your modifications",
                    content: "Click the <b>Save</b> button to apply modifications on your website.",
                    template: openerp.qweb.render('website.tour_simple'),
                    onNext: function () {
                        self.stop();
                    },
                },
            ];
            return this._super();
        },
    });

    website.EditorBar.include({
        start: function () {
            if (window.location.hash.indexOf("tour") >= 0) {
                window.location.hash = "";
                new website.EditorBasicTour(this).start();
            }
            return this._super();
        },
    });

}());