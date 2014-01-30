(function () {
    'use strict';

    var website = openerp.website;
    website.add_template_file('/website/static/src/xml/website.tour.xml');

    website.Tour = openerp.Class.extend({
        steps: [], // Override
        tourStorage: window.localStorage, // FIXME: will break on iPad in private mode
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
        registerStep: function (step) {
            var self = this;
            step.tour = self;
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
                } else if (step.trigger === 'reload') {
                    step.triggers = function (callback) {
                        var stack = JSON.parse(step.tour.tourStorage.getItem("website-reloads")) || [];
                        var index = stack.indexOf(step.stepId);
                        if (index !== -1) {
                            setTimeout(function () {
                                $(step.element).popover("destroy");
                                setTimeout(function () {
                                    stack.splice(index,1);
                                    (callback || self.moveToNextStep).apply(self);
                                    step.tour.tourStorage.setItem("website-reloads", JSON.stringify(stack));
                                },10);
                            },0);
                        } else {
                            stack.push(step.stepId);
                            step.tour.tourStorage.setItem("website-reloads", JSON.stringify(stack));
                        }
                    };
                } else if (step.trigger === 'drag') {
                    step.triggers = function (callback) {
                        self.onSnippetDragged(callback || self.moveToNextStep);
                    };
                } else if (step.trigger.id) {
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
                            if (!emitter.size()) throw "Emitter is undefined";
                            emitter.on(step.trigger.id, function () {
                                (callback || self.moveToNextStep).apply(self, arguments);
                            });
                        };
                    }
                } else if (step.trigger.url) {
                    step.triggers = function (callback) {
                        var stack = JSON.parse(step.tour.tourStorage.getItem("website-geturls")) || [];
                        var id = step.trigger.url.toString();
                        var index = stack.indexOf(id);
                        if (index !== -1) {
                            var url = new website.UrlParser(window.location.href);
                            var test = typeof step.trigger.url === "string" ?
                                step.trigger.url == url.pathname+url.search :
                                step.trigger.url.test(url.pathname+url.search);
                            if (!test) return;
                            setTimeout(function () {
                                $(step.element).popover("destroy");
                                setTimeout(function () {
                                    stack.splice(index,1);
                                    (callback || self.moveToNextStep).apply(self);
                                    step.tour.tourStorage.setItem("website-geturls", JSON.stringify(stack));
                                },10);
                            },0);
                        } else {
                            stack.push(id);
                            step.tour.tourStorage.setItem("website-geturls", JSON.stringify(stack));
                        }
                        return index !== -1;
                    };
                } else if (step.trigger.modal) {
                    step.triggers = function (callback, auto) {
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
                                if (!callback) {
                                    self.moveToStep(step.trigger.modal.afterSubmit);
                                }
                            });
                            (callback || self.moveToNextStep).apply(self);
                        });
                    };
                } else if (step.trigger === 'ajax') {
                    step.triggers = function (callback) {
                        $( document ).ajaxSuccess(function(event, xhr, settings) {
                            $( document ).unbind('ajaxSuccess');
                            xhr.then(function () {
                                setTimeout(function () {
                                    $(step.element).popover("destroy");
                                    setTimeout(function () {
                                        (callback || self.moveToNextStep).apply(self);
                                    },10);
                                },0);
                            });
                        });
                    };
                } else {
                    step.triggers = function (callback) {
                        var emitter = $(step.element);
                        if (!emitter.size()) throw "Emitter is undefined";
                        var trigger = function () {
                            emitter.off(step.trigger, trigger);
                            (callback || self.moveToNextStep).apply(self, arguments);
                        };
                        emitter.on(step.trigger, trigger);
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
        },
        registerSteps: function () {
            var self = this;
            this.tour.addSteps(_.map(this.steps, function (step) {
                return self.registerStep(step);
            }));
        },
        reset: function () {
            this.tourStorage.removeItem(this.id+'_current_step');
            this.tourStorage.removeItem(this.id+'_end');
            this.tourStorage.removeItem("website-reloads");
            this.tourStorage.removeItem("website-geturls");
            this.tour._current = 0;
            $('.popover.tour').remove();
        },
        start: function () {
            window.Tour.prototype._isOrphan = function(step) {
                return (step.element == null) || !$(step.element).length;
            };
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
                $('.popover.tour').remove();
                self.tour.goto(index);
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
            var path = (this.path && url.pathname !== this.path) ? this.path : url.pathname;
            var search = url.activateTutorial(this.id);
            var newUrl = path + search;
            window.location.replace(newUrl);
        },
        ended: function () {
            return this.tourStorage.getItem(this.id+'_end') === "yes";
        },
        resume: function () {
            // Override if necessary
            return this.tourStorage.getItem(this.id+'_current_step') && !this.ended();
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
            var selector = '#website-top-navbar [data-snippet-id].ui-draggable';
            var beginDrag = function beginDrag () {
                $('.popover.tour').remove();
                var advance = function advance () {
                    if (_.isFunction(callback)) {
                        callback.apply(self);
                    }
                    $(selector).off('mouseup', advance);
                };
                $(document.body).one('mouseup', advance);
                $(selector).off('mousedown', beginDrag);
            };
            $(selector).one('mousedown', beginDrag);
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
        snippetThumbnailExists: function (snippetId) {
            return this.snippetThumbnail(snippetId).length > 0;
        },
        dragAndDropSnippet: function (snippetId) {
            function actualDragAndDrop ($thumbnail) {
                var thumbnailPosition = $thumbnail.position();
                $thumbnail.trigger($.Event("mousedown", { which: 1, pageX: thumbnailPosition.left, pageY: thumbnailPosition.top }));
                $thumbnail.trigger($.Event("mousemove", { which: 1, pageX: document.body.scrollWidth/2, pageY: document.body.scrollHeight/2 }));
                var $dropZone = $(".oe_drop_zone").first();
                var dropPosition = $dropZone.position();
                $dropZone.trigger($.Event("mouseup", { which: 1, pageX: dropPosition.left, pageY: dropPosition.top }));
            }
            if (this.snippetThumbnailExists(snippetId)) {
                actualDragAndDrop(this.snippetThumbnail(snippetId));
            } else {
                this.editor.on('rte:ready', this, function () {
                    actualDragAndDrop(this.snippetThumbnail(snippetId));
                });
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
            var menu = $('#help-menu');
            _.each(this.tours, function (tour) {
                var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
                $menuItem.click(function () {
                    tour.reset();
                    tour.redirect(new website.UrlParser(window.location.href));
                });
                menu.append($menuItem);
                if (tour.trigger()) {
                    setTimeout(function () {
                        setTimeout(function () {
                            tour.start();
                        },100);
                    },0);
                }
            });
            return this._super();
        },
        registerTour: function (tour) {
            var self = this;
            var testId = 'test_'+tour.id+'_tour';
            this.tours.push(tour);
            var defaultDelay = 250; //ms
            var overlapsCrash;
            var test = {
                id: tour.id,
                run: function (force) {
                    if (force === true) {
                        this.reset();
                        tour.reset();
                    }
                    var actionSteps = _.filter(tour.steps, function (step) {
                       return step.trigger || step.triggers || step.sampleText;
                    });
                    window.onbeforeunload = function () {
                        clearTimeout(overlapsCrash);
                    };
                    function throwError (message) {
                        console.log(tour.tourStorage.getItem("test-report"));
                        test.reset();
                        tour.reset();
                        throw message;
                    }
                    function initReport () {
                        // set last time for report
                        if (!tour.tourStorage.getItem("test-last-time")) {
                            tour.tourStorage.setItem("test-last-time", new Date().getTime());
                        }
                    }
                    function setReport (step) {
                        var report = JSON.parse(tour.tourStorage.getItem("test-report")) || {};
                        report[step.stepId] = (new Date().getTime() - tour.tourStorage.getItem("test-last-time")) + " ms";
                        tour.tourStorage.setItem("test-report", JSON.stringify(report));
                    }
                    function testCycling (step) {
                        var lastStep = tour.tourStorage.getItem(testId);
                        var tryStep = lastStep != step.stepId ? 0 : (+(tour.tourStorage.getItem("test-last-"+testId) || 0) + 1);
                        tour.tourStorage.setItem("test-last-"+testId, tryStep);
                        if (tryStep > 2) {
                            throwError("Test: '" + testId + "' cycling step: '" + step.stepId + "'");
                        }
                        return tryStep;
                    }
                    function getDelay (step) {
                        return step.delay || defaultDelay;
                    }
                    function executeStep (step) {
                        if (testCycling(step) === 0) initReport();

                        tour.tourStorage.setItem(testId, step.stepId);

                        var delay = getDelay (step);

                        overlapsCrash = setTimeout(function () {
                            throwError("Test: '" + testId + "' can't resolve step: '" + step.stepId + "'");
                        }, delay + 3000);


                        var _next = false;
                        tour.tourStorage.setItem(testId, step.stepId);
                        function next () {
                            _next = true;
                            clearTimeout(overlapsCrash);

                            setReport(step);

                            var nextStep = actionSteps.shift();

                            if (nextStep) {
                                executeStep(nextStep);
                            } else {
                                tour.tourStorage.removeItem(testId);
                            }
                        }

                        setTimeout(function () {
                            var $element = $(step.element);

                            var flag = step.triggers && (!step.trigger || !step.trigger.modal);
                            if (flag) {
                                try {
                                    step.triggers(next, true);
                                } catch (e) {
                                    throwError(e);
                                }
                            }
                            if ((step.trigger === 'reload' || (step.trigger && step.trigger.url)) && _next) return;

                            if (step.snippet && step.trigger === 'drag') {
                                website.TestConsole.dragAndDropSnippet(step.snippet);
                            } else if (step.trigger && step.trigger.id === 'change') {
                                $element.trigger($.Event("change", { srcElement: $element }));
                            } else if (step.sampleText) {
                                $element.trigger($.Event("keydown", { srcElement: $element }));
                                if ($element.is("select") || $element.is("input") ) {
                                    $element.val(step.sampleText);
                                } else {
                                    $element.html(step.sampleText);
                                }
                                $element.trigger($.Event("change", { srcElement: $element }));
                                $element.trigger($.Event("keyup", { srcElement: $element }));
                            } else if ($element.is(":visible")) { // Click by default
                                $element.trigger($.Event("mouseenter", { srcElement: $element }));
                                $element.trigger($.Event("mousedown", { srcElement: $element }));
                                var evt = document.createEvent("MouseEvents");
                                evt.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                                $element[0].dispatchEvent(evt);
                                $element.trigger($.Event("mouseup", { srcElement: $element }));
                                $element.trigger($.Event("mouseleave", { srcElement: $element }));

                                // trigger after for step like: mouseenter, next step click on button display with mouseenter
                                $element.trigger($.Event("mouseenter", { srcElement: $element }));
                            }
                            if (!flag) next();
                        },delay);
                    }
                    var url = new website.UrlParser(window.location.href);
                    if (tour.path && url.pathname !== tour.path && !tour.tourStorage.getItem(testId)) {
                        tour.tourStorage.setItem(testId, actionSteps[0].stepId);
                        window.location.href = tour.path;
                    } else {
                        var lastStepId = tour.tourStorage.getItem(testId);
                        var currentStep = actionSteps.shift();
                        if (lastStepId) {
                            while (currentStep && lastStepId !== currentStep.stepId) {
                                currentStep = actionSteps.shift();
                            }
                        }
                        if (currentStep.snippet && $(currentStep.element).length === 0) {
                            self.on('rte:ready', this, function () {
                                executeStep(currentStep);
                            });
                        } else {
                            setTimeout(function () {
                                executeStep(currentStep);
                            }, 500);
                        }
                    }
                },
                reset: function () {
                    tour.tourStorage.removeItem(testId);
                    tour.tourStorage.removeItem("test-report");
                    for (var k in tour.tourStorage) {
                        if (tour.tourStorage[k].indexOf("test-last")) {
                            tour.tourStorage.removeItem(k);
                        }
                    }
                },
            };
            website.TestConsole.tests.push(test);
            if (window.localStorage.getItem(testId)) {
                test.run();
            }
        },
    });

}());
