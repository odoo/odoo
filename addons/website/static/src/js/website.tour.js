(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.tour.xml');

    var tourStorage = window.sessionStorage;

    website.EditorTour = openerp.Class.extend({
        observers: [],
        start: function () {
            var self = this;
            tourStorage.removeItem("tour_current_step");
            tourStorage.removeItem("tour_end");
            var tour = new Tour({
                storage: tourStorage,
            });
            tour.addSteps([
                {
                    element: "button[data-action=edit]",
                    template: openerp.qweb.render("website.tour_simple"),
                    backdrop: true,
                    title: "Switch to edit mode",
                    content: "Press the 'Edit' button to start modifying the page",
                },
                {
                    element: "#oe_rte_toolbar",
                    template: openerp.qweb.render("website.tour_confirm"),
                    placement: "bottom",
                    title: "Edit the page inline",
                    content: "Use rich text editing to make inline modifications to your page",
                },
                {
                    element: "button[data-action=snippet]",
                    template: openerp.qweb.render("website.tour_simple"),
                    backdrop: true,
                    reflex: true,
                    title: "Add a snippet to your page",
                    content: "Click on the 'Insert Blocks' button to open the snippet collection",
                },
                {
                    element: "[data-snippet-id=title]",
                    template: openerp.qweb.render("website.tour_simple"),
                    placement: "right",
                    title: "Choose a title for the page",
                    content: "Drag the 'Title' block to the body of the page and drop it on a purple zone",
                    onShown: function () {
                        $('[data-snippet-id=title]').on('mousedown', function () {
                            function goToNextStep () {
                                self.toEditTitle();
                                $('body').off('mouseup', goToNextStep);
                            }
                            $('body').on('mouseup', goToNextStep);
                        });
                    }
                },
                {
                    element: "#wrap [data-snippet-id=title]",
                    template: openerp.qweb.render("website.tour_confirm"),
                    placement: "bottom",
                    backdrop: true,
                    title: "Modify the title",
                    content: "Click on the title and modify it to fit your needs",
                },
                {
                    element: "button[data-action=save]",
                    template: openerp.qweb.render("website.tour_simple"),
                    backdrop: true,
                    title: "Save your modifications",
                    content: "Click on the 'Save' button to persist your changes to the CMS database",
                    reflex: true,
                    onNext: function () {
                        self.stop();
                    }
                },
            ]);
            tour.start(true);
            self.tour = tour;
            self.tourStorage = tourStorage;
        },
        toBuildingBlocks: function () {
            $('#step-0').remove();
            this.tour.goto(1);
        },
        toEditTitle: function () {
            $('#step-3').remove();
            this.tour.goto(4);
        },
        onDomMutation: function (selector, callback) {
            var target = document.querySelector(selector);
            var observer = new MutationObserver(function(mutations) {
                _.each(mutations, function(mutation) {
                    callback(mutation)
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
            tourStorage.setItem("tour_current_step", 0);
            tourStorage.setItem("tour_end", "yes");
        },
    });

    website.EditorBar.include({
        start: function () {
            if (window.location.href.indexOf("tour=true") >= 0 && tourStorage.getItem("tour_end") !== "yes") {
                var editorTour = new website.EditorTour();
                editorTour.start();
                this.on('rte:ready', this, function () {
                    editorTour.toBuildingBlocks()
                });
            }
            return this._super();
        },
    });

}());