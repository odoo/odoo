odoo.define('web_tour.TourManager', function(require) {
"use strict";

var core = require('web.core');
var local_storage = require('web.local_storage');
var mixins = require('web.mixins');
var utils = require('web_tour.utils');
var RainbowMan = require('web.RainbowMan');
var RunningTourActionHelper = require('web_tour.RunningTourActionHelper');
var ServicesMixin = require('web.ServicesMixin');
var session = require('web.session');
var Tip = require('web_tour.Tip');

var _t = core._t;

var RUNNING_TOUR_TIMEOUT = 10000;

var get_step_key = utils.get_step_key;
var get_running_key = utils.get_running_key;
var get_running_delay_key = utils.get_running_delay_key;
var get_first_visible_element = utils.get_first_visible_element;
var do_before_unload = utils.do_before_unload;
var get_jquery_element_from_selector = utils.get_jquery_element_from_selector;

return core.Class.extend(mixins.EventDispatcherMixin, ServicesMixin, {
    init: function(parent, consumed_tours) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);

        this.$body = $('body');
        this.active_tooltips = {};
        this.tours = {};
        this.consumed_tours = consumed_tours || [];
        this.running_tour = local_storage.getItem(get_running_key());
        this.running_step_delay = parseInt(local_storage.getItem(get_running_delay_key()), 10) || 10;
        this.edition = (_.last(session.server_version_info) === 'e') ? 'enterprise' : 'community';
        this._log = [];
        console.log('Tour Manager is ready.  running_tour=' + this.running_tour);
    },
    /**
     * Registers a tour described by the following arguments *in order*
     *
     * @param {string} name - tour's name
     * @param {Object} [options] - options (optional), available options are:
     * @param {boolean} [options.test=false] - true if this is only for tests
     * @param {boolean} [options.skip_enabled=false]
     *        true to add a link in its tips to consume the whole tour
     * @param {string} [options.url]
     *        the url to load when manually running the tour
     * @param {boolean} [options.rainbowMan=true]
     *        whether or not the rainbowman must be shown at the end of the tour
     * @param {Deferred} [options.wait_for]
     *        indicates when the tour can be started
     * @param {Object[]} steps - steps' descriptions, each step being an object
     *                     containing a tip description
     */
    register: function() {
        var args = Array.prototype.slice.call(arguments);
        var last_arg = args[args.length - 1];
        var name = args[0];
        if (this.tours[name]) {
            console.warn(_.str.sprintf("Tour %s is already defined", name));
            return;
        }
        var options = args.length === 2 ? {} : args[1];
        var steps = last_arg instanceof Array ? last_arg : [last_arg];
        var tour = {
            name: name,
            steps: steps,
            url: options.url,
            rainbowMan: options.rainbowMan === undefined ? true : !!options.rainbowMan,
            test: options.test,
            wait_for: options.wait_for || $.when(),
        };
        if (options.skip_enabled) {
            tour.skip_link = '<p><span class="o_skip_tour">' + _t('Skip tour') + '</span></p>';
            tour.skip_handler = function (tip) {
                this._deactivate_tip(tip);
                this._consume_tour(name);
            };
        }
        this.tours[name] = tour;
    },
    _register_all: function (do_update) {
        if (this._all_registered) return;
        this._all_registered = true;

        _.each(this.tours, this._register.bind(this, do_update));
    },
    _register: function (do_update, tour, name) {
        if (tour.ready) return $.when();

        var tour_is_consumed = _.contains(this.consumed_tours, name);

        return tour.wait_for.then((function () {
            tour.current_step = parseInt(local_storage.getItem(get_step_key(name))) || 0;
            tour.steps = _.filter(tour.steps, (function (step) {
                return !step.edition || step.edition === this.edition;
            }).bind(this));

            if (tour_is_consumed || tour.current_step >= tour.steps.length) {
                local_storage.removeItem(get_step_key(name));
                tour.current_step = 0;
            }

            tour.ready = true;

            if (do_update && (this.running_tour === name || (!this.running_tour && !tour.test && !tour_is_consumed))) {
                this._to_next_step(name, 0);
                this.update(name);
            }
        }).bind(this));
    },
    run: function (tour_name, step_delay) {
        console.log(_.str.sprintf("Preparing tour %s", tour_name));
        if (this.running_tour) {
            this._deactivate_tip(this.active_tooltips[this.running_tour]);
            this._consume_tour(this.running_tour, _.str.sprintf("Killing tour %s", this.running_tour));
            return;
        }
        var tour = this.tours[tour_name];
        if (!tour) {
            console.warn(_.str.sprintf("Unknown Tour %s", name));
            return;
        }
        console.log(_.str.sprintf("Running tour %s", tour_name));
        this.running_tour = tour_name;
        this.running_step_delay = step_delay || this.running_step_delay;
        local_storage.setItem(get_running_key(), this.running_tour);
        local_storage.setItem(get_running_delay_key(), this.running_step_delay);

        this._deactivate_tip(this.active_tooltips[tour_name]);

        tour.current_step = 0;
        this._to_next_step(tour_name, 0);
        local_storage.setItem(get_step_key(tour_name), tour.current_step);

        if (tour.url) {
            this.pause();
            do_before_unload(null, (function () {
                this.play();
                this.update();
            }).bind(this));

            var url = session.debug ? $.param.querystring(tour.url, {debug: session.debug}) : tour.url;
            window.location.href = window.location.origin + url;
        } else {
            this.update();
        }
    },
    pause: function () {
        this.paused = true;
    },
    play: function () {
        this.paused = false;
    },
    /**
     * Checks for tooltips to activate (only from the running tour or specified tour if there
     * is one, from all active tours otherwise). Should be called each time the DOM changes.
     */
    update: function (tour_name) {
        if (this.paused) return;

        this.$modal_displayed = $('.modal:visible').last();

        tour_name = this.running_tour || tour_name;
        if (tour_name) {
            var tour = this.tours[tour_name];
            if (!tour || !tour.ready) return;

            if (this.running_tour && this.running_tour_timeout === undefined) {
                this._set_running_tour_timeout(this.running_tour, this.active_tooltips[this.running_tour]);
            }
            this._check_for_tooltip(this.active_tooltips[tour_name], tour_name);
        } else {
            for (var tourName in this.active_tooltips) {
                var tip = this.active_tooltips[tourName];
                var activated = this._check_for_tooltip(tip, tourName);
                if (activated) {
                    break;
                }
            }
        }
    },
    /**
     *  Check (and activate or update) a help tooltip for a tour.
     *
     * @param {Object} tip
     * @param {string} tour_name
     * @returns {boolean} true if a tip was found and activated/updated
     */
    _check_for_tooltip: function (tip, tour_name) {

        if ($('body').hasClass('o_ui_blocked')) {
            this._deactivate_tip(tip);
            this._log.push("blockUI is preventing the tip to be consumed");
            return false;
        }

        var $trigger;
        if (tip.in_modal !== false && this.$modal_displayed.length) {
            $trigger = this.$modal_displayed.find(tip.trigger);
        } else {
            $trigger = get_jquery_element_from_selector(tip.trigger);
        }
        var $visible_trigger = get_first_visible_element($trigger);

        var extra_trigger = true;
        var $extra_trigger;
        if (tip.extra_trigger) {
            $extra_trigger = get_jquery_element_from_selector(tip.extra_trigger);
            extra_trigger = get_first_visible_element($extra_trigger).length;
        }

        var triggered = $visible_trigger.length && extra_trigger;
        if (triggered) {
            if (!tip.widget) {
                this._activate_tip(tip, tour_name, $visible_trigger);
            } else {
                tip.widget.update($visible_trigger);
            }
        } else {
            if ($trigger.iframeContainer || ($extra_trigger && $extra_trigger.iframeContainer)) {
                var $el = $();
                if ($trigger.iframeContainer) {
                    $el = $el.add($trigger.iframeContainer);
                }
                if (($extra_trigger && $extra_trigger.iframeContainer) && $trigger.iframeContainer !== $extra_trigger.iframeContainer) {
                    $el = $el.add($extra_trigger.iframeContainer);
                }
                var self = this;
                $el.off('load').one('load', function () {
                    $el.off('load');
                    if (self.active_tooltips[tour_name] === tip) {
                        self.update(tour_name);
                    }
                });
            }
            this._deactivate_tip(tip);

            if (this.running_tour === tour_name) {
                this._log.push("_check_for_tooltip");
                this._log.push("- modal_displayed: " + this.$modal_displayed.length);
                this._log.push("- trigger '" + tip.trigger + "': " + $trigger.length);
                this._log.push("- visible trigger '" + tip.trigger + "': " + $visible_trigger.length);
                if ($extra_trigger !== undefined) {
                    this._log.push("- extra_trigger '" + tip.extra_trigger + "': " + $extra_trigger.length);
                    this._log.push("- visible extra_trigger '" + tip.extra_trigger + "': " + extra_trigger);
                }
            }
        }
        return !!triggered;
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
        if (this.running_tour !== tour_name) {
            tip.widget.on('tip_consumed', this, this._consume_tip.bind(this, tip, tour_name));
        }
        tip.widget.attach_to($anchor).then(this._to_next_running_step.bind(this, tip, tour_name));
    },
    _deactivate_tip: function(tip) {
        if (tip && tip.widget) {
            tip.widget.destroy();
            delete tip.widget;
        }
    },
    _consume_tip: function(tip, tour_name) {
        this._deactivate_tip(tip);
        this._to_next_step(tour_name);

        var is_running = (this.running_tour === tour_name);
        if (is_running) {
            console.log(_.str.sprintf("Tour %s: step %s succeeded", tour_name, tip.trigger));
        }

        if (this.active_tooltips[tour_name]) {
            local_storage.setItem(get_step_key(tour_name), this.tours[tour_name].current_step);
            if (is_running) {
                this._log = [];
                this._set_running_tour_timeout(tour_name, this.active_tooltips[tour_name]);
            }
            this.update(tour_name);
        } else {
            this._consume_tour(tour_name);
        }
    },
    _to_next_step: function (tour_name, inc) {
        var tour = this.tours[tour_name];
        tour.current_step += (inc !== undefined ? inc : 1);
        if (this.running_tour !== tour_name) {
            var index = _.findIndex(tour.steps.slice(tour.current_step), function (tip) {
                return !tip.auto;
            });
            if (index >= 0) {
                tour.current_step += index;
            } else {
                tour.current_step = tour.steps.length;
            }
        }
        this.active_tooltips[tour_name] = tour.steps[tour.current_step];
    },
    _consume_tour: function (tour_name, error) {
        delete this.active_tooltips[tour_name];
        //display rainbow at the end of any tour
        if (this.tours[tour_name].rainbowMan && this.running_tour !== tour_name &&
            this.tours[tour_name].current_step === this.tours[tour_name].steps.length) {
            var $rainbow_message = $('<strong>' +
                                '<b>Good job!</b>' +
                                ' You went through all steps of this tour.' +
                                '</strong>');
            new RainbowMan({message: $rainbow_message}).appendTo(this.$body);
        }
        this.tours[tour_name].current_step = 0;
        local_storage.removeItem(get_step_key(tour_name));
        if (this.running_tour === tour_name) {
            this._stop_running_tour_timeout();
            local_storage.removeItem(get_running_key());
            local_storage.removeItem(get_running_delay_key());
            this.running_tour = undefined;
            this.running_step_delay = undefined;
            if (error) {
                _.each(this._log, function (log) {
                    console.log(log);
                });
                console.log(document.body.outerHTML);
                console.error(error); // will be displayed as error info
                console.log("error"); // phantomJS wait for message starting by error to stop
            } else {
                console.log(_.str.sprintf("Tour %s succeeded", tour_name));
                console.log("ok"); // phantomJS wait for exact message "ok"
            }
            this._log = [];
        } else {
            var self = this;
            this._rpc({
                    model: 'web_tour.tour',
                    method: 'consume',
                    args: [[tour_name]],
                })
                .then(function () {
                    self.consumed_tours.push(tour_name);
                });
        }
    },
    _set_running_tour_timeout: function (tour_name, step) {
        this._stop_running_tour_timeout();
        this.running_tour_timeout = setTimeout((function() {
            this._consume_tour(tour_name, _.str.sprintf("Tour %s failed at step %s", tour_name, step.trigger));
        }).bind(this), (step.timeout || RUNNING_TOUR_TIMEOUT) + this.running_step_delay);
    },
    _stop_running_tour_timeout: function () {
        clearTimeout(this.running_tour_timeout);
        this.running_tour_timeout = undefined;
    },
    _to_next_running_step: function (tip, tour_name) {
        if (this.running_tour !== tour_name) return;
        this._stop_running_tour_timeout();

        var action_helper = new RunningTourActionHelper(tip.widget);
        _.delay((function () {
            do_before_unload(this._consume_tip.bind(this, tip, tour_name));

            if (typeof tip.run === "function") {
                tip.run.call(tip.widget, action_helper);
            } else if (tip.run !== undefined) {
                var m = tip.run.match(/^([a-zA-Z0-9_]+) *(?:\(? *(.+?) *\)?)?$/);
                action_helper[m[1]](m[2]);
            } else {
                action_helper.auto();
            }
        }).bind(this), this.running_step_delay);
    },

    /**
     * Tour predefined steps
     */
    STEPS: {
        SHOW_APPS_MENU_ITEM: {
            edition: 'community',
            trigger: '.o_menu_apps a',
            auto: true,
            position: "bottom",
        },

        TOGGLE_HOME_MENU: {
            edition: "enterprise",
            trigger: ".o_main_navbar .o_menu_toggle",
            content: _t('Click on the <i>Home icon</i> to navigate across apps.'),
            position: "bottom",
        },

        WEBSITE_NEW_PAGE: {
            trigger: "#new-content-menu > a",
            auto: true,
            position: "bottom",
        },
    },
});
});
