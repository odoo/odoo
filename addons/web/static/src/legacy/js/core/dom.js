/** @odoo-module **/

/**
 * DOM Utility helpers
 *
 * We collect in this file some helpers to help integrate various DOM
 * functionalities with the odoo framework.  A common theme in these functions
 * is the use of the main core.bus, which helps the framework react when
 * something happens in the DOM.
 */

import { delay } from "@web/core/utils/concurrency";

var dom = {
    DEBOUNCE: 400,

    /**
     * jQuery find function behavior is::
     *
     *      $('A').find('A B') <=> $('A A B')
     *
     * The searches behavior to find options' DOM needs to be::
     *
     *      $('A').find('A B') <=> $('A B')
     *
     * This is what this function does.
     *
     * @param {jQuery} $from - the jQuery element(s) from which to search
     * @param {string} selector - the CSS selector to match
     * @param {boolean} [addBack=false] - whether or not the $from element
     *                                  should be considered in the results
     * @returns {jQuery}
     */
    cssFind: function ($from, selector, addBack) {
        var $results;

        // No way to correctly parse a complex jQuery selector but having no
        // spaces should be a good-enough condition to use a simple find
        var multiParts = selector.indexOf(' ') >= 0;
        if (multiParts) {
            $results = $from.find('*').filter(selector);
        } else {
            $results = $from.find(selector);
        }

        if (addBack && $from.is(selector)) {
            $results = $results.add($from);
        }

        return $results;
    },
    /**
     * Protects a function which is to be used as a handler by preventing its
     * execution for the duration of a previous call to it (including async
     * parts of that call).
     *
     * Limitation: as the handler is ignored during async actions,
     * the 'preventDefault' or 'stopPropagation' calls it may want to do
     * will be ignored too. Using the 'preventDefault' and 'stopPropagation'
     * arguments solves that problem.
     *
     * @param {function} fct
     *      The function which is to be used as a handler. If a promise
     *      is returned, it is used to determine when the handler's action is
     *      finished. Otherwise, the return is used as jQuery uses it.
     * @param {function|boolean} preventDefault
     * @param {function|boolean} stopPropagation
     */
    makeAsyncHandler: function (fct, preventDefault, stopPropagation) {
        var pending = false;
        function _isLocked() {
            return pending;
        }
        function _lock() {
            pending = true;
        }
        function _unlock() {
            pending = false;
        }
        return function (ev) {
            if (preventDefault === true || preventDefault && preventDefault()) {
                ev.preventDefault();
            }
            if (stopPropagation === true || stopPropagation && stopPropagation()) {
                ev.stopPropagation();
            }

            if (_isLocked()) {
                // If a previous call to this handler is still pending, ignore
                // the new call.
                return;
            }

            _lock();
            var result = fct.apply(this, arguments);
            Promise.resolve(result).finally(_unlock);
            return result;
        };
    },
    /**
     * Creates a debounced version of a function to be used as a button click
     * handler. Also improves the handler to disable the button for the time of
     * the debounce and/or the time of the async actions it performs.
     *
     * Limitation: if two handlers are put on the same button, the button will
     * become enabled again once any handler's action finishes (multiple click
     * handlers should however not be binded to the same button).
     *
     * @param {function} fct
     *      The function which is to be used as a button click handler. If a
     *      promise is returned, it is used to determine when the button can be
     *      re-enabled. Otherwise, the return is used as jQuery uses it.
     */
    makeButtonHandler: function (fct) {
        // Fallback: if the final handler is not binded to a button, at least
        // make it an async handler (also handles the case where some events
        // might ignore the disabled state of the button).
        fct = dom.makeAsyncHandler(fct);

        return function (ev) {
            var result = fct.apply(this, arguments);

            var $button = $(ev.target).closest('.btn');
            if (!$button.length) {
                return result;
            }

            // Disable the button for the duration of the handler's action
            // or at least for the duration of the click debounce. This makes
            // a 'real' debounce creation useless. Also, during the debouncing
            // part, the button is disabled without any visual effect.
            $button.addClass('pe-none');
            Promise.resolve(dom.DEBOUNCE && delay(dom.DEBOUNCE)).then(function () {
                $button.removeClass('pe-none');
                const restore = dom.addButtonLoadingEffect($button[0]);
                return Promise.resolve(result).finally(restore);
            });

            return result;
        };
    },
    /**
     * Gives the button a loading effect by disabling it and adding a `fa`
     * spinner icon.
     * The existing button `fa` icons will be hidden through css.
     *
     * @param {HTMLElement} btn - the button to disable/load
     * @return {function} a callback function that will restore the button
     *         initial state
     */
    addButtonLoadingEffect: function (btn) {
        const $btn = $(btn);
        $btn.addClass('o_website_btn_loading disabled');
        $btn.prop('disabled', true);
        const $loader = $('<span/>', {
            class: 'fa fa-refresh fa-spin me-2',
        });
        $btn.prepend($loader);
        return () => {
             $btn.removeClass('o_website_btn_loading disabled');
             $btn.prop('disabled', false);
             $loader.remove();
        };
    },
    /**
     * Renders a button with standard odoo template. This does not use any xml
     * template to avoid forcing the frontend part to lazy load a xml file for
     * each widget which might want to create a simple button.
     *
     * @param {Object} options
     * @param {Object} [options.attrs] - Attributes to put on the button element
     * @param {string} [options.attrs.type='button']
     * @param {string} [options.attrs.class='btn-secondary']
     *        Note: automatically completed with "btn btn-X"
     *        (@see options.size for the value of X)
     * @param {string} [options.size] - @see options.attrs.class
     * @param {string} [options.icon]
     *        The specific fa icon class (for example "fa-home") or an URL for
     *        an image to use as icon.
     * @param {string} [options.text] - the button's text
     * @returns {jQuery}
     */
    renderButton: function (options) {
        var jQueryParams = Object.assign({
            type: 'button',
        }, options.attrs || {});

        var extraClasses = jQueryParams.class;
        if (extraClasses) {
            // If we got extra classes, check if old oe_highlight/oe_link
            // classes are given and switch them to the right classes (those
            // classes have no style associated to them anymore).
            // TODO ideally this should be dropped at some point.
            extraClasses = extraClasses.replace(/\boe_highlight\b/g, 'btn-primary')
                                       .replace(/\boe_link\b/g, 'btn-link');
        }

        jQueryParams.class = 'btn';
        if (options.size) {
            jQueryParams.class += (' btn-' + options.size);
        }
        jQueryParams.class += (' ' + (extraClasses || 'btn-secondary'));

        var $button = $('<button/>', jQueryParams);

        if (options.icon) {
            if (options.icon.substr(0, 3) === 'fa-') {
                $button.append($('<i/>', {
                    class: 'fa fa-fw o_button_icon ' + options.icon,
                }));
            } else {
                $button.append($('<img/>', {
                    src: options.icon,
                }));
            }
        }
        if (options.text) {
            $button.append($('<span/>', {
                text: options.text,
            }));
        }

        return $button;
    },
    /**
     * Computes the size by which a scrolling point should be decreased so that
     * the top fixed elements of the page appear above that scrolling point.
     *
     * @return {Document} [document=window.document]
     * @returns {number}
     */
    scrollFixedOffset(document = window.document) {
        let size = 0;
        for (const el of document.querySelectorAll('.o_top_fixed_element')) {
            size += $(el).outerHeight();
        }
        return size;
    },
    /**
     * @param {HTMLElement|string} el - the element to scroll to. If "el" is a
     *      string, it must be a valid selector of an element in the DOM or
     *      '#top' or '#bottom'. If it is an HTML element, it must be present
     *      in the DOM.
     *      Limitation: if the element is using a fixed position, this
     *      function cannot work except if is the header (el is then either a
     *      string set to '#top' or an HTML element with the "top" id) or the
     *      footer (el is then a string set to '#bottom' or an HTML element
     *      with the "bottom" id) for which exceptions have been made.
     * @param {number} [options] - same as animate of jQuery
     * @param {number} [options.extraOffset=0]
     *      extra offset to add on top of the automatic one (the automatic one
     *      being computed based on fixed header sizes)
     * @param {number} [options.forcedOffset]
     *      offset used instead of the automatic one (extraOffset will be
     *      ignored too)
     * @param {JQuery} [options.$scrollable] the $element to scroll
     * @return {Promise}
     */
    scrollTo(el, options = {}) {
        if (!el) {
            throw new Error("The scrollTo function was called without any given element");
        }
        const $el = $(el);
        if (typeof(el) === 'string' && $el[0]) {
            el = $el[0];
        }
        const isTopOrBottomHidden = (el === '#top' || el === '#bottom');
        const $scrollable = isTopOrBottomHidden ? $().getScrollingElement() : (options.$scrollable || $el.parent().closestScrollable());
        // If $scrollable and $el are not in the same document, we can safely
        // assume $el is in an $iframe. We retrieve it by filtering the list of
        // iframes in $scrollable to keep only the one that contains $el.
        const scrollDocument = $scrollable[0].ownerDocument;
        const isInOneDocument = isTopOrBottomHidden || scrollDocument === $el[0].ownerDocument;
        const $iframe = !isInOneDocument && $scrollable.find('iframe').filter((i, node) => $(node).contents().has($el));
        const $topLevelScrollable = $().getScrollingElement(scrollDocument);
        const isTopScroll = $scrollable.is($topLevelScrollable);

        function _computeScrollTop() {
            if (el === '#top' || el.id === 'top') {
                return 0;
            }
            if (el === '#bottom' || el.id === 'bottom') {
                return $scrollable[0].scrollHeight - $scrollable[0].clientHeight;
            }

            let offsetTop = $el.offset().top;
            if (el.classList.contains('d-none')) {
                el.classList.remove('d-none');
                offsetTop = $el.offset().top;
                el.classList.add('d-none');
            }
            const isDocScrollingEl = $scrollable.is(el.ownerDocument.scrollingElement);
            let elPosition = offsetTop
                - ($scrollable.offset().top - (isDocScrollingEl ? 0 : $scrollable[0].scrollTop));
            if (!isInOneDocument && $iframe.length) {
                elPosition += $iframe.offset().top;
            }
            let offset = options.forcedOffset;
            if (offset === undefined) {
                offset = (isTopScroll ? dom.scrollFixedOffset(scrollDocument) : 0) + (options.extraOffset || 0);
            }
            return Math.max(0, elPosition - offset);
        }

        const originalScrollTop = _computeScrollTop();

        return new Promise(resolve => {
            const clonedOptions = Object.assign({}, options);

            // During the animation, detect any change needed for the scroll
            // offset. If any occurs, stop the animation and continuing it to
            // the new scroll point for the remaining time.
            // Note: limitation, the animation won't be as fluid as possible if
            // the easing mode is different of 'linear'.
            clonedOptions.progress = function (a, b, remainingMs) {
                if (options.progress) {
                    options.progress.apply(this, ...arguments);
                }
                const newScrollTop = _computeScrollTop();
                if (Math.abs(newScrollTop - originalScrollTop) <= 1.0
                        && (isTopOrBottomHidden || !(el.classList.contains('o_transitioning')))) {
                    return;
                }
                $scrollable.stop();
                dom.scrollTo(el, Object.assign({}, options, {
                    duration: remainingMs,
                    easing: 'linear',
                })).then(() => resolve());
            };

            // Detect the end of the animation to be able to indicate it to
            // the caller via the returned Promise.
            clonedOptions.complete = function () {
                if (options.complete) {
                    options.complete.apply(this, ...arguments);
                }
                resolve();
            };

            $scrollable.animate({scrollTop: originalScrollTop}, clonedOptions);
        });
    },
};
export default dom;
