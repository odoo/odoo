odoo.define('web_tour.tour', function(require) {
"use strict";

var ajax = require('web.ajax');
var config = require('web.config');
var core = require('web.core');
var Model = require('web.Model');
var session = require('web.session');
var TourManager = require('web_tour.TourManager');

var QWeb = core.qweb;

if (config.device.size_class <= config.device.SIZES.XS) {
    return {
        register: function () {},
        run: function () {
            console.warn("Tours are disabled for mobile mode.");
        },
        STEPS: {},
    };
}

return session.is_bound.then(function () {
    var defs = [];
    // Load the list of consumed tours and the tip template only if we are admin, in the frontend,
    // tours being only available for the admin. For the backend, the list of consumed is directly
    // in the page source.
    if (session.is_frontend && session.is_superuser) {
        defs.push(new Model('web_tour.tour').call('get_consumed_tours'));
    }
    return $.when.apply($, defs).then(function (consumed_tours) {
        var tour = new TourManager(session.is_frontend ? consumed_tours : session.web_tours);

        // Use a MutationObserver to detect DOM changes
        var untracked_classnames = ["o_tooltip", "o_tooltip_content", "o_tooltip_overlay"];
        var check_tooltip = _.debounce(function (records) {
            var update = _.some(records, function (record) {
                return !(is_untracked(record.target)
                    || _.some(record.addedNodes, is_untracked)
                    || _.some(record.removedNodes, is_untracked));

                function is_untracked(node) {
                    var record_class = node.className;
                    return (_.isString(record_class)
                        && _.intersection(record_class.split(' '), untracked_classnames).length !== 0);
                }
            });
            if (update) { // ignore mutations which concern the tooltips
                tour.update();
            }
        }, 500);
        var observer = new MutationObserver(check_tooltip);
        var start_service = (function () {
            var load_def;

            return function (observe) {
                if (load_def === undefined && observe && session.is_frontend) {
                    load_def = ajax.loadXML('/web_tour/static/src/xml/tip.xml', QWeb);
                }

                var def = $.Deferred();
                $(function () {
                    /**
                     * Once the DOM is ready, we still have to wait all the modules are loaded before completing the tours
                     * registration and starting listening for DOM mutations.
                     */
                     $.when(load_def).then(function () {
                         _.defer(function () {
                            tour._register_all(observe);
                            if (observe) {
                                observer.observe(document.body, {
                                    attributes: true,
                                    childList: true,
                                    subtree: true,
                                });
                            }
                            def.resolve();
                        });
                    });
                });
                return def;
            };
        })();

        // Enable the MutationObserver for the admin or if a tour is running, when the DOM is ready
        start_service(session.is_superuser || tour.running_tour);

        // Override the TourManager so that it enables/disables the observer when necessary
        if (!session.is_superuser) {
            var run = tour.run;
            tour.run = function () {
                var self = this;
                var args = arguments;

                start_service(true).then(function () {
                    run.apply(self, args);
                    if (!self.running_tour) {
                        observer.disconnect();
                    }
                });
            };
            var _consume_tour = tour._consume_tour;
            tour._consume_tour = function () {
                _consume_tour.apply(this, arguments);
                observer.disconnect();
            };
        }

        return tour;
    });
});

});
