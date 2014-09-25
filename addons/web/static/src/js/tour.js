(function () {
    'use strict';

// raise an error in test mode if openerp don't exist
if (typeof openerp === "undefined") {
    var error = "openerp is undefined"
                + "\nhref: " + window.location.href
                + "\nreferrer: " + document.referrer
                + "\nlocalStorage: " + window.localStorage.getItem("tour");
    if (typeof $ !== "undefined") {
        error += '\n\n' + $("body").html();
    }
    throw new Error(error);
}

var website = openerp.website;

// don't rewrite T in test mode
if (typeof openerp.Tour !== "undefined") {
    return;
}

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

/////////////////////////////////////////////////

var localStorage = window.localStorage;

var Tour = {
    tours: {},
    defaultDelay: 50,
    retryRunningDelay: 1000,
    errorDelay: 5000,
    state: null,
    $element: null,
    timer: null,
    testtimer: null,
    currentTimer: null,
    register: function (tour) {
        if (tour.mode !== "test") tour.mode = "tutorial";
        Tour.tours[tour.id] = tour;
    },
    run: function (tour_id, mode) {
        var tour = Tour.tours[tour_id];
        if (!tour) {
            return Tour.error(null, "Can't run '"+tour_id+"' (tour undefined)");
        }
        Tour.log("Tour '"+tour_id+"' Begin from run method", true);
        var state = Tour.getState();
        if (state) {
             if (state.mode === "test") {
                return Tour.error(false, "An other running tour has been detected all tours are now killed.");
            } else {
                Tour.endTour();
            }
        }
        this.time = new Date().getTime();
        if (tour.path && !window.location.href.match(new RegExp("("+Tour.getLang()+")?"+tour.path+"#?$", "i"))) {
            var href = Tour.getLang()+tour.path;
            Tour.saveState(tour.id, mode || tour.mode, -1, 0);
            $(document).one("ajaxStop", Tour.running);
            window.location.href = href;
        } else {
            Tour.saveState(tour.id, mode || tour.mode, 0, 0);
            Tour.running();
        }
    },
    registerSteps: function (tour, mode) {
        if (tour.register) {
            return;
        }
        tour.register = true;

        for (var index=0, len=tour.steps.length; index<len; index++) {
            var step = tour.steps[index];
            step.id = index;

            if (!step.waitNot && index > 0 && tour.steps[index-1] &&
                tour.steps[index-1].popover && tour.steps[index-1].popover.next) {
                step.waitNot = '.popover.tour.fade.in:visible';
            }
            if (!step.waitFor && index > 0 && tour.steps[index-1].snippet) {
                step.waitFor = '.oe_overlay_options .oe_options:visible';
            }


            var snippet = step.element && step.element.match(/#oe_snippets (.*) \.oe_snippet_thumbnail/);
            if (snippet) {
                step.snippet = snippet[1];
            } else if (step.snippet) {
                step.element = '#oe_snippets '+step.snippet+' .oe_snippet_thumbnail';
            }

            if (!step.element) {
                step.element = "body";
                step.orphan = true;
                step.backdrop = true;
            } else {
                step.popover = step.popover || {};
                step.popover.arrow = true;
            }
        }
        if (tour.steps[index-1] &&
            tour.steps[index-1].popover && tour.steps[index-1].popover.next) {
            var step = {
                _title: "close popover and finish",
                id: index,
                waitNot: '.popover.tour.fade.in:visible'
            };
            tour.steps.push(step);
        }

        // rendering bootstrap tour and popover
        if (mode !== "test") {
            for (var index=0, len=tour.steps.length; index<len; index++) {
                var step = tour.steps[index];
                step._title = step._title || step.title;
                step.title = Tour.popoverTitle(tour, { title: step._title });
                step.template = step.template || Tour.popover( step.popover );
            }
        }
    },
    closePopover: function () {
        if (Tour.$element) {
            Tour.$element.popover('destroy');
            Tour.$element.removeData("tour");
            Tour.$element.removeData("tour-step");
            $(".tour-backdrop").remove();
            $(".popover.tour").remove();
            Tour.$element = null;
        }
    },
    autoTogglePopover: function () {
        var state = Tour.getState();
        var step = state.step;

        if (Tour.$element &&
            Tour.$element.is(":visible") &&
            Tour.$element.data("tour") === state.id &&
            Tour.$element.data("tour-step") === step.id) {
            Tour.repositionPopover();
            return;
        }

        if (step.busy) {
            return;
        }

        Tour.closePopover();

        var $element = $(step.element).first();
        if (!step.element || !$element.size() || !$element.is(":visible")) {
            return;
        }


        Tour.$element = $element;
        $element.data("tour", state.id);
        $element.data("tour-step", step.id);
        $element.popover({
            placement: step.placement || "auto",
            animation: true,
            trigger: "manual",
            title: step.title,
            content: step.content,
            html: true,
            container: "body",
            template: step.template,
            orphan: step.orphan
        }).popover("show");


        var $tip = $element.data("bs.popover").tip();


        // add popover style (orphan, static, backdrop)
        if (step.orphan) {
            $tip.addClass("orphan");
        }

        var node = $element[0];
        var css;
        do {
            css = window.getComputedStyle(node);
            if (!css || css.position == "fixed") {
                $tip.addClass("fixed");
                break;
            }
        } while ((node = node.parentNode) && node !== document);

        if (step.backdrop) {
            $("body").append('<div class="tour-backdrop"></div>');
        }

        if (step.backdrop || $element.parents("#website-top-navbar, .oe_navbar, .modal").size()) {
            $tip.css("z-index", 2010);
        }

        // button click event
        $tip.find("button")
            .one("click", function () {
                step.busy = true;
                if (!$(this).is("[data-role='next']")) {
                    clearTimeout(Tour.timer);
                    Tour.endTour();
                }
                Tour.closePopover();
            });

        Tour.repositionPopover();
    },
    repositionPopover: function() {
        var popover = Tour.$element.data("bs.popover");
        var $tip = Tour.$element.data("bs.popover").tip();

        if (popover.options.orphan) {
            return $tip.css("top", $(window).outerHeight() / 2 - $tip.outerHeight() / 2);
        }

        var offsetBottom, offsetHeight, offsetRight, offsetWidth, originalLeft, originalTop, tipOffset;
        offsetWidth = $tip[0].offsetWidth;
        offsetHeight = $tip[0].offsetHeight;
        tipOffset = $tip.offset();
        originalLeft = tipOffset.left;
        originalTop = tipOffset.top;
        offsetBottom = $(document).outerHeight() - tipOffset.top - $tip.outerHeight();
        if (offsetBottom < 0) {
            tipOffset.top = tipOffset.top + offsetBottom;
        }
        offsetRight = $("html").outerWidth() - tipOffset.left - $tip.outerWidth();
        if (offsetRight < 0) {
            tipOffset.left = tipOffset.left + offsetRight;
        }
        if (tipOffset.top < 0) {
            tipOffset.top = 0;
        }
        if (tipOffset.left < 0) {
            tipOffset.left = 0;
        }
        $tip.offset(tipOffset);
        if (popover.options.placement === "bottom" || popover.options.placement === "top") {
                var left = Tour.$element.offset().left + Tour.$element.outerWidth()/2 - tipOffset.left;
                $tip.find(".arrow").css("left", left ? left + "px" : "");
        } else if (popover.options.placement !== "auto") {
                var top = Tour.$element.offset().top + Tour.$element.outerHeight()/2 - tipOffset.top;
                $tip.find(".arrow").css("top", top ? top + "px" : "");
        }
    },
    _load_template: false,
    load_template: function () {
        // don't need template to use bootstrap Tour in automatic mode
        Tour._load_template = true;
        if (typeof QWeb2 === "undefined") return $.when();
        var def = $.Deferred();
        openerp.qweb.add_template('/web/static/src/xml/website.tour.xml', function(err) {
            if (err) {
                def.reject(err);
            } else {
                def.resolve();
            }
        });
        return def;
    },
    popoverTitle: function (tour, options) {
        return typeof QWeb2 !== "undefined" ? openerp.qweb.render('tour.popover_title', options) : options.title;
    },
    popover: function (options) {
        return typeof QWeb2 !== "undefined" ? openerp.qweb.render('tour.popover', options) : options.title;
    },
    getLang: function () {
        return $("html").attr("lang") ? "/" + $("html").attr("lang").replace(/-/, '_') : "";
    },
    getState: function () {
        var state = JSON.parse(localStorage.getItem("tour") || 'false') || {};
        if (state) { this.time = state.time; }
        var tour_id,mode,step_id;
        if (!state.id && window.location.href.indexOf("#tutorial.") > -1) {
            state = {
                "id": window.location.href.match(/#tutorial\.(.*)=true/)[1],
                "mode": "tutorial",
                "step_id": 0
            };
            window.location.hash = "";
            Tour.log("Tour '"+state.id+"' Begin from url hash");
            Tour.saveState(state.id, state.mode, state.step_id, 0);
        }
        if (!state.id) {
            return;
        }
        state.tour = Tour.tours[state.id];
        state.step = state.tour && state.tour.steps[state.step_id === -1 ? 0 : state.step_id];
        return state;
    },
    log: function (message, add_user) {
        if (add_user) {
            var user = $(".navbar .dropdown:has(>.js_usermenu) a:first, .navbar .oe_topbar_name, .pos .username").text();
            if (!user && $('a[href*="/login"]')) user = 'Public User';
            message += " (" + (user||"").replace(/^\s*|\s*$/g, '') + ")";
        }
        console.log(message);
    },
    logError: function (step, message, all) {
        var state = Tour.getState();
        message += '\ntour: ' + state.id
            + (step ? '\nstep: ' + step.id + ": '" + (step._title || step.title) + "'" : '' )
            + (all ? '\nhref: ' + window.location.href : '' )
            + (all ? '\nreferrer: ' + document.referrer : '' )
            + (step ? '\nelement: ' + Boolean(!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden"))) : '' )
            + (step ? '\nwaitNot: ' + Boolean(!step.waitNot || !$(step.waitNot).size()) : '' )
            + (step ? '\nwaitFor: ' + Boolean(!step.waitFor || $(step.waitFor).size()) : '' )
            + (all ? "\nlocalStorage: " + JSON.stringify(localStorage) : '' )
            + (all ? '\n\n' + $("body").html() : '' );
        Tour.log(message, true);
    },
    error: function (step, message) {
        var state = Tour.getState();
        Tour.logError(step, "Error: " + message, true);
        Tour.endTour();
    },
    lists: function () {
        var tour_ids = [];
        for (var k in Tour.tours) {
            tour_ids.push(k);
        }
        return tour_ids;
    },
    saveState: function (tour_id, mode, step_id, number, wait) {
        localStorage.setItem("tour", JSON.stringify({
            "id":tour_id,
            "mode":mode,
            "step_id":step_id || 0,
            "time": this.time,
            "number": number+1,
            "wait": wait || 0
        }));
    },
    reset: function () {
        var state = Tour.getState();
        if (state && state.tour) {
            for (var k in state.tour.steps) {
                state.tour.steps[k].busy = false;
            }
        }
        localStorage.removeItem("tour");
        clearTimeout(Tour.timer);
        clearTimeout(Tour.testtimer);
        Tour.closePopover();
        Tour.log("Tour reset");
    },
    running: function () {
        var state = Tour.getState();
        if (!state) return;
        else if (state.tour) {
            if (!Tour._load_template) {
                Tour.load_template().then(Tour.running);
                return;
            }
            Tour.log("Tour '"+state.id+"' is running", true);
            Tour.registerSteps(state.tour, state.mode);
            Tour.nextStep();
        } else {
            if (state.mode === "test" && state.wait >= 10) {
                return Tour.error(state.step, "Tour '"+state.id+"' undefined");
            }
            Tour.saveState(state.id, state.mode, state.step_id, state.number-1, state.wait+1);
            Tour.log("Tour '"+state.id+"' wait for running (tour undefined)");
            setTimeout(Tour.running, Tour.retryRunningDelay);
        }
    },
    check: function (step) {
        return (step &&
            (!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden"))) &&
            (!step.waitNot || !$(step.waitNot).size()) &&
            (!step.waitFor || $(step.waitFor).size()));
    },
    waitNextStep: function () {
        var state = Tour.getState();
        var time = new Date().getTime();
        var timer;
        var next = state.step.next ? Tour.search_step(state.step.next) : state.tour.steps[state.step.id+1];
        var overlaps = state.mode === "test" ? Tour.errorDelay : 0;

        window.onbeforeunload = function () {
            clearTimeout(Tour.timer);
            clearTimeout(Tour.testtimer);
        };

        function checkNext () {
            if (!Tour.getState()) return;

            Tour.autoTogglePopover();

            clearTimeout(Tour.timer);
            if (Tour.check(next)) {

                clearTimeout(Tour.currentTimer);
                // use an other timeout for cke dom loading
                Tour.saveState(state.id, state.mode, state.step.id, 0);
                setTimeout(function () {
                    if (state.step.onend && Tour._goto(state.step.onend())) return;
                    Tour.nextStep(next);
                }, Tour.defaultDelay);
                return;

            } else if (!overlaps || new Date().getTime() - time < overlaps) {

                Tour.timer = setTimeout(checkNext, Tour.defaultDelay);
                return;

            } else if(next.onerror) {
                
                Tour.logError(next, "Error: Can't reach the next step (call next step onerror)", false);
                var id = next.onerror();
                if (id) {
                    if (Tour._goto(id)) return;
                    if (id === true) {
                        Tour.nextStep(next);
                        return;
                    }
                }

            }
            
            Tour.error(next, "Can't reach the next step");
            return;

        }
        setTimeout(checkNext, 0);
    },
    search_step: function (id_or_title) {
        var state = Tour.getState();
        if (id_or_title !== undefined) {
            if (isNaN(id_or_title)) {
                for (var k=0; k<state.tour.steps.length; k++) {
                    if (state.tour.steps[k].title === id_or_title || state.tour.steps[k]._title === id_or_title) {
                        return state.tour.steps[k];
                    }
                }
            } else {
                return state.tour.steps[id_or_title];
            }
        }
        return undefined;
    },
    _goto: function (id_or_title) {
        var state = Tour.getState();
        if (!state) return true;
        if (id_or_title === undefined) return false;
        var step = Tour.search_step(id_or_title);
        Tour.saveState(state.id, state.mode, step.id, 0);
        Tour.nextStep(Tour.getState().step);
        return true;
    },
    nextStep: function (step) {
        var state = Tour.getState();

        if (!state) {
            return;
        }

        step = step || state.step;
        var next = state.step.next ? Tour.search_step(state.step.next) : state.tour.steps[step.id+1];

        if (state.mode === "test" && state.number > 3) {
            return Tour.error(next, "Cycling. Can't reach the next step");
        }
        
        Tour.saveState(state.id, state.mode, step.id, state.number);

        if (state.number === 1) {
            Tour.log("Tour '"+state.id+"' Step: '" + (step._title || step.title) + "' (" + (new Date().getTime() - this.time) + "ms)");
        }

        Tour.autoTogglePopover(true);

        // onload a step you can fallback to an other step
        if (step.onload && Tour._goto(step.onload())) {
            return;
        }

        if (state.mode === "test") {
            setTimeout(function () {
                Tour.autoNextStep(state.tour, step);
                if (next && Tour.getState()) {
                    Tour.waitNextStep();
                }
            }, step.wait || Tour.defaultDelay);
        } else if (next) {
            setTimeout(Tour.waitNextStep, next.wait || 0);
        }
        if (!next) {
            Tour.endTour();
        }
    },
    endTour: function () {
        var state = Tour.getState();
        var test = state.step && state.step.id >= state.tour.steps.length-1;
        Tour.reset();
        if (test) {
            Tour.log("Tour '"+state.id+"' finish: ok");
            Tour.log('ok');
        } else {
            Tour.log("Tour '"+state.id+"' finish: error");
            Tour.log('error');
        }
    },
    autoNextStep: function (tour, step) {
        clearTimeout(Tour.testtimer);

        function autoStep () {
            if (!Tour.getState()) return;

            if (!step) return;

            if (step.autoComplete) {
                step.autoComplete(tour);
            }

            $(".popover.tour [data-role='next']").click();

            var $element = $(step.element);
            if (!$element.size()) return;

            if (step.snippet) {

                Tour.autoDragAndDropSnippet($element);
            
            } else if ($element.is(":visible")) {

                $element.trigger($.Event("mouseenter", { srcElement: $element[0] }));
                $element.trigger($.Event("mousedown", { srcElement: $element[0] }));
        
                var evt = document.createEvent("MouseEvents");
                evt.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                $element[0].dispatchEvent(evt);

                // trigger after for step like: mouseenter, next step click on button display with mouseenter
                setTimeout(function () {
                    if (!Tour.getState()) return;
                    $element.trigger($.Event("mouseup", { srcElement: $element[0] }));
                    $element.trigger($.Event("mouseleave", { srcElement: $element[0] }));
                }, 1000);
            }
            if (step.sampleText) {
            
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
                    if (!Tour.getState()) return;
                    $element.trigger($.Event("keyup", { srcElement: $element }));
                    $element.trigger($.Event("change", { srcElement: $element }));
                }, self.defaultDelay<<1);
            
            }
        }
        Tour.testtimer = setTimeout(autoStep, 0);
    },
    autoDragAndDropSnippet: function (selector) {
        var $thumbnail = $(selector).first();
        var thumbnailPosition = $thumbnail.position();
        $thumbnail.trigger($.Event("mousedown", { which: 1, pageX: thumbnailPosition.left, pageY: thumbnailPosition.top }));
        $thumbnail.trigger($.Event("mousemove", { which: 1, pageX: document.body.scrollWidth/2, pageY: document.body.scrollHeight/2 }));
        var $dropZone = $(".oe_drop_zone").first();
        var dropPosition = $dropZone.position();
        $dropZone.trigger($.Event("mouseup", { which: 1, pageX: dropPosition.left, pageY: dropPosition.top }));
    }
};
openerp.Tour = Tour;

/////////////////////////////////////////////////

$(document).ready(Tour.running);

}());
