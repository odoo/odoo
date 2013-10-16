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
        name: "Insert a banner",
        init: function (editor) {
            var self = this;
            self.steps = [
                {
                    stepId: 'welcome',
                    orphan: true,
                    backdrop: true,
                    title: "Welcome to your website!",
                    content: "This tutorial will guide you to build your first page. We will start by adding a banner.",
                    template: render('website.tour_popover', { next: "Start Tutorial", end: "Skip It" }),
                },
                {
                    stepId: 'edit-page',
                    element: 'button[data-action=edit]',
                    placement: 'bottom',
                    reflex: true,
                    title: "Edit this page",
                    content: "Every page of your website can be modified through the <i>Edit</i> button.",
                    template: render('website.tour_popover'),
                },
                {
                    stepId: 'add-block',
                    element: 'button[data-action=snippet]',
                    placement: 'bottom',
                    title: "Insert building blocks",
                    content: "To add content in a page, you can insert building blocks.",
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
                    element: '#website-top-navbar [data-snippet-id=carousel].ui-draggable',
                    placement: 'bottom',
                    title: "Drag & Drop a Banner",
                    content: "Drag the <em>Banner</em> block and drop it in your page. <p class='text-muted'>Tip: release the mouse button when you are in a valid zone, with a preview of the banner.</p>",
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
                    title: "Customize banner's text",
                    content: "Click in the text and start editing it. Click continue once it's done.",
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
                    title: "Customize the banner",
                    content: "You can customize components of your page through the <em>Customize</em> menu. Try to change the background of your banner.",
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
                    content: "Once you click on save, your website page is updated.",
                    template: render('website.tour_popover'),
                    onHide: function () {
                        self.saveStep('part-2');
                    },

                },
                {
                    stepId: 'part-2',
                    orphan: true,
                    title: "Congratulation!",
                    content: "Your homepage have been updated. Now, we suggest you to insert others building blocks like texts and images to structure your page.",
                    template: render('website.tour_popover', { next: "Continue" }),
                },
                {
                    stepId: 'show-tutorials',
                    element: '#help-menu-button',
                    placement: 'left',
                    title: "Help is always available",
                    content: "But you can always click here if you want more tutorials.",
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
                });
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
