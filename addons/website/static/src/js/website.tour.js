(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.tour.xml');

    website.Tour = openerp.Class.extend({
        tour: undefined,
        steps: [],
        tourStorage: window.localStorage,
        init: function () {
            this.tour = new Tour({
                name: this.id,
                storage: this.tourStorage,
                keyboard: false,
                template: this.popover(),
            });
            this.tour.addSteps(_.map(this.steps, function (step) {
               step.title = openerp.qweb.render('website.tour_popover_title', { title: step.title });
               return step;
            }));
        },
        reset: function () {
            this.tourStorage.removeItem(this.id+'_current_step');
            this.tourStorage.removeItem(this.id+'_end');
            this.tour._current = 0;
            $('.popover.tour').remove();
        },
        start: function () {
            if (this.resume() || ((this.currentStepIndex() === 0) && !this.tour.ended())) {
                this.tour.start();
            }
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
        isCurrentStep: function (stepId) {
            return this.currentStepIndex() === this.indexOfStep(stepId);
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
        redirect: function (url) {
            url = url || new website.UrlParser(window.location.href);
            if (this.startPath && url.pathname !== this.startPath) {
                var newUrl = this.startPath + (url.search ? (url.search + "&") : "?") + this.id + "=true"
                window.location.replace(newUrl);
            }
        },
        resume: function () {
            // Override if necessary
            return this.currentStepIndex() === 0;
        },
        trigger: function (url) {
            // Override if necessary
            url = url || new website.UrlParser(window.location.href);
            var urlTrigger = this.id + "=true";
            return url.search.indexOf(urlTrigger) >= 0;
        },
        testUrl: function (pattern) {
            var url = new website.UrlParser(window.location.href);
            return pattern.test(url.pathname+url.search);
        },
        popover: function (options) {
            return openerp.qweb.render('website.tour_popover', options);
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
            this.hash = a.hash;
        },
    });

    website.EditorBar.include({
        tours: [],
        start: function () {
            $('.tour-backdrop').click(function (e) {
                e.stopImmediatePropagation();
                e.preventDefault();
            });
            var url = new website.UrlParser(window.location.href);
            var menu = $('#help-menu');
            _.each(this.tours, function (tour) {
                var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
                $menuItem.click(function () {
                    tour.redirect(url);
                    tour.reset();
                    tour.start();
                });
                menu.append($menuItem);
                if (tour.trigger()) {
                    tour.start();
                }
            });
            return this._super();
        },
        registerTour: function (tour) {
            this.tours.push(tour);
        },
    });

}());
