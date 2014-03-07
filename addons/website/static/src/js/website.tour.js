(function () {
    'use strict';

var website = openerp.website;

if (typeof QWeb2 !== "undefined")
website.add_template_file('/website/static/src/xml/website.tour.xml');

if (website.EditorBar)
website.EditorBar.include({
    tours: [],
    start: function () {
        var self = this;
        var menu = $('#help-menu');
        _.each(this.tours, function (tour) {
            var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
            $menuItem.click(function () {
                tour.reset();
                tour.run();
            });
            menu.append($menuItem);
        });
        return this._super();
    },
    registerTour: function (tour) {
        website.Tour.add(tour);
        this.tours.push(tour);
    }
});


/////////////////////////////////////////////////


/* jQuery selector to match exact text inside an element
 *  :containsExact()     - case insensitive
 *  :containsExactCase() - case sensitive
 *  :containsRegex()     - set by user ( use: $(el).find(':containsRegex(/(red|blue|yellow)/gi)') )
 */
$.extend($.expr[':'],{
    containsExact: function(a,i,m){
        return $.trim(a.innerHTML.toLowerCase()) === m[3].toLowerCase();
    },
    containsExactCase: function(a,i,m){
        return $.trim(a.innerHTML) === m[3];
    },
    // Note all escaped characters need to be double escaped
    // inside of the containsRegex, so "\(" needs to be "\\("
    containsRegex: function(a,i,m){
        var regreg =  /^\/((?:\\\/|[^\/])+)\/([mig]{0,3})$/,
        reg = regreg.exec(m[3]);
        return reg ? new RegExp(reg[1], reg[2]).test($.trim(a.innerHTML)) : false;
    }
});
$.ajaxSetup({
    beforeSend:function(){
        $.ajaxBusy = ($.ajaxBusy|0) + 1;
    },
    complete:function(){
        $.ajaxBusy--;
    }
});

website.Tour = openerp.Class.extend({
    steps: [],
    defaultDelay: 50, //ms
    defaultOverLaps: 5000, //ms
    localStorage: window.localStorage,
    init: function () {},

    run: function (automatic) {
        this.reset();

        for (var k in this.localStorage) {
            if (!k.indexOf("tour-") && k.indexOf("-test") > -1) return;
        }

        website.Tour.busy = true;

        if (automatic) {
            this.localStorage.setItem("tour-"+this.id+"-test-automatic", true);
        } else {
            this.localStorage.removeItem("tour-"+this.id+"-test-automatic");
        }
        this.automatic = automatic;

        if (this.path) {
            // redirect to begin of the tour in function of the language
            if (!this.testUrl(this.path+"(#.*)?$")) {
                var path = this.path.split('#');
                window.location.href = "/"+this.getLang()+path[0] + "#tutorial."+this.id+"=true&" + path.slice(1, path.length).join("#");
                return;
            }
        }

        var self = this;
        this.localStorage.setItem("tour-"+this.id+"-test", 0);
        website.Tour.waitReady.call(this, function () {self._running();});
    },
    running: function () {
        var self = this;
        if (+this.localStorage.getItem("tour-"+this.id+"-test") >= this.steps.length-1) {
            this.endTour();
            return;
        }

        if (website.Tour.is_busy()) return;

        // launch tour with url
        this.checkRunningUrl();

        // mark tour as busy (only one test running)
        if (this.localStorage.getItem("tour-"+this.id+"-test") != null) {
            website.Tour.busy = true;
            this.automatic = !!this.localStorage.getItem("tour-"+this.id+"-test-automatic");
        }

        if (!this.testPathUrl()) {
            if (this.automatic) {
                this.timer = setTimeout(function () {
                    self.reset();
                    throw new Error("Wrong url for running " + self.id
                        + '\ntestPath: ' + self.testPath
                        + '\nhref: ' + window.location.href
                        + "\nreferrer: " + document.referrer
                    );
                },this.defaultOverLaps);
            }
            return;
        }

        var self = this;
        website.Tour.waitReady.call(this, function () {self._running();});
    },
    _running: function () {
        var stepId = this.localStorage.getItem("tour-"+this.id+"-test");

        if (stepId != null) {
            this.registerTour();
            this.nextStep(stepId,  this.automatic ? this.autoNextStep : null, this.automatic ? this.defaultOverLaps : null);
        }
    },

    reset: function () {
        website.Tour.busy = false;
        for (var k in this.steps) {
            this.steps[k].busy = false;
        }
        clearTimeout(self.timer);
        clearTimeout(self.testtimer);

        for (var k in this.localStorage) {
            if (!k.indexOf("tour-") || !k.indexOf(this.id)) {
                this.localStorage.removeItem(k);
            }
        }

        $('.popover.tour').remove();
    },

    getLang: function () {
        return $("html").attr("lang").replace(/-/, '_');
    },
    testUrl: function (url) {
        return new RegExp("(/"+this.getLang()+")?"+url, "i").test(window.location.href);
    },
    testPathUrl: function () {
        if (!this.testPath || this.testUrl(this.testPath)) return true;
    },
    checkRunningUrl: function () {
        if (window.location.hash.indexOf("tutorial."+this.id+"=true") > -1) {
            this.localStorage.setItem("tour-"+this.id+"-test", 0);
            window.location.hash = window.location.hash.replace(/tutorial.+=true&?/, '');
        }
    },

    registerTour: function () {
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
        for (var index=0, len=this.steps.length; index<len; index++) {
            var step = this.steps[index];
            step.stepId = step.stepId || ""+index;

            if (!step.waitNot && index > 0 && this.steps[index-1] &&
                this.steps[index-1].popover && this.steps[index-1].popover.next) {
                step.waitNot = '.popover.tour:visible';
            }
            if (!step.waitFor && index > 0 && this.steps[index-1].snippet) {
                step.waitFor = '.oe_overlay_options .oe_options:visible';
            }

            step._title = step._title || step.title;
            step.title = this.popoverTitle({ title: step._title });
            step.template = step.template || this.popover( step.popover );

            if (!step.element) step.orphan = true;
            if (step.snippet) {
                step.element = '#oe_snippets div.oe_snippet[data-snippet-id="'+step.snippet+'"] .oe_snippet_thumbnail';
            }

        }

        if (this.steps[index-1] &&
            this.steps[index-1].popover && this.steps[index-1].popover.next) {
            var step = {
                stepId:    ""+index,
                waitNot:   '.popover.tour:visible'
            };
            this.steps.push(step);
        }

        this.tour.addSteps(this.steps);
    },

    popoverTitle: function (options) {
        try {
            return openerp.qweb.render('website.tour_popover_title', options);
        } catch (e) {
            if (!this.automatic) throw e;
            return options.title;
        }
    },
    popover: function (options) {
        try {
            return openerp.qweb.render('website.tour_popover', options);
        } catch (e) {
            if (!this.automatic) throw e;
            return "";
        }
    },

    timer: null,
    testtimer: null,
    check: function (step) {
        return (step &&
            (!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden"))) &&
            (!step.waitNot || !$(step.waitNot).size()) &&
            (!step.waitFor || $(step.waitFor).size()));
    },
    waitNextStep: function (step, callback, overlaps) {
        var self = this;
        var time = new Date().getTime();
        var timer;

        window.onbeforeunload = function () {
            clearTimeout(self.timer);
            clearTimeout(self.testtimer);
        };

        // check popover activity
        $(".popover.tour button")
            .off()
            .on("click", function () {
                $(".popover.tour").remove();
                if (step.busy) return;
                if (!$(this).is("[data-role='next']")) {
                    clearTimeout(self.timer);
                    step.busy = true;
                    self.tour.end();
                    self.endTour(callback);
                }
            });

        function checkNext () {
            clearTimeout(self.timer);
            if (step.busy) return;
            if (self.check(step)) {
                step.busy = true;
                // use an other timeout for cke dom loading
                setTimeout(function () {
                    self.nextStep(step.stepId, callback, overlaps);
                }, self.defaultDelay);
            } else if (!overlaps || new Date().getTime() - time < overlaps) {
                if (self.current.element) {
                    var $popover = $(".popover.tour");
                    if(!$(self.current.element).is(":visible")) {
                        $popover.data("hide", true).fadeOut(300);
                    } else if($popover.data("hide")) {
                        $popover.data("hide", false).fadeIn(150);
                    }
                }
                self.timer = setTimeout(checkNext, self.defaultDelay);
            } else {
                self.reset();
                throw new Error("Time overlaps to arrive to step " + step.stepId + ": '" + step._title + "'"
                    + '\nelement: ' + Boolean(!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden")))
                    + '\nwaitNot: ' + Boolean(!step.waitNot || !$(step.waitNot).size())
                    + '\nwaitFor: ' + Boolean(!step.waitFor || $(step.waitFor).size())
                    + '\n\n' + $("body").html()
                );
            }
        }
        checkNext();
    },
    step: function (stepId) {
        var steps = this.steps.slice(0,this.steps.length),
            step;
        while (step = steps.shift()) {
            if (!stepId || step.stepId === stepId)
                return step;
        }
        return null;
    },
    next: function (stepId) {
        var steps = this.steps.slice(0,this.steps.length),
            step, next, index=0;
        while (step = steps.shift()) {
            if (!stepId || step.stepId === stepId) {
                // clear popover (fix for boostrap tour if the element is removed before destroy popover)
                $(".popover.tour").remove();
                // go to step in bootstrap tour
                this.tour.goto(index);
                if (step.onload) step.onload();
                next = steps.shift();
                break;
            }
            index++;
        }
        return next;
    },
    nextStep: function (stepId, callback, overlaps) {
        var self = this;
        if (!this.localStorage.getItem("tour-"+this.id+"-test")) return;

        this.localStorage.setItem("tour-"+this.id+"-test", stepId || 0);

        this.current = this.step(stepId);
        var next = this.next(stepId);

        if (next) {
            setTimeout(function () {
                    self.waitNextStep(next, callback, overlaps);
                    if (callback) setTimeout(function(){callback.call(self, next);}, self.defaultDelay);
            }, next && next.wait || 0);
        } else {
            this.endTour();
        }
    },
    endTour: function () {
        if (parseInt(this.localStorage.getItem("tour-"+this.id+"-test"),10) >= this.steps.length-1) {
            console.log('{ "event": "success" }');
        } else {
            console.log('{ "event": "canceled" }');
        }
        this.reset();
    },
    autoNextStep: function () {
        var self = this;
        clearTimeout(self.testtimer);

        function autoStep () {
            var step = self.current;
            if (!step) return;

            if (step.autoComplete) {
                step.autoComplete(tour);
            }

            var $popover = $(".popover.tour");
            if ($popover.find("button[data-role='next']:visible").size()) {
                $popover.find("button[data-role='next']:visible").click();
                $popover.remove();
            }

            var $element = $(step.element);
            if (!$element.size()) return;

            if (step.snippet) {
            
                var selector = '#oe_snippets div.oe_snippet[data-snippet-id="'+step.snippet+'"] .oe_snippet_thumbnail';
                self.autoDragAndDropSnippet(selector);
            
            } else if (step.element.match(/#oe_snippets .* \.oe_snippet_thumbnail/)) {
            
                self.autoDragAndDropSnippet($element);
            
            } else if (step.sampleText) {
            
                $element.trigger($.Event("keydown", { srcElement: $element }));
                if ($element.is("input") ) {
                    $element.val(step.sampleText);
                } if ($element.is("select")) {
                    $element.find("[value='"+step.sampleText+"'], option:contains('"+step.sampleText+"')").attr("selected", true);
                    $element.val(step.sampleText);
                } else {
                    $element.html(step.sampleText);
                }
                setTimeout(function () {
                    $element.trigger($.Event("keyup", { srcElement: $element }));
                    $element.trigger($.Event("change", { srcElement: $element }));
                }, self.defaultDelay<<1);
            
            } else if ($element.is(":visible")) {

                $element.trigger($.Event("mouseenter", { srcElement: $element[0] }));
                $element.trigger($.Event("mousedown", { srcElement: $element[0] }));
        
                var evt = document.createEvent("MouseEvents");
                evt.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                $element[0].dispatchEvent(evt);

                // trigger after for step like: mouseenter, next step click on button display with mouseenter
                setTimeout(function () {
                    $element.trigger($.Event("mouseup", { srcElement: $element[0] }));
                    $element.trigger($.Event("mouseleave", { srcElement: $element[0] }));
                }, 1000);
            }
        }
        self.testtimer = setTimeout(autoStep, 100);
    },
    autoDragAndDropSnippet: function (selector) {
        var $thumbnail = $(selector).first();
        var thumbnailPosition = $thumbnail.position();
        $thumbnail.trigger($.Event("mousedown", { which: 1, pageX: thumbnailPosition.left, pageY: thumbnailPosition.top }));
        $thumbnail.trigger($.Event("mousemove", { which: 1, pageX: document.body.scrollWidth/2, pageY: document.body.scrollHeight/2 }));
        var $dropZone = $(".oe_drop_zone").first();
        var dropPosition = $dropZone.position();
        $dropZone.trigger($.Event("mouseup", { which: 1, pageX: dropPosition.left, pageY: dropPosition.top }));
    },

});


website.Tour.tours = {};
website.Tour.busy = false;
website.Tour.add = function (tour) {
    website.Tour.waitReady(function () {
        tour = tour.id ? tour : new tour();
        if (!website.Tour.tours[tour.id]) {
            website.Tour.tours[tour.id] = tour;
            tour.running();
        }
    });
};
website.Tour.get = function (id) {
    return website.Tour.tours[id];
};
website.Tour.each = function (callback) {
    website.Tour.waitReady(function () {
        for (var k in website.Tour.tours) {
            callback.call(website.Tour.tours[k]);
        }
    });
};
website.Tour.waitReady = function (callback) {
    var self = this;
    $(document).ready(function () {
        if ($.ajaxBusy) {
            $(document).ajaxStop(function() {
                setTimeout(function () {
                    callback.call(self);
                },0);
            });
        }
        else {
            setTimeout(function () {
                callback.call(self);
            },0);
        }
    });
};
website.Tour.run_test = function (id) {
    website.Tour.waitReady(function () {
        if (!website.Tour.is_busy()) {
            website.Tour.tours[id].run(true);
        }
    });
};
website.Tour.is_busy = function () {
    for (var k in this.localStorage) {
        if (!k.indexOf("tour-")) {
            return k;
        }
    }
    return website.Tour.busy;
};


}());
