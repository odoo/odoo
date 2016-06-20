odoo.define('web_tour.TourManager', function(require) {
"use strict";

var core = require('web.core');
var local_storage = require('web.local_storage');
var Model = require('web.Model');
var Tip = require('web_tour.Tip');

var _t = core._t;

var RUNNING_TOUR_TIMEOUT = 3000;

function getStepKey(name) {
    return 'tour_' + name + '_step';
}
function getRunningKey() {
    return 'running_tour';
}

return core.Class.extend({
    init: function(consumed_tours) {
        this.$body = $('body');
        this.active_tooltips = {};
        this.tours = {};
        this.consumed_tours = consumed_tours || [];
        this.running_tour = local_storage.getItem(getRunningKey());
        this.TourModel = new Model('web_tour.tour');
    },
    /**
     * Registers a tour described by the following arguments (in order)
     * @param [String] tour's name
     * @param [Object] dict of options (optional), available options are:
     *   test [Boolean] true if the tour is dedicated to tests (it won't be enabled by default)
     *   skip_enabled [Boolean] true to add a link to consume the whole tour in its tips
     *   url [String] the url to load when manually running the tour
     * @param [Array] dict of steps, each step being a dict containing a tip description
     */
    register: function() {
        var args = Array.prototype.slice.call(arguments);
        var last_arg = args[args.length - 1];
        var name = args[0];
        if (this.tours[name]) {
            console.warn(_.str.sprintf(_t("Tour %s is already defined"), name));
            return;
        }
        var options = args.length === 2 ? {} : args[1];
        var steps = last_arg instanceof Array ? last_arg : [last_arg];
        var tour = {
            name: name,
            current_step: parseInt(local_storage.getItem(getStepKey(name))) || 0,
            steps: steps,
            url: options.url,
            test: options.test,
        };
        if (options.skip_enabled) {
            tour.skip_link = '<p><span class="o_skip_tour">' + _t('Skip tour') + '</span></p>';
            tour.skip_handler = function (tip) {
                this._deactivate_tip(tip);
                this._consume_tour(name);
            };
        }
        this.tours[name] = tour;
        if (name === this.running_tour || (!tour.test && !_.contains(this.consumed_tours, name))) {
            this.active_tooltips[name] = steps[tour.current_step];
        }
    },
    run: function(tour_name) {
        if (this.running_tour) {
            console.warn(_.str.sprintf(_t("Killing tour %s"), tour_name));
            this._deactivate_tip(this.active_tooltips[tour_name]);
            this._consume_tour(tour_name);
            return;
        }
        var tour = this.tours[tour_name];
        if (!tour) {
            console.warn(_.str.sprintf(_t("Unknown Tour %s"), name));
            return;
        }
        console.log(_.str.sprintf(_t("Running tour %s"), tour_name));
        local_storage.setItem(getRunningKey(), tour_name);
        if (tour.url) {
            window.location = tour.url;
        }
        this.running_tour = tour_name;
        this.active_tooltips[tour_name] = tour.steps[0];
        this._set_running_tour_timeout(tour_name, tour.steps[0]);
        this.update();
    },
    /**
     * Checks for tooltips to activate (only from the running tour if there is one, from all
     * active tours otherwise). Should be called each time the DOM changes.
     */
    update: function() {
        this.in_modal = this.$body.hasClass('modal-open');
        if (this.running_tour) {
            this._check_for_tooltip(this.active_tooltips[this.running_tour], this.running_tour);
        } else {
            _.each(this.active_tooltips, this._check_for_tooltip.bind(this));
        }
    },
    _check_for_tooltip: function (tip, tour_name) {
        var $trigger = $((this.in_modal ? '.modal ' : '') + tip.trigger).filter(':visible').first();
        var extra_trigger = tip.extra_trigger ? $(tip.extra_trigger).filter(':visible').length : true;
        var triggered = $trigger.length && extra_trigger;
        if (triggered) {
            if (!tip.widget) {
                this._activate_tip(tip, tour_name, $trigger);
            } else {
                tip.widget.update($trigger);
            }
        } else {
            this._deactivate_tip(tip);
        }
    },
    _activate_tip: function(tip, tour_name, $anchor) {
        var tour = this.tours[tour_name];
        var tip_info = tip;
        if (tour.skip_link) {
            tip_info = _.extend(_.omit(tip_info, 'content'), {
                content: tip.content + tour.skip_link,
                event_handlers: [{
                    event: 'click',
                    selector: '.o_skip_tour',
                    handler: tour.skip_handler.bind(this, tip),
                }],
            });
        }
        tip.widget = new Tip(this, tip_info);
        tip.widget.on('tip_consumed', this, this._consume_tip.bind(this, tip, tour_name));
        tip.widget.attach_to($anchor);

        if (this.running_tour === tour_name) {
            clearTimeout(this.running_tour_timeout);
            if (tip.run) {
                this._consume_tip(tip, tour_name);
                tip.run.apply(tip);
            }
        }
    },
    _deactivate_tip: function(tip) {
        if (tip.widget) {
            tip.widget.destroy();
            delete tip.widget;
        }
    },
    _consume_tip: function(tip, tour_name) {
        this._deactivate_tip(tip);
        var tour = this.tours[tour_name];
        if (tour.current_step < tour.steps.length - 1) {
            tour.current_step = tour.current_step + 1;
            this.active_tooltips[tour_name] = tour.steps[tour.current_step];
            local_storage.setItem(getStepKey(tour_name), tour.current_step);
            if (this.running_tour === tour_name) {
                this._set_running_tour_timeout(tour_name, this.active_tooltips[tour_name]);
            }
        } else {
            this._consume_tour(tour_name);
        }
    },
    _consume_tour: function(tour_name) {
        delete this.active_tooltips[tour_name];
        this.tours[tour_name].current_step = 0;
        local_storage.removeItem(getStepKey(tour_name));
        if (this.running_tour === tour_name) {
            local_storage.removeItem(getRunningKey());
            this.running_tour = undefined;
            clearTimeout(this.running_tour_timeout);
        } else {
            this.TourModel.call('consume', [tour_name]);
        }
    },
    _set_running_tour_timeout: function(tour_name, step) {
        if (!step.run) { return; } // don't set a timeout if the current step requires a manual action
        var self = this;
        this.running_tour_timeout = setTimeout(function() {
            console.error(_.str.sprintf(_t("Tour %s failed at step %s"), tour_name, step.trigger));
            self._consume_tour(tour_name);
        }, RUNNING_TOUR_TIMEOUT);
    },
});

});
