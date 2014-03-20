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

// don't rewrite website.Tour in test mode
if (typeof website.Tour !== "undefined") {
    return;
}

// don't need template to use bootstrap Tour in automatic mode
if (typeof QWeb2 !== "undefined") {
    website.add_template_file('/website/static/src/xml/website.tour.xml');

}

// don't need to use bootstrap Tour to launch an automatic tour
function bootstrap_tour_stub () {
    if (typeof Tour === "undefined") {
        window.Tour = function Tour() {};
        Tour.prototype.addSteps = function () {};
        Tour.prototype.end = function () {};
        Tour.prototype.goto = function () {};
    }
}

if (website.EditorBar) {
    website.EditorBar.include({
        tours: [],
        start: function () {
            var self = this;
            var menu = $('#help-menu');
            _.each(website.Tour.tours, function (tour) {
                if (tour.mode != "tutorial") {
                    return;
                }
                var $menuItem = $($.parseHTML('<li><a href="#">'+tour.name+'</a></li>'));
                $menuItem.click(function () {
                    website.Tour.reset();
                    website.Tour.run(tour.id);
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

website.Tour = {};
website.Tour.tours = {};
website.Tour.state = null;
website.Tour.register = function (tour) {
    website.Tour.tours[tour.id] = tour;
};
website.Tour.run = function (tour_id, mode) {
    if (localStorage.getItem("tour")) { // only one test running
        return;
    }
    var tour = website.Tour.tours[tour_id];
    website.Tour.save_state(tour.id, mode || tour.mode, 0);
    if (tour.path) {
        window.location.href = "/"+website.Tour.getLang()+tour.path;
    }
};
website.Tour.registerSteps = function (tour) {
    if (tour.register) {
        return;
    }
    tour.register = true;

    for (var index=0, len=tour.steps.length; index<len; index++) {
        var step = tour.steps[index];
        step.id = index;

        if (!step.waitNot && index > 0 && tour.steps[index-1] &&
            tour.steps[index-1].popover && tour.steps[index-1].popover.next) {
            step.waitNot = '.popover.tour:visible';
        }
        if (!step.waitFor && index > 0 && tour.steps[index-1].snippet) {
            step.waitFor = '.oe_overlay_options .oe_options:visible';
        }

        if (!step.element) step.orphan = true;

        var snippet = step.element.match(/#oe_snippets (.*) \.oe_snippet_thumbnail/);
        if (snippet) {
            step.snippet = snippet[1];
        } else if (step.snippet) {
            step.element = '#oe_snippets '+step.snippet+' .oe_snippet_thumbnail';
        }
    }
    if (tour.steps[index-1] &&
        tour.steps[index-1].popover && tour.steps[index-1].popover.next) {
        var step = {
            step_id:    index,
            waitNot:   '.popover.tour:visible'
        };
        tour.steps.push(step);
    }

    // rendering bootstrap tour and popover
    if (tour.mode != "test") {
        tour.tour = new Tour({
            name: this.id,
            storage: localStorage,
            keyboard: false,
            template: this.popover(),
            onHide: function () {
                window.scrollTo(0, 0);
            }
        });
        for (var index=0, len=tour.steps.length; index<len; index++) {
            var step = tour.steps[index];
            step._title = step._title || step.title;
            step.title = tour.popoverTitle(tour, { title: step._title });
            step.template = step.template || tour.popover( step.popover );
        }
        tour.tour.addSteps(tour.steps);
    }
};
website.Tour.popoverTitle = function (tour, options) {
    return openerp.qweb.render('website.tour_popover_title', options);
};
website.Tour.popover = function (options) {
    return openerp.qweb.render('website.tour_popover', options);
};
website.Tour.getLang = function () {
    return $("html").attr("lang").replace(/-/, '_');
};
website.Tour.get_state = function () {
    var tour_id;
    var tour_running = eval(localStorage.getItem("tour") || 'false');
    if (tour_running) {
        tour_id = tour_running[0];
        mode = tour_running[1];
        step_id = tour_running[2];
    } else if (window.location.href.indexOf("#tutorial.") > -1) {
        tour_id = window.location.href.match(/#tutorial\.(.*)=true/)[1];
        mode = "tutorial";
        step_id = 0;
    }
    if (!tour_id) {
        return;
    }
    var tour = website.Tour.tours[tour_id];
    return {'tour': tour, 'tour_id': tour_id, 'mode': mode, 'step_id': step_id};
};
website.Tour.error = function (tour, step, message) {
    website.Tour.reset();
    throw new Error(message +
        + "\ntour:" + tour.id +
        + "\nstep:" + step.id + ": '" + (step._title || step.title) + "'"
        + '\nhref: ' + window.location.href
        + '\nreferrer: ' + document.referrer
        + '\nelement: ' + Boolean(!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden")))
        + '\nwaitNot: ' + Boolean(!step.waitNot || !$(step.waitNot).size())
        + '\nwaitFor: ' + Boolean(!step.waitFor || $(step.waitFor).size())
        + '\n\n' + $("body").html()
    );
};
website.Tour.lists = function () {
    var tour_ids = [];
    for (var k in website.Tour.tours) {
        tour_ids.push(k);
    }
    return tour_ids;
};
website.Tour.save_state = function (tour_id, mode, step_id) {
    localStorage.setItem("tour", '{tour_id:'+tour_id+',  mode:'+mode+',  step_id:'+step_id+'}');
};
website.Tour.reset = function () {
    var running = website.Tour.get_state();
    for (var k in running.tour.steps) {
        running.tour.steps[k].busy = false;
    }
    localStorage.removeItem("tour");
    clearTimeout(website.Tour.timer);
    clearTimeout(website.Tour.testtimer);

    $('.popover.tour').remove();
};
website.Tour.running = function () {
    var running = website.Tour.get_state();
    website.Tour.registerSteps(running.tour);
    website.Tour.nextStep( running.tour, running.step_id );
};

website.Tour.timer =  null;
website.Tour.testtimer = null;
website.Tour.defaultDelay = 50;
website.Tour.check = function (step) {
    return (step &&
        (!step.element || ($(step.element).size() && $(step.element).is(":visible") && !$(step.element).is(":hidden"))) &&
        (!step.waitNot || !$(step.waitNot).size()) &&
        (!step.waitFor || $(step.waitFor).size()));
};
website.Tour.waitNextStep = function (tour, step, overlaps) {
    var time = new Date().getTime();
    var timer;

    window.onbeforeunload = function () {
        clearTimeout(website.Tour.timer);
        clearTimeout(website.Tour.testtimer);
    };

    // check popover activity
    $(".popover.tour button")
        .off()
        .on("click", function () {
            $(".popover.tour").remove();
            if (step.busy) return;
            if (!$(this).is("[data-role='next']")) {
                clearTimeout(website.Tour.timer);
                step.busy = true;
                if (tour.tour) {
                    tour.tour.end();
                }
                tour.endTour(tour);
            }
        });

    function checkNext () {
        clearTimeout(website.Tour.timer);
        if (step.busy) return;
        if (website.Tour.check(step)) {
            step.busy = true;
            // use an other timeout for cke dom loading
            setTimeout(function () {
                website.Tour.nextStep(tour, step, overlaps);
            }, website.Tour.defaultDelay);
        } else if (!overlaps || new Date().getTime() - time < overlaps) {
            if (self.current.element) {
                var $popover = $(".popover.tour");
                if(!$(self.current.element).is(":visible")) {
                    $popover.data("hide", true).fadeOut(300);
                } else if($popover.data("hide")) {
                    $popover.data("hide", false).fadeIn(150);
                }
            }
            website.Tour.timer = setTimeout(checkNext, website.Tour.defaultDelay);
        } else {
            website.Tour.error(tour, step, "Can't arrive to the next step");
        }
    }
    checkNext();
};
website.Tour.nextStep = function (tour, step, overlaps) {
    var state = website.Tour.get_state();
    website.Tour.save_state(tour.id, state.mode, step.id);

    // clear popover (fix for boostrap tour if the element is removed before destroy popover)
    $(".popover.tour").remove();
    // go to step in bootstrap tour
    tour.tour.goto(step.id);
    step.onload();
    var next = tour.steps[step.id+1];

    if (next) {
        setTimeout(function () {
                website.Tour.waitNextStep(tour, next, overlaps);
                if (state.mode === "test") {
                    setTimeout(function(){
                        website.Tour.autoNextStep(tour, step);
                    }, website.Tour.defaultDelay);
                }
        }, next && next.wait || 0);
    } else {
        website.Tour.endTour(tour);
    }
};
website.Tour.endTour = function (tour) {
    var state = website.Tour.get_state();
    var test = state.step_id >= tour.steps.length-1;
    this.reset();
    if (test) {
        console.log('ok');
    } else {
        console.log('error');
    }
};
website.Tour.autoNextStep = function (tour, step) {
    clearTimeout(website.Tour.testtimer);

    function autoStep () {
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
            
            website.Tour.autoDragAndDropSnippet($element);
        
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
            }, website.Tour.defaultDelay<<1);
        
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
    website.Tour.testtimer = setTimeout(autoStep, 100);
};
website.Tour.autoDragAndDropSnippet = function (selector) {
    var $thumbnail = $(selector).first();
    var thumbnailPosition = $thumbnail.position();
    $thumbnail.trigger($.Event("mousedown", { which: 1, pageX: thumbnailPosition.left, pageY: thumbnailPosition.top }));
    $thumbnail.trigger($.Event("mousemove", { which: 1, pageX: document.body.scrollWidth/2, pageY: document.body.scrollHeight/2 }));
    var $dropZone = $(".oe_drop_zone").first();
    var dropPosition = $dropZone.position();
    $dropZone.trigger($.Event("mouseup", { which: 1, pageX: dropPosition.left, pageY: dropPosition.top }));
};

website.ready(website.Tour.running);


}());
