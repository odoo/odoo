(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.tour.xml');

    website.tour = {
        render: function render (template, dict)  {
            return openerp.qweb.render(template, dict);
        }
    };

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
               step.title = website.tour.render('website.tour_popover_title', { title: step.title });
               return step;
            }));
            // TODO: Disabled until properly implemented
            // this.monkeyPatchTour();
        },
        monkeyPatchTour: function () {
            var self = this;
            // showStep should wait for 'element' to appear instead of moving to the next step
            self.tour.showStep = function (i) {
              var step = self.tour.getStep(i);
              return (function proceed () {
                  if (step.orphan || $(step.element).length > 0) {
                      return Tour.prototype.showStep.call(self.tour, i);
                  } else {
                      setTimeout(proceed, 50);
                  }
              }());
            };
        },
        reset: function () {
            this.tourStorage.removeItem(this.id+'_current_step');
            this.tourStorage.removeItem(this.id+'_end');
            this.tour._current = 0;
            $('.popover.tour').remove();
        },
        start: function () {
            if (this.canResume()) {
                this.tour.start();
            }
        },
        canResume: function () {
            return (this.currentStepIndex() === 0) && !this.tour.ended();
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
            $('.tour-backdrop').click(function (e) {
                e.stopImmediatePropagation();
                e.preventDefault();
            });
            return this._super();
        },
    });

}());
