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

var website = window.openerp.website;

// don't rewrite T in test mode
if (typeof website.Tour !== "undefined") {
    return;
}

// don't need template to use bootstrap Tour in automatic mode
if (typeof QWeb2 !== "undefined") {
    website.add_template_file('/website/static/src/xml/website.tour.xml');
}

if (website.EditorBar) {
    website.EditorBar.include({
        tours: [],
        start: function () {
            var self = this;
            var menu = $('#help-menu');
            _.each(T.tours, function (tour) {
                if (tour.mode === "test") {
                    return;
                }
                var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
                $menuItem.click(function () {
                    T.reset();
                    T.run(tour.id);
                });
                menu.append($menuItem);
            });
            return this._super();
        }
    });
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

var T = website.Tour = {
    tours: {},
    defaultDelay: 50,
    errorDelay: 5000,
    state: null,
    $element: null,
    timer: null,
    testtimer: null,
    currentTimer: null,
    register: function (tour) {
        if (tour.mode !== "test") tour.mode = "tutorial";
        T.tours[tour.id] = tour;
    },
    run: function (tour_id, mode) {
        var tour = T.tours[tour_id];
        this.time = new Date().getTime();
        if (tour.path && !window.location.href.match(new RegExp("("+T.getLang()+")?"+tour.path+"#?$", "i"))) {
            var href = "/"+T.getLang()+tour.path;
            console.log("Tour Begin from run method (redirection to "+href+")");
            T.saveState(tour.id, mode || tour.mode, -1);
            window.location.href = href;
        } else {
            console.log("Tour Begin from run method");
            T.saveState(tour.id, mode || tour.mode, 0);
            T.running();
        }
    },
    registerSteps: function (tour) {
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
            }
        }
        if (tour.steps[index-1] &&
            tour.steps[index-1].popover && tour.steps[index-1].popover.next) {
            var step = {
                id: index,
                waitNot: '.popover.tour.fade.in:visible'
            };
            tour.steps.push(step);
        }

        // rendering bootstrap tour and popover
        if (tour.mode !== "test") {
            for (var index=0, len=tour.steps.length; index<len; index++) {
                var step = tour.steps[index];
                step._title = step._title || step.title;
                step.title = T.popoverTitle(tour, { title: step._title });
                step.template = step.template || T.popover( step.popover );
            }
        }
    },
    closePopover: function () {
        if (T.$element) {
            T.$element.popover('destroy');
            T.$element.removeData("tour");
            T.$element.removeData("tour-step");
            $(".tour-backdrop").remove();
            $(".popover.tour").remove();
            T.$element = null;
        }
    },
    autoTogglePopover: function () {
        var state = T.getState();
        var step = state.step;

        if (T.$element &&
            T.$element.is(":visible") &&
            T.$element.data("tour") === state.id &&
            T.$element.data("tour-step") === step.id) {
            T.repositionPopover();
            return;
        }

        if (step.busy) {
            return;
        }

        T.closePopover();

        var $element = $(step.element).first();
        if (!step.element || !$element.size() || !$element.is(":visible")) {
            return;
        }


        T.$element = $element;
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

        if (step.backdrop || $element.parents("#website-top-navbar, .modal").size()) {
            $tip.css("z-index", 2010);
        }

        // button click event
        $tip.find("button")
            .one("click", function () {
                step.busy = true;
                if (!$(this).is("[data-role='next']")) {
                    clearTimeout(T.timer);
                    T.endTour();
                }
                T.closePopover();
            });

        T.repositionPopover();
    },
    repositionPopover: function() {
        var popover = T.$element.data("bs.popover");
        var $tip = T.$element.data("bs.popover").tip();

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
                var left = T.$element.offset().left + T.$element.outerWidth()/2 - tipOffset.left;
                $tip.find(".arrow").css("left", left ? left + "px" : "");
        } else if (popover.options.placement !== "auto") {
                var top = T.$element.offset().top + T.$element.outerHeight()/2 - tipOffset.top;
                $tip.find(".arrow").css("top", top ? top + "px" : "");
        }
    },
    popoverTitle: function (tour, options) {
        return openerp.qweb ? openerp.qweb.render('website.tour_popover_title', options) : options.title;
    },
    popover: function (options) {
        return openerp.qweb ? openerp.qweb.render('website.tour_popover', options) : options.title;
    },
    getLang: function () {
        return $("html").attr("lang").replace(/-/, '_');
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
            console.log("Tour Begin from url hash");
            T.saveState(state.id, state.mode, state.step_id);
        }
        if (!state.id || !T.tours[state.id]) {
            return;
        }
        state.tour = T.tours[state.id];
        state.step = state.tour.steps[state.step_id === -1 ? 0 : state.step_id];
        return state;
    },
    error: function (step, message) {
        var state = T.getState();
        message += '\n tour: ' + state.id
            + '\n step: ' + step.id + ": '" + (step._title || step.title) + "'"
            + '\n href: ' + window.location.href
            + '\n referrer: ' + document.referrer
            + '\n element: ' + Boolean(!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden")))
            + '\n waitNot: ' + Boolean(!step.waitNot || !$(step.waitNot).size())
            + '\n waitFor: ' + Boolean(!step.waitFor || $(step.waitFor).size())
            + "\n localStorage: " + JSON.stringify(localStorage)
            + '\n\n' + $("body").html();
        T.reset();
        throw new Error(message);
    },
    lists: function () {
        var tour_ids = [];
        for (var k in T.tours) {
            tour_ids.push(k);
        }
        return tour_ids;
    },
    saveState: function (tour_id, mode, step_id) {
        localStorage.setItem("tour", JSON.stringify({"id":tour_id, "mode":mode, "step_id":step_id || 0, "time": this.time}));
    },
    reset: function () {
        var state = T.getState();
        if (state) {
            for (var k in state.tour.steps) {
                state.tour.steps[k].busy = false;
            }
        }
        localStorage.removeItem("tour");
        clearTimeout(T.timer);
        clearTimeout(T.testtimer);
        T.closePopover();
    },
    testRunning: 0,
    running: function () {
        function run () {
            var state = T.getState();
            if (state) {
                console.log("Tour '"+state.id+"' is running");
                T.registerSteps(state.tour);
                T.nextStep();
            }
        }
        setTimeout(function () {
            if ($.ajaxBusy) {
                $(document).ajaxStop(run);
            } else {
                run();
            }
        },0);
    },
    check: function (step) {
        return (step &&
            (!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden"))) &&
            (!step.waitNot || !$(step.waitNot).size()) &&
            (!step.waitFor || $(step.waitFor).size()));
    },
    waitNextStep: function () {
        var state = T.getState();
        var time = new Date().getTime();
        var timer;
        var next = state.tour.steps[state.step.id+1];
        var overlaps = state.mode === "test" ? T.errorDelay : 0;

        window.onbeforeunload = function () {
            clearTimeout(T.timer);
            clearTimeout(T.testtimer);
        };

        function checkNext () {
            T.autoTogglePopover();

            clearTimeout(T.timer);
            if (T.check(next)) {
                clearTimeout(T.currentTimer);
                // use an other timeout for cke dom loading
                setTimeout(function () {
                    T.nextStep(next);
                }, T.defaultDelay);
            } else if (!overlaps || new Date().getTime() - time < overlaps) {
                T.timer = setTimeout(checkNext, T.defaultDelay);
            } else {
                T.error(next, "Can't reach the next step");
            }
        }
        checkNext();
    },
    nextStep: function (step) {
        var state = T.getState();

        if (!state) {
            return;
        }

        step = step || state.step;
        T.saveState(state.id, state.mode, step.id);

        if (step.id !== state.step_id) {
            console.log("Tour Step: '" + (step._title || step.title) + "' (" + (new Date().getTime() - this.time) + "ms)");
        }

        T.autoTogglePopover(true);

        if (step.onload) {
            step.onload();
        }

        var next = state.tour.steps[step.id+1];
        if (next) {
            setTimeout(function () {
                    T.waitNextStep();
                    if (state.mode === "test") {
                        setTimeout(function(){
                            T.autoNextStep(state.tour, step);
                        }, T.defaultDelay);
                    }
            }, next.wait || 0);
        } else {
            T.endTour();
        }
    },
    endTour: function () {
        var state = T.getState();
        var test = state.step.id >= state.tour.steps.length-1;
        T.reset();
        if (test) {
            console.log('ok');
        } else {
            console.log('error');
        }
    },
    autoNextStep: function (tour, step) {
        clearTimeout(T.testtimer);

        function autoStep () {
            if (!step) return;

            if (step.autoComplete) {
                step.autoComplete(tour);
            }

            $(".popover.tour [data-role='next']").click();

            var $element = $(step.element);
            if (!$element.size()) return;

            if (step.snippet) {

                T.autoDragAndDropSnippet($element);
            
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
                }, T.defaultDelay<<1);
            
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
        T.testtimer = setTimeout(autoStep, 100);
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

//$(document).ready(T.running);
website.ready().then(T.running);


}());
