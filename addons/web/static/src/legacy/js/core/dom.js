/**
 * DOM Utility helpers
 *
 * We collect in this file some helpers to help integrate various DOM
 * functionalities with the odoo framework.  A common theme in these functions
 * is the use of the main core.bus, which helps the framework react when
 * something happens in the DOM.
 */


var dom = {
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
            $results = $from.closest('body').find(selector).filter((i, $el) => $from.has($el).length);
        } else {
            $results = $from.find(selector);
        }

        if (addBack && $from.is(selector)) {
            $results = $results.add($from);
        }

        return $results;
    },

    // Helper function to determine if an element is scrollable
    isScrollable(element) {
        if (!element) {
            return false;
        }
        const overflowY = window.getComputedStyle(element).overflowY;
        return overflowY === 'auto' || overflowY === 'scroll' ||
            (overflowY === 'visible' && element === element.ownerDocument.scrollingElement);
    },

    /**
     * Finds the closest scrollable element for the given element.
     *
     * @param {Element} element - The element to find the closest scrollable element for.
     * @returns {Element} The closest scrollable element.
     */
    closestScrollable(element) {
        const document = element.ownerDocument || window.document;

        while (element && element !== document.scrollingElement) {
            if (element instanceof Document) {
                return null;
            }
            if (dom.isScrollable(element)) {
                return element;
            }
            element = element.parentElement;
        }
        return element || document.scrollingElement;
    },

    /**
     * Computes the size by which a scrolling point should be decreased so that
     * the top fixed elements of the page appear above that scrolling point.
     *
     * @param {Document} [doc=document]
     * @returns {number}
     */
    scrollFixedOffset(doc = document) {
        let size = 0;
        const elements = doc.querySelectorAll('.o_top_fixed_element');

        elements.forEach(el => {
            size += el.offsetHeight;
        });

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
     * @param {number} [options] - options for the scroll behavior
     * @param {number} [options.extraOffset=0]
     *      extra offset to add on top of the automatic one (the automatic one
     *      being computed based on fixed header sizes)
     * @param {number} [options.forcedOffset]
     *      offset used instead of the automatic one (extraOffset will be
     *      ignored too)
     * @param {HTMLElement} [options.scrollable] the element to scroll
     * @return {Promise}
     */
    scrollTo(el, options = {}) {
        if (!el) {
            throw new Error("The scrollTo function was called without any given element");
        }
        if (typeof el === 'string') {
            el = document.querySelector(el);
        }
        const isTopOrBottomHidden = (el.id === 'top' || el.id === 'bottom');
        const scrollable = isTopOrBottomHidden ? document.scrollingElement : (options.scrollable || dom.closestScrollable(el.parentElement));
        const scrollDocument = scrollable.ownerDocument;
        const isInOneDocument = isTopOrBottomHidden || scrollDocument === el.ownerDocument;
        const iframe = !isInOneDocument && Array.from(scrollable.querySelectorAll('iframe')).find(node => node.contentDocument.contains(el));
        const topLevelScrollable = scrollDocument.scrollingElement;

        function _computeScrollTop() {
            if (el.id === 'top') {
                return 0;
            }
            if (el.id === 'bottom') {
                return scrollable.scrollHeight - scrollable.clientHeight;
            }

            let offsetTop = el.getBoundingClientRect().top + window.scrollY;
            if (el.classList.contains('d-none')) {
                el.classList.remove('d-none');
                offsetTop = el.getBoundingClientRect().top + window.scrollY;
                el.classList.add('d-none');
            }
            const isDocScrollingEl = scrollable === el.ownerDocument.scrollingElement;
            let elPosition = offsetTop - (scrollable.getBoundingClientRect().top - (isDocScrollingEl ? 0 : scrollable.scrollTop));
            if (!isInOneDocument && iframe) {
                elPosition += iframe.getBoundingClientRect().top + window.scrollY;
            }
            let offset = options.forcedOffset;
            if (offset === undefined) {
                offset = (scrollable === topLevelScrollable ? dom.scrollFixedOffset(scrollDocument) : 0) + (options.extraOffset || 0);
            }
            return Math.max(0, elPosition - offset);
        }

        const originalScrollTop = _computeScrollTop();

        return new Promise(resolve => {
            const start = scrollable.scrollTop;
            const change = originalScrollTop - start;
            const duration = options.duration || 600;
            const startTime = performance.now();

            function animateScroll(currentTime) {
                const elapsedTime = currentTime - startTime;
                const progress = Math.min(elapsedTime / duration, 1);
                const easeInOutQuad = progress < 0.5 ? 2 * progress * progress : 1 - Math.pow(-2 * progress + 2, 2) / 2;
                const newScrollTop = start + change * easeInOutQuad;

                scrollable.scrollTop = newScrollTop;

                if (elapsedTime < duration) {
                    requestAnimationFrame(animateScroll);
                } else {
                    resolve();
                }
            }

            requestAnimationFrame(animateScroll);
        });
    },
};
export default dom;
