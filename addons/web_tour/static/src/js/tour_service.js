odoo.define('web_tour.tour', function (require) {
"use strict";

var rootWidget = require('root.widget');
var rpc = require('web.rpc');
var session = require('web.session');
var TourManager = require('web_tour.TourManager');
const { device } = require('web.config');

const untrackedClassnames = ["o_tooltip", "o_tooltip_content", "o_tooltip_overlay"];

/**
 * @namespace
 * @property {Object} active_tooltips
 * @property {Object} tours
 * @property {Array} consumed_tours
 * @property {String} running_tour
 * @property {Number} running_step_delay
 * @property {'community' | 'enterprise'} edition
 * @property {Array} _log
 */
return session.is_bound.then(function () {
    var defs = [];
    // Load the list of consumed tours and the tip template only if we are admin, in the frontend,
    // tours being only available for the admin. For the backend, the list of consumed is directly
    // in the page source.
    if (session.is_frontend && session.is_admin) {
        var def = rpc.query({
                model: 'web_tour.tour',
                method: 'get_consumed_tours',
            });
        defs.push(def);
    }
    return Promise.all(defs).then(function (results) {
        var consumed_tours = session.is_frontend ? results[0] : session.web_tours;
        const disabled = session.tour_disable || device.isMobile;
        var tour_manager = new TourManager(rootWidget, consumed_tours, disabled);

        // The tests can be loaded inside an iframe. The tour manager should
        // not run in that context, as it will already run in its parent
        // window.
        const isInIframe = window.frameElement && window.frameElement.classList.contains('o_iframe');
        if (isInIframe) {
            return tour_manager;
        }

        function _isTrackedNode(node) {
            if (node.classList) {
                return !untrackedClassnames
                    .some(className => node.classList.contains(className));
            }
            return true;
        }

        const classSplitRegex = /\s+/g;
        const tooltipParentRegex = /\bo_tooltip_parent\b/;
        let currentMutations = [];
        function _processMutations() {
            const hasTrackedMutation = currentMutations.some(mutation => {
                // First check if the mutation applied on an element we do not
                // track (like the tour tips themself).
                if (!_isTrackedNode(mutation.target)) {
                    return false;
                }

                if (mutation.type === 'characterData') {
                    return true;
                }

                if (mutation.type === 'childList') {
                    // If it is a modification to the DOM hierarchy, only
                    // consider the addition/removal of tracked nodes.
                    for (const nodes of [mutation.addedNodes, mutation.removedNodes]) {
                        for (const node of nodes) {
                            if (_isTrackedNode(node)) {
                                return true;
                            }
                        }
                    }
                    return false;
                } else if (mutation.type === 'attributes') {
                    // Get old and new value of the attribute. Note: as we
                    // compute the new value after a setTimeout, this might not
                    // actually be the new value for that particular mutation
                    // record but this is the one after all mutations. This is
                    // normally not an issue: e.g. "a" -> "a b" -> "a" will be
                    // seen as "a" -> "a" (not "a b") + "a b" -> "a" but we
                    // only need to detect *one* tracked mutation to know we
                    // have to update tips anyway.
                    const oldV = mutation.oldValue ? mutation.oldValue.trim() : '';
                    const newV = (mutation.target.getAttribute(mutation.attributeName) || '').trim();

                    // Not sure why but this occurs, especially on ID change
                    // (probably some strange jQuery behavior, see below).
                    // Also sometimes, a class is just considered changed while
                    // it just loses the spaces around the class names.
                    if (oldV === newV) {
                        return false;
                    }

                    if (mutation.attributeName === 'id') {
                        // Check if this is not an ID change done by jQuery for
                        // performance reasons.
                        return !(oldV.includes('sizzle') || newV.includes('sizzle'));
                    } else if (mutation.attributeName === 'class') {
                        // Check if the change is *only* about receiving or
                        // losing the 'o_tooltip_parent' class, which is linked
                        // to the tour service system. We have to check the
                        // potential addition of another class as we compute
                        // the new value after a setTimeout. So this case:
                        // 'a' -> 'a b' -> 'a b o_tooltip_parent' produces 2
                        // mutation records but will be seen here as
                        // 1) 'a' -> 'a b o_tooltip_parent'
                        // 2) 'a b' -> 'a b o_tooltip_parent'
                        const hadClass = tooltipParentRegex.test(oldV);
                        const newClasses = mutation.target.classList;
                        const hasClass = newClasses.contains('o_tooltip_parent');
                        return !(hadClass !== hasClass
                            && Math.abs(oldV.split(classSplitRegex).length - newClasses.length) === 1);
                    }
                }

                return true;
            });

            // Either all the mutations have been ignored or one was detected as
            // tracked and will trigger a tour manager update.
            currentMutations = [];

            // Update the tour manager if required.
            if (hasTrackedMutation) {
                tour_manager.update();
            }
        }

        // Use a MutationObserver to detect DOM changes. When a mutation occurs,
        // only add it to the list of mutations to process and delay the
        // mutation processing. We have to record them all and not in a
        // debounced way otherwise we may ignore tracked ones in a serie of
        // 10 tracked mutations followed by an untracked one. Most of them
        // will trigger a tip check anyway so, most of the time, processing the
        // first ones will be enough to ensure that a tip update has to be done.
        let mutationTimer;
        const observer = new MutationObserver(mutations => {
            clearTimeout(mutationTimer);
            currentMutations = currentMutations.concat(mutations);
            mutationTimer = setTimeout(() => _processMutations(), 750);
        });

        // Now that the observer is configured, we have to start it when needed.
        const observerOptions = {
            attributes: true,
            childList: true,
            subtree: true,
            attributeOldValue: true,
            characterData: true,
        };

        var start_service = (function () {
            return function (observe) {
                return new Promise(function (resolve, reject) {
                    tour_manager._register_all(observe).then(function () {
                        if (observe) {
                            observer.observe(document.body, observerOptions);

                            // If an iframe is added during the tour, its DOM
                            // mutations should also be observed to update the
                            // tour manager.
                            const findIframe = mutations => {
                                for (const mutation of mutations) {
                                    for (const addedNode of Array.from(mutation.addedNodes)) {
                                        if (addedNode.nodeType === Node.ELEMENT_NODE) {
                                            if (addedNode.classList.contains('o_iframe')) {
                                                return addedNode;
                                            }
                                            const iframeChildEl = addedNode.querySelector('.o_iframe');
                                            if (iframeChildEl) {
                                                return iframeChildEl;
                                            }
                                        }
                                    }
                                }
                            };
                            const iframeObserver = new MutationObserver(mutations => {
                                const iframeEl = findIframe(mutations);
                                if (iframeEl) {
                                    iframeEl.addEventListener('load', () => {
                                        observer.observe(iframeEl.contentDocument, observerOptions);
                                    });
                                    // If the iframe was added without a src,
                                    // its load event was immediately fired and
                                    // will not fire again unless another src is
                                    // set. Unfortunately, the case of this
                                    // happening and the iframe content being
                                    // altered programmaticaly may happen.
                                    // (E.g. at the moment this was written,
                                    // the mass mailing editor iframe is added
                                    // without src and its content rewritten
                                    // immediately afterwards).
                                    if (!iframeEl.src) {
                                        observer.observe(iframeEl.contentDocument, observerOptions);
                                    }
                                }
                            });
                            iframeObserver.observe(document.body, { childList: true, subtree: true });
                        }
                        resolve();
                    });
                });
            };
        })();

        // Enable the MutationObserver for the admin or if a tour is running, when the DOM is ready
        start_service(session.is_admin || tour_manager.running_tour);

        // Override the TourManager so that it enables/disables the observer when necessary
        if (!session.is_admin) {
            var run = tour_manager.run;
            tour_manager.run = function () {
                var self = this;
                var args = arguments;

                start_service(true).then(function () {
                    run.apply(self, args);
                    if (!self.running_tour) {
                        observer.disconnect();
                    }
                });
            };
            var _consume_tour = tour_manager._consume_tour;
            tour_manager._consume_tour = function () {
                _consume_tour.apply(this, arguments);
                observer.disconnect();
            };
        }
        // helper to start a tour manually (or from a python test with its counterpart start_tour function)
        odoo.startTour = tour_manager.run.bind(tour_manager);
        return tour_manager;
    });
});

});
