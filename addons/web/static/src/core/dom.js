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
     *      document.querySelector('A').querySelectorAll('A B') <=> document.querySelectorAll('A A B')
     *
     * The searches behavior to find options' DOM needs to be::
     *
     *      document.querySelector('A').querySelectorAll('A B') <=> document.querySelectorAll('A B')
     *
     * This is what this function does.
     *
     * @param {Array|NodeList|Element} fromEl - The element(s) from which to search.
     * @param {string} selector - The CSS selector to match.
     * @param {boolean} [addBack=false] - Whether or not the fromEl element
     *                                    should be considered in the results.
     * @returns {Array<Element>} - The matched elements.
     */
    cssFind: function (fromEl, selector, addBack) {
        const resultEls = [];

        // If no selector or fromEl, return an empty array
        if (!selector || !fromEl) {
            return resultEls;
        }

        // Normalize fromEl to always be an array
        if (!(fromEl instanceof NodeList || Array.isArray(fromEl))) {
            fromEl = [fromEl];
        } else {
            fromEl = Array.from(fromEl);
        }

        // No way to correctly parse a complex jQuery selector but having no
        // spaces should be a good-enough condition to use a simple find
        const multiParts = selector.indexOf(" ") >= 0;
        if (multiParts) {
            fromEl.forEach((el) => {
                // Note: Why we targeted body in closest, we can make this more
                // faster & clear by targeting parentNode?
                const children = Array.from(el.closest("body")?.querySelectorAll(selector)).filter(
                    (e) => el.contains(e)
                );
                resultEls.push(...children);
            });
        } else {
            for (const el of fromEl) {
                resultEls.push(...Array.from(el.querySelectorAll(selector)));
            }
        }

        if (addBack) {
            const addBackEls = fromEl.filter((el) => el.matches(selector));
            resultEls.push(...addBackEls);
        }

        return resultEls;
    },
};
export default dom;
