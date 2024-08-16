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
};
export default dom;
