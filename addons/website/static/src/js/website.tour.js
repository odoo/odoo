(function () {
    'use strict';

    var website = openerp.website;
    website.templates.push('/website/static/src/xml/website.tour.xml');

    function render (template, dict)  {
        return openerp.qweb.render(template, dict);
    }

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
               step.title = render('website.tour_popover_title', { title: step.title });
               return step;
            }));
            this.monkeyPatchTour();
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

    website.EditorBasicTour = website.EditorTour.extend({
        id: 'add_banner_tour',
        name: "How to add a banner",
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you to build your website.<br>Let's start by the banner!",
                    template: render('website.tour_popover', { next: "Start", end: "Close" }),
                },
                {
                    stepId: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'bottom',
                    reflex: true,
                    title: "Edit this page",
                    content: "You are in your website homepage.<br>Click here to edit it.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Shows Building Blocks",
                    content: "Make the home page more attractive with a banner.<br>Click here to see available building blocks.",
                    template: render('website.tour_popover'),
                    onShow: function () {
                        function refreshAddBlockStep () {
                            self.tour.showStep(self.indexOfStep('add-block'));
                            editor.off('rte:ready', editor, refreshAddBlockStep);
                        }
                        editor.on('rte:ready', editor, refreshAddBlockStep);
                        $('button[data-action=snippet]').click(function () {
                            self.movetoStep('drag-banner');
                        });
                    }
                },
                {
                    stepId: 'drag-banner',
                    element: '#website-top-navbar [data-snippet-id=carousel]',
                    placement: 'bottom',
                    title: "Drag & Drop a Banner",
                    content: "Drag the <em>Banner</em> block and drop it to the top of your page.",
                    template: render('website.tour_popover'),
                    onShow: function () {
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
                    placement: 'left',
                    title: "Set your Banner text",
                    content: "Click in the text to edit it.<br>Select the text to change the look thanks to the top menu bar.",
                    template: render('website.tour_popover', { next: "Continue" }),
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
                    title: "Customize your new Banner style",
                    content: "Click on <em>Customize</em> and change the background of your banner.<br>If your are satisfied with the current background, just click <em>Continue</em>.",
                    template: render('website.tour_popover', { next: "Continue" }),
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
                    content: "Click here to save the content of your website.",
                    template: render('website.tour_popover'),
                    onHide: function () {
                        self.saveStep('part-2');
                    },

                },
                {
                    stepId: 'part-2',
                    orphan: true,
                    backdrop: true,
                    title: "Congratutaltions!",
                    content: "Congratulations on your first modifications.",
                    template: render('website.tour_popover', { next: "OK" }),
                },
                {
                    stepId: 'show-tutorials',
                    element: '#help-menu-button',
                    placement: 'left',
                    title: "Help is always available",
                    content: "You can find more tutorials in the <em>Help</em> menu.",
                    template: render('website.tour_popover', { end: "Close" }),
                },
            ];
            return this._super();
        },
        startOfPart2: function () {
            var currentStepIndex = this.currentStepIndex();
            var secondPartIndex = this.indexOfStep('part-2');
            var showTutorialsIndex = this.indexOfStep('show-tutorials');
            return (currentStepIndex === secondPartIndex || currentStepIndex === showTutorialsIndex) && !this.tour.ended();
        },
        canResume: function () {
            return this.startOfPart2() || this._super();
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
            var url = new website.UrlParser(window.location.href);
            if (url.search.indexOf('?tutorial=true') === 0 || website.tutorials.basic.startOfPart2()) {
                website.tutorials.basic.start();
            }
            $('.tour-backdrop').click(function (e) {
                e.stopImmediatePropagation();
                e.preventDefault();
            });
            return this._super();
        },
    });

}());