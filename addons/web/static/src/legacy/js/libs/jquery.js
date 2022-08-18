/** @odoo-module **/

/**
 * The jquery library extensions and fixes should be done here to avoid patching
 * in place.
 */

// jQuery selectors extensions
$.extend($.expr[':'], {
    data: function (element, index, matches) {
        return $(element).data(matches[3]);
    },
});

// jQuery functions extensions
$.fn.extend({
    /**
     * Makes DOM elements bounce the way Odoo decided it.
     *
     * @param {string} [extraClass]
     */
    odooBounce: function (extraClass) {
        for (const el of this) {
            el.classList.add('o_catch_attention', extraClass);
            setTimeout(() => el.classList.remove('o_catch_attention', extraClass), 400);
        }
        return this;
    },
    /**
     * Allows to bind events to a handler just as the standard `$.on` function
     * but binds the handler so that it is executed before any already-attached
     * handler for the same events.
     *
     * @see jQuery.on
     */
    prependEvent: function (events, selector, data, handler) {
        this.on.apply(this, arguments);

        events = events.split(' ');
        return this.each(function () {
            var el = this;
            events.forEach((evNameNamespaced) => {
                var evName = evNameNamespaced.split('.')[0];
                var handler = $._data(el, 'events')[evName].pop();
                $._data(el, 'events')[evName].unshift(handler);
            });
        });
    },
    /**
     * @deprecated this will soon be removed: just rely on the fact that the
     * scrollbar is at its natural position.
     * @returns {jQuery}
     */
    getScrollingElement(document = window.document) {
        const $baseScrollingElement = $(document.scrollingElement);
        if ($baseScrollingElement.isScrollable()
                && $baseScrollingElement.hasScrollableContent()) {
            return $baseScrollingElement;
        }
        const bodyHeight = $(document.body).height();
        for (const el of document.body.children) {
            // Search for a body child which is at least as tall as the body
            // and which has the ability to scroll if enough content in it. If
            // found, suppose this is the top scrolling element.
            if (bodyHeight - el.scrollHeight > 1.5) {
                continue;
            }
            const $el = $(el);
            if ($el.isScrollable()) {
                return $el;
            }
        }
        return $baseScrollingElement;
    },
    /**
     * @deprecated this will soon be removed: just rely on the fact that the
     * scrollbar is at its natural position.
     * @returns {jQuery}
     */
    getScrollingTarget(contextItem = window.document) {
        // Cannot use `instanceof` because of cross-frame issues.
        const isElement = obj => obj && obj.nodeType === Node.ELEMENT_NODE;
        const isJQuery = obj => obj && ('jquery' in obj);

        const $scrollingElement = isElement(contextItem)
            ? $(contextItem)
            : isJQuery(contextItem)
            ? contextItem
            : $().getScrollingElement(contextItem);
        const document = $scrollingElement[0].ownerDocument;
        return $scrollingElement.is(document.scrollingElement)
            ? $(document.defaultView)
            : $scrollingElement;
    },
    /**
     * @return {boolean}
     */
    hasScrollableContent() {
        return this[0].scrollHeight > this[0].clientHeight;
    },
    /**
     * @returns {boolean}
     */
    isScrollable() {
        if (!this.length) {
            return false;
        }
        const overflow = this.css('overflow-y');
        const el = this[0];
        return overflow === 'auto' || overflow === 'scroll'
            || (overflow === 'visible' && el === el.ownerDocument.scrollingElement);
    },
});

// jQuery functions monkey-patching

// Some magic to ensure scrollTop and animate on html/body animate the top level
// scrollable element even if not html or body. Note: we should consider
// removing this as it was only really needed when the #wrapwrap was the one
// with the scrollbar. Although the rest of the code still use
// getScrollingElement to be generic so this is consistent. Maybe all of this
// can live on as long as we continue using jQuery a lot. We can decide of the
// fate of getScrollingElement and related code the moment we get rid of jQuery.
const originalScrollTop = $.fn.scrollTop;
$.fn.scrollTop = function (value) {
    if (value !== undefined && this.filter('html, body').length) {
        // The caller wants to scroll a set of elements including html and/or
        // body to a specific point -> do that but make sure to add the real
        // top level element to that set of elements if any different is found.
        const $withRealScrollable = this.not('html, body').add($().getScrollingElement(this[0].ownerDocument));
        originalScrollTop.apply($withRealScrollable, arguments);
        return this;
    } else if (value === undefined && this.eq(0).is('html, body')) {
        // The caller wants to get the scroll point of a set of elements, jQuery
        // will return the scroll point of the first one, if it is html or body
        // return the scroll point of the real top level element.
        return originalScrollTop.apply($().getScrollingElement(this[0].ownerDocument), arguments);
    }
    return originalScrollTop.apply(this, arguments);
};
const originalAnimate = $.fn.animate;
$.fn.animate = function (properties, ...rest) {
    const props = Object.assign({}, properties);
    if ('scrollTop' in props && this.filter('html, body').length) {
        // The caller wants to scroll a set of elements including html and/or
        // body to a specific point -> do that but make sure to add the real
        // top level element to that set of elements if any different is found.
        const $withRealScrollable = this.not('html, body').add($().getScrollingElement(this[0].ownerDocument));
        originalAnimate.call($withRealScrollable, {'scrollTop': props['scrollTop']}, ...rest);
        delete props['scrollTop'];
    }
    if (!Object.keys(props).length) {
        return this;
    }
    return originalAnimate.call(this, props, ...rest);
};
