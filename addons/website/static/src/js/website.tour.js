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
            this.registerSteps();
        },
        registerSteps: function () {
            var self = this;
            this.tour.addSteps(_.map(this.steps, function (step) {
               step.title = openerp.qweb.render('website.tour_popover_title', { title: step.title });
               if (step.modal) {
                   step.onShow = function () {
                        var $doc = $(document);
                        function onStop () {
                            if (step.modal.stopOnClose) {
                                self.stop();
                            }
                        }
                        $doc.on('hide.bs.modal', onStop);
                        $doc.one('shown.bs.modal', function () {
                            $('.modal button.btn-primary').one('click', function () {
                                $doc.off('hide.bs.modal', onStop);
                                self.moveToStep(step.modal.afterSubmit);
                            });
                            self.moveToNextStep();
                        });
                    };
               } else {
                   step.onShow = step.triggers;
               }
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
        moveToStep: function (step) {
            var index = _.isNumber(step) ? step : this.indexOfStep(step);
            if (index >= this.steps.length) {
                this.stop();
            } else if (index >= 0) {
                var self = this;
                setTimeout(function () {
                    $('.popover.tour').remove();
                    self.tour.goto(index);
                }, 0);
            }
        },
        moveToNextStep: function () {
            this.moveToStep(this.currentStepIndex() + 1);
        },
        stop: function () {
            this.tour.end();
        },
        redirect: function (url) {
            url = url || new website.UrlParser(window.location.href);
            if (this.startPath && url.pathname !== this.startPath) {
                var newUrl = this.startPath + (url.search ? (url.search + "&") : "?") + this.id + "=true";
                window.location.replace(newUrl);
            }
        },
        ended: function () {
            return this.tourStorage.getItem(this.id+'_end') === "yes";
        },
        resume: function () {
            // Override if necessary
            return !this.ended();
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
        onSnippetDraggedAdvance: function (snippetId, stepId) {
            var self = this;
            function beginDrag () {
                $('.popover.tour').remove();
                function advance () {
                    if (stepId) {
                        self.moveToStep(stepId);
                    } else {
                        self.moveToNextStep();
                    }
                }
                $(document.body).one('mouseup', advance);
            }
            $('#website-top-navbar [data-snippet-id].ui-draggable').one('mousedown', beginDrag);
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
