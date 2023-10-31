odoo.define('web_tour.TourManager', function(require) {
"use strict";

var core = require('web.core');
var config = require('web.config');
var local_storage = require('web.local_storage');
var mixins = require('web.mixins');
var utils = require('web_tour.utils');
var TourStepUtils = require('web_tour.TourStepUtils');
var RunningTourActionHelper = require('web_tour.RunningTourActionHelper');
var ServicesMixin = require('web.ServicesMixin');
var session = require('web.session');
var Tip = require('web_tour.Tip');
const {Markup} = require('web.utils');

var _t = core._t;

var RUNNING_TOUR_TIMEOUT = 10000;

var get_step_key = utils.get_step_key;
var get_debugging_key = utils.get_debugging_key;
var get_running_key = utils.get_running_key;
var get_running_delay_key = utils.get_running_delay_key;
var get_first_visible_element = utils.get_first_visible_element;
var do_before_unload = utils.do_before_unload;
var get_jquery_element_from_selector = utils.get_jquery_element_from_selector;

return core.Class.extend(mixins.EventDispatcherMixin, ServicesMixin, {
    init: function(parent, consumed_tours, disabled = false) {
        mixins.EventDispatcherMixin.init.call(this);
        this.setParent(parent);

        this.$body = $('body');
        this.active_tooltips = {};
        this.tours = {};
        // remove the tours being debug from the list of consumed tours
        this.consumed_tours = (consumed_tours || []).filter(tourName => {
            return !local_storage.getItem(get_debugging_key(tourName));
        });
        this.disabled = disabled;
        this.running_tour = local_storage.getItem(get_running_key());
        this.running_step_delay = parseInt(local_storage.getItem(get_running_delay_key()), 10) || 0;
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
     * @param {string} [options.fadeout]
     *        Delay for rainbowman to disappear. 'fast' will make rainbowman dissapear, quickly,
     *        'medium', 'slow' and 'very_slow' will wait little longer before disappearing, no
     *        will keep rainbowman on screen until user clicks anywhere outside rainbowman
     * @param {boolean} [options.sequence=1000]
     *        priority sequence of the tour (lowest is first, tours with the same
     *        sequence will be executed in a non deterministic order).
     * @param {Promise} [options.wait_for]
     *        indicates when the tour can be started
     * @param {string|function} [options.rainbowManMessage]
              text or function returning the text displayed under the rainbowman
              at the end of the tour.
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
            name: options.saveAs || name,
            steps: steps,
            url: options.url,
            rainbowMan: options.rainbowMan === undefined ? true : !!options.rainbowMan,
            rainbowManMessage: options.rainbowManMessage,
            fadeout: options.fadeout || 'medium',
            sequence: options.sequence || 1000,
            test: options.test,
            wait_for: options.wait_for || Promise.resolve(),
        };
        if (options.skip_enabled) {
            tour.skip_link = Markup`<p><span class="o_skip_tour">${_t('Skip tour')}</span></p>`;
            tour.skip_handler = function (tip) {
                this._deactivate_tip(tip);
                this._consume_tour(name);
            };
        }
        this.tours[tour.name] = tour;
    },
    /**
     * Returns a promise which is resolved once the tour can be started. This
     * is when the DOM is ready and at the end of the execution stack so that
     * all tours have potentially been extended by all apps.
     *
     * @private
     * @returns {Promise}
     */
    _waitBeforeTourStart: function () {
        return new Promise(function (resolve) {
            $(function () {
                setTimeout(resolve);
            });
        });
    },
    _register_all: function (do_update) {
        var self = this;
        if (this._allRegistered) {
            return Promise.resolve();
        }
        this._allRegistered = true;
        return self._waitBeforeTourStart().then(function () {
            return Promise.all(_.map(self.tours, function (tour, name) {
                return self._register(do_update, tour, name);
            })).then(() => self.update());
        });
    },
    _register: function (do_update, tour, name) {
        const debuggingTour = local_storage.getItem(get_debugging_key(name));
        if (this.disabled && !this.running_tour && !debuggingTour) {
            this.consumed_tours.push(name);
        }

        if (tour.ready) return Promise.resolve();

        const tour_is_consumed = this._isTourConsumed(name);

        return tour.wait_for.then((function () {
            tour.current_step = parseInt(local_storage.getItem(get_step_key(name))) || 0;
            tour.steps = _.filter(tour.steps, (function (step) {
                return (!step.edition || step.edition === this.edition) &&
                    (step.mobile === undefined || step.mobile === config.device.isMobile);
            }).bind(this));

            if (tour_is_consumed || tour.current_step >= tour.steps.length) {
                local_storage.removeItem(get_step_key(name));
                tour.current_step = 0;
            }

            tour.ready = true;

            if (debuggingTour ||
                (do_update && (this.running_tour === name ||
                              (!this.running_tour && !tour.test && !tour_is_consumed)))) {
                this._to_next_step(name, 0);
            }
        }).bind(this));
    },
    /**
     * Resets the given tour to its initial step, and prevent it from being
     * marked as consumed at reload.
     *
     * @param {string} tourName
     */
    reset: function (tourName) {
        // remove it from the list of consumed tours
        const index = this.consumed_tours.indexOf(tourName);
        if (index >= 0) {
            this.consumed_tours.splice(index, 1);
        }
        // mark it as being debugged
        local_storage.setItem(get_debugging_key(tourName), true);
        // reset it to the first step
        const tour = this.tours[tourName];
        tour.current_step = 0;
        local_storage.removeItem(get_step_key(tourName));
        this._to_next_step(tourName, 0);
        // redirect to its starting point (or /web by default)
        window.location.href = window.location.origin + (tour.url || '/web');
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

            window.location.href = window.location.origin + tour.url;
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
            var self = this;
            setTimeout(function () {
                self._check_for_tooltip(self.active_tooltips[tour_name], tour_name);
            });
        } else {
            const sortedTooltips = Object.keys(this.active_tooltips).sort(
                (a, b) => this.tours[a].sequence - this.tours[b].sequence
            );
            let visibleTip = false;
            for (const tourName of sortedTooltips) {
                var tip = this.active_tooltips[tourName];
                tip.hidden = visibleTip;
                visibleTip = this._check_for_tooltip(tip, tourName) || visibleTip;
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
        if (tip === undefined) {
            return true;
        }
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

        var $visible_alt_trigger = $();
        if (tip.alt_trigger) {
            var $alt_trigger;
            if (tip.in_modal !== false && this.$modal_displayed.length) {
                $alt_trigger = this.$modal_displayed.find(tip.alt_trigger);
            } else {
                $alt_trigger = get_jquery_element_from_selector(tip.alt_trigger);
            }
            $visible_alt_trigger = get_first_visible_element($alt_trigger);
        }

        var triggered = $visible_trigger.length && extra_trigger;
        if (triggered) {
            if (!tip.widget) {
                this._activate_tip(tip, tour_name, $visible_trigger, $visible_alt_trigger);
            } else {
                tip.widget.update($visible_trigger, $visible_alt_trigger);
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
    /**
     * Activates the provided tip for the provided tour, $anchor and $alt_trigger.
     * $alt_trigger is an alternative trigger that can consume the step. The tip is
     * however only displayed on the $anchor.
     *
     * @param {Object} tip
     * @param {String} tour_name
     * @param {jQuery} $anchor
     * @param {jQuery} $alt_trigger
     * @private
     */
    _activate_tip: function(tip, tour_name, $anchor, $alt_trigger) {
        var tour = this.tours[tour_name];
        var tip_info = tip;
        if (tour.skip_link) {
            tip_info = _.extend(_.omit(tip_info, 'content'), {
                content: Markup`${tip.content}${tour.skip_link}`,
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
        tip.widget.attach_to($anchor, $alt_trigger).then(this._to_next_running_step.bind(this, tip, tour_name));
    },
    _deactivate_tip: function(tip) {
        if (tip && tip.widget) {
            tip.widget.destroy();
            delete tip.widget;
        }
    },
    _describeTip: function(tip) {
        return tip.content ? tip.content + ' (trigger: ' + tip.trigger + ')' : tip.trigger;
    },
    _consume_tip: function(tip, tour_name) {
        this._deactivate_tip(tip);
        this._to_next_step(tour_name);

        var is_running = (this.running_tour === tour_name);
        if (is_running) {
            var stepDescription = this._describeTip(tip);
            console.log(_.str.sprintf("Tour %s: step '%s' succeeded", tour_name, stepDescription));
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
    /**
     * @private
     * @param {string} tourName
     * @returns {boolean}
     */
    _isTourConsumed(tourName) {
        return this.consumed_tours.includes(tourName);
    },
    _consume_tour: function (tour_name, error) {
        delete this.active_tooltips[tour_name];
        //display rainbow at the end of any tour
        if (this.tours[tour_name].rainbowMan && this.running_tour !== tour_name &&
            this.tours[tour_name].current_step === this.tours[tour_name].steps.length) {
            let message = this.tours[tour_name].rainbowManMessage;
            if (message) {
                message = typeof message === 'function' ? message() : message;
            } else {
                message = _t('<strong><b>Good job!</b> You went through all steps of this tour.</strong>');
            }
            const fadeout = this.tours[tour_name].fadeout;
            core.bus.trigger('show-effect', {
                type: "rainbow_man",
                message,
                fadeout,
                messageIsHtml: true,
            });
        }
        this.tours[tour_name].current_step = 0;
        local_storage.removeItem(get_step_key(tour_name));
        local_storage.removeItem(get_debugging_key(tour_name));
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
                console.log(document.body.parentElement.outerHTML);
                console.error(error); // will be displayed as error info
            } else {
                console.log(_.str.sprintf("Tour %s succeeded", tour_name));
                console.log("test successful"); // browser_js wait for message "test successful"
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
            var descr = this._describeTip(step);
            this._consume_tour(tour_name, _.str.sprintf("Tour %s failed at step %s", tour_name, descr));
        }).bind(this), (step.timeout || RUNNING_TOUR_TIMEOUT) + this.running_step_delay);
    },
    _stop_running_tour_timeout: function () {
        clearTimeout(this.running_tour_timeout);
        this.running_tour_timeout = undefined;
    },
    _to_next_running_step: function (tip, tour_name) {
        if (this.running_tour !== tour_name) return;
        var self = this;
        this._stop_running_tour_timeout();
        if (this.running_step_delay) {
            // warning: due to the delay, it may happen that the $anchor isn't
            // in the DOM anymore when exec is called, either because:
            // - it has been removed from the DOM meanwhile and the tip's
            //   selector doesn't match anything anymore
            // - it has been re-rendered and thus the selector still has a match
            //   in the DOM, but executing the step with that $anchor won't work
            _.delay(exec, this.running_step_delay);
        } else {
            exec();
        }

        function exec() {
            const anchorIsInDocument = tip.widget.$anchor[0].ownerDocument.contains(tip.widget.$anchor[0]);
            const uiIsBlocked = $('body').hasClass('o_ui_blocked');
            if (!anchorIsInDocument || uiIsBlocked) {
                // trigger is no longer in the DOM, or UI is now blocked, so run the same step again
                self._deactivate_tip(self.active_tooltips[tour_name]);
                self._to_next_step(tour_name, 0);
                self.update();
                return;
            }
            var action_helper = new RunningTourActionHelper(tip.widget);
            do_before_unload(self._consume_tip.bind(self, tip, tour_name));

            var tour = self.tours[tour_name];
            if (typeof tip.run === "function") {
                tip.run.call(tip.widget, action_helper);
            } else if (tip.run !== undefined) {
                var m = tip.run.match(/^([a-zA-Z0-9_]+) *(?:\(? *(.+?) *\)?)?$/);
                action_helper[m[1]](m[2]);
            } else if (tour.current_step === tour.steps.length - 1) {
                console.log('Tour %s: ignoring action (auto) of last step', tour_name);
            } else {
                action_helper.auto();
            }
        }
    },
    stepUtils: new TourStepUtils(this)
});
});
