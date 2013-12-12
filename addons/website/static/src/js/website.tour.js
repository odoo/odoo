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
                if (step.snippet) {
                    step.element = '#oe_snippets div.oe_snippet[data-snippet-id="'+step.snippet+'"] .oe_snippet_thumbnail';
                }
                if (step.trigger) {
                    if (step.trigger === 'click') {
                        step.triggers = function (callback) {
                            $(step.element).one('click', function () {
                                (callback || self.moveToNextStep).apply(self);
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
                                var emitter = _.isString(step.trigger.emitter) ? $(step.trigger.emitter) : (step.trigger.emitter || $(step.element));
                                emitter.on(step.trigger.id, function () {
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
                                (callback || self.moveToNextStep).apply(self);
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
                        callback.apply(self);
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

    var TestConsole = openerp.Class.extend({
        tests: [],
        editor: null,
        init: function (editor) {
            if (!editor) {
                throw new Error("Editor cannot be null or undefined");
            }
            this.editor = editor;
        },
        test: function (id) {
            return _.find(this.tests, function (tour) {
               return tour.id === id;
            });
        },
        snippetSelector: function (snippetId) {
            return '#oe_snippets div.oe_snippet[data-snippet-id="'+snippetId+'"] .oe_snippet_thumbnail';
        },
        snippetThumbnail: function (snippetId) {
            return $(this.snippetSelector(snippetId)).first();
        },
        dragAndDropSnippet: function (snippetId) {
            function actualDragAndDrop ($thumbnail) {
                var thumbnailPosition = $thumbnail.position();
                $thumbnail.trigger($.Event("mousedown", { which: 1, pageX: thumbnailPosition.left, pageY: thumbnailPosition.top }));
                $thumbnail.trigger($.Event("mousemove", { which: 1, pageX: thumbnailPosition.left, pageY: thumbnailPosition.top+500 }));
                var $dropZone = $(".oe_drop_zone").first();
                var dropPosition = $dropZone.position();
                $dropZone.trigger($.Event("mouseup", { which: 1, pageX: dropPosition.left, pageY: dropPosition.top }));
            }
            if (this.snippetThumbnail(snippetId).length === 0) {
                this.editor.on('rte:ready', this, function () {
                    actualDragAndDrop(this.snippetThumbnail(snippetId));
                });
            } else {
                actualDragAndDrop(this.snippetThumbnail(snippetId));
            }
        },
    });

    website.EditorBar.include({
        tours: [],
        init: function () {
            var result = this._super();
            website.TestConsole = new TestConsole(this);
            return result;
        },
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
            var testId = 'test_'+tour.id+'_tour';
            this.tours.push(tour);
            var test = {
                id: tour.id,
                run: function (force) {
                    if (force === true) {
                        this.reset();
                    }
                    var actionSteps = _.filter(tour.steps, function (step) {
                       return step.trigger;
                    });
                    function executeStep (step) {
                        window.localStorage.setItem(testId, step.stepId);
                        step.triggers(function () {
                            var nextStep = actionSteps.shift();
                            if (nextStep) {
                                // Ensure the previous step has been fully propagated
                                setTimeout(function () {
                                    setTimeout(function () {
                                        executeStep(nextStep);
                                    }, 0);
                                }, 0);
                            } else {
                                window.localStorage.removeItem(testId);
                            }
                        });
                        var $element = $(step.element);
                        if (step.snippet && step.trigger === 'drag') {
                            website.TestConsole.dragAndDropSnippet(step.snippet);
                        } else if (step.trigger.id === 'change') {
                            var currentValue = $element.val();
                            var options = $element[0].options;
                            // FIXME: It may be necessary to set a particular value
                            var newValue = _.find(options, function (option) {
                                return option.value !== currentValue;
                            }).value;
                            $element.val(newValue).trigger($.Event("change"));
                        } else {
                            $element.trigger($.Event("click", { srcElement: $element }));
                        }
                    }
                    var url = new website.UrlParser(window.location.href);
                    if (tour.startPath && url.pathname !== tour.startPath) {
                        window.localStorage.setItem(testId, actionSteps[0].stepId);
                        window.location.href = tour.startPath;
                    } else {
                        var lastStepId = window.localStorage.getItem(testId);
                        var currentStep = actionSteps.shift();
                        if (lastStepId) {
                            while (currentStep && lastStepId !== currentStep.stepId) {
                                currentStep = actionSteps.shift();
                            }
                        }
                        setTimeout(function () {
                            executeStep(currentStep);
                        }, 0);
                    }
                },
                reset: function () {
                    window.localStorage.removeItem(testId);
                },
            };
            website.TestConsole.tests.push(test);
            if (window.localStorage.getItem(testId)) {
                test.run();
            }
        },
    });

}());
