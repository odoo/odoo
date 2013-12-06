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
                onHide: function () {
                    window.scrollTo(0, 0);
                }
            });
            this.registerSteps();
        },
        registerSteps: function () {
            var self = this;
            this.tour.addSteps(_.map(this.steps, function (step) {
                step.title = openerp.qweb.render('website.tour_popover_title', { title: step.title });
                if (!step.element) {
                    step.orphan = true;
                }
                if (step.trigger) {
                    if (step.trigger === 'click') {
                        step.triggers = function (callback) {
                            $(step.element).one('click', function () {
                                (callback || self.moveToNextStep).call(self);
                            });
                        };
                    } else if (step.trigger === 'drag') {
                        step.triggers = function (callback) {
                            self.onSnippetDragged(callback || self.moveToNextStep);
                        };
                    } else if (step.trigger && step.trigger.id) {
                        if (step.trigger.emitter && step.trigger.type === 'openerp') {
                            step.triggers = function (callback) {
                                step.trigger.emitter.on(step.trigger.id, self, function customHandler () {
                                    step.trigger.emitter.off(step.trigger.id, customHandler);
                                    (callback || self.moveToNextStep).apply(self, arguments);
                                });
                            };
                        } else {
                            step.triggers = function (callback) {
                                var emitter = step.trigger.emitter || $(step.element);
                                emitter.one(step.trigger.id, function customHandler () {
                                    (callback || self.moveToNextStep).apply(self, arguments);
                                });
                            };
                        }
                    } else if (step.trigger.modal) {
                        step.triggers = function (callback) {
                            var $doc = $(document);
                            function onStop () {
                                if (step.trigger.modal.stopOnClose) {
                                    self.stop();
                                }
                            }
                            $doc.on('hide.bs.modal', onStop);
                            $doc.one('shown.bs.modal', function () {
                                $('.modal button.btn-primary').one('click', function () {
                                    $doc.off('hide.bs.modal', onStop);
                                    self.moveToStep(step.trigger.modal.afterSubmit);
                                });
                                (callback || self.moveToNextStep).call(self);
                            });
                        };
                    }
                }
                step.onShow = (function () {
                    var executed = false;
                    return function () {
                        if (!executed) {
                            _.isFunction(step.onStart) && step.onStart();
                            _.isFunction(step.triggers) && step.triggers();
                            executed = true;
                        }
                    };
                }());
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
            var nextStepIndex = this.currentStepIndex() + 1;
            this.moveToStep(nextStepIndex);
        },
        stop: function () {
            this.tour.end();
        },
        redirect: function (url) {
            url = url || new website.UrlParser(window.location.href);
            var path = (this.startPath && url.pathname !== this.startPath) ? this.startPath : url.pathname;
            var search = url.activateTutorial(this.id);
            var newUrl = path + search;
            window.location.replace(newUrl);
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
            return url.isActive(this.id);
        },
        testUrl: function (pattern) {
            var url = new website.UrlParser(window.location.href);
            return pattern.test(url.pathname+url.search);
        },
        popover: function (options) {
            return openerp.qweb.render('website.tour_popover', options);
        },
        onSnippetDragged: function (callback) {
            var self = this;
            function beginDrag () {
                $('.popover.tour').remove();
                function advance () {
                    if (_.isFunction(callback)) {
                        callback.call(self);
                    }
                }
                $(document.body).one('mouseup', advance);
            }
            $('#website-top-navbar [data-snippet-id].ui-draggable').one('mousedown', beginDrag);
        },
        onSnippetDraggedAdvance: function () {
            onSnippetDragged(self.moveToNextStep);
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
            function generateTrigger (id) {
                return "tutorial."+id+"=true";
            }
            this.activateTutorial = function (id) {
                var urlTrigger = generateTrigger(id);
                var querystring = _.filter(this.search.split('?'), function (str) {
                    return str;
                });
                if (querystring.length > 0) {
                    var queries = _.filter(querystring[0].split("&"), function (query) {
                        return query.indexOf("tutorial.") < 0
                    });
                    queries.push(urlTrigger);
                    return "?"+_.uniq(queries).join("&");
                } else {
                    return "?"+urlTrigger;
                }
            };
            this.isActive = function (id) {
                var urlTrigger = generateTrigger(id);
                return this.search.indexOf(urlTrigger) >= 0;
            };
        },
    });

    var TestConsole = website.TestConsole = {
        tests: []
    };

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
            TestConsole.tests.push({
                id: tour.id,
                run: function runTest () {
                    var actionSteps = _.filter(tour.steps, function (step) {
                       return step.triggers;
                    });
                    var currentIndex = 0;
                    function executeStep (step) {
                       var $element = $(step.element);
                       step.triggers(function () {
                           currentIndex = currentIndex + 1;
                           executeStep(actionSteps[currentIndex]);
                       });
                       $element.click();
                    }
                    executeStep(actionSteps[currentIndex]);
                },
            });
        },
    });

}());
