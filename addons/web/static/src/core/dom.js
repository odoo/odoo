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
     * @param {Array} [fromEl] - the  element(s) from which to search
     * @param {string} selector - the CSS selector to match
     * @param {boolean} [addBack=false] - whether or not the fromEl element
     *                                  should be considered in the results
     * @returns {HtmlElements}
     */
    cssFind: function (fromEl, selector, addBack) {
        var resultEls = [];

        if (!selector) {
            return resultEls;
        }
        // No way to correctly parse a complex jQuery selector but having no
        // spaces should be a good-enough condition to use a simple find
        var multiParts = selector.indexOf(" ") >= 0;
        if (multiParts && fromEl.length) {
            const els = fromEl[0].closest("body")?.querySelectorAll(selector) || [];
            resultEls = [...els].filter((el) => [...fromEl].includes(el));
        } else {
            for (const el of fromEl) {
                resultEls = resultEls.concat([...el.querySelectorAll(selector)]);
            }
        }

        if (addBack && [...fromEl].some((el) => el.matches(selector))) {
            resultEls = resultEls.concat([...fromEl]);
        }

        return resultEls;
    },

    // TODO: If needed DIVY
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
     * @returns {Element}
     */
    renderButton: function (options) {
        const ElementParams = Object.assign(
            {
                type: "button",
            },
            options.attrs || {}
        );

        let extraClasses = ElementParams.class;
        if (extraClasses) {
            // If we got extra classes, check if old oe_highlight/oe_link
            // classes are given and switch them to the right classes (those
            // classes have no style associated to them anymore).
            // TODO ideally this should be dropped at some point.
            extraClasses = extraClasses
                .replace(/\boe_highlight\b/g, "btn-primary")
                .replace(/\boe_link\b/g, "btn-link");
        }

        ElementParams.class = "btn";
        if (options.size) {
            ElementParams.class += " btn-" + options.size;
        }
        ElementParams.class += " " + (extraClasses || "btn-secondary");

        const buttonEl = document.createElement("button");
        for (var key in ElementParams) {
            if (Object.prototype.hasOwnProperty.call(ElementParams, key)) {
                buttonEl.setAttribute(key, ElementParams[key]);
            }
        }

        if (options.icon) {
            var iconEl;
            if (options.icon.substr(0, 3) === "fa-") {
                iconEl = document.createElement("i");
                iconEl.className = "fa fa-fw o_button_icon " + options.icon;
            } else {
                iconEl = document.createElement("img");
                iconEl.src = options.icon;
            }
            buttonEl.appendChild(iconEl);
        }
        if (options.text) {
            var textEl = document.createElement("span");
            textEl.textContent = options.text;
            buttonEl.appendChild(textEl);
        }

        return buttonEl;
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
        for (const el of document.querySelectorAll(".o_top_fixed_element")) {
            size += el.outerHeight();
        }
        return size;
    },
};
export default dom;
