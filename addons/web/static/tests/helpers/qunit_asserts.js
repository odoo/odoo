odoo.define('web.qunit_asserts', function (require) {
    "use strict";

    /**
     * In this file, we extend QUnit by adding some specialized assertions. The goal
     * of these new assertions is twofold:
     * - ease of use: they should allow us to simplify some common complex assertions
     * - safer: these assertions will fail when some preconditions are not met.
     *
     * For example, the assert.isVisible assertion will also check that the target
     * matches exactly one element.
     */

    const Widget = require('web.Widget');

    /** @todo use testUtilsDom.getNode to extract the element from the 'w' argument */

    //-------------------------------------------------------------------------
    // Private functions
    //-------------------------------------------------------------------------

    /**
     * Helper function, to check if a given element
     * - is unique (if it is a jquery node set)
     * - has (or has not) a css class
     *
     * @private
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} className
     * @param {boolean} shouldHaveClass
     * @param {string} [msg]
     */
    function _checkClass(w, className, shouldHaveClass, msg) {
        if (w instanceof jQuery && w.length !== 1) {
            const assertion = shouldHaveClass ? 'hasClass' : 'doesNotHaveClass';
            QUnit.assert.ok(false, `Assertion '${assertion} ${className}' targets ${w.length} elements instead of 1`);
        }

        const el = w instanceof Widget || w instanceof owl.Component ? w.el :
            w instanceof jQuery ? w[0] : w;

        msg = msg || `target should ${shouldHaveClass ? 'have' : 'not have'} class ${className}`;
        const isFalse = className.split(" ").some(cls => {
            const hasClass = el.classList.contains(cls);
            return shouldHaveClass ? !hasClass : hasClass;
        });
        QUnit.assert.ok(!isFalse, msg);
    }

    /**
     * Helper function, to check if a given element
     * - is unique (if it is a jquery node set)
     * - is (or not) visible
     *
     * @private
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {boolean} shouldBeVisible
     * @param {string} [msg]
     */
    function _checkVisible(w, shouldBeVisible, msg) {
        if (w instanceof jQuery && w.length !== 1) {
            const assertion = shouldBeVisible ? 'isVisible' : 'isNotVisible';
            QUnit.assert.ok(false, `Assertion '${assertion}' targets ${w.length} elements instead of 1`);
        }

        const el = w instanceof Widget || w instanceof owl.Component ? w.el :
            w instanceof jQuery ? w[0] : w;

        msg = msg || `target should ${shouldBeVisible ? '' : 'not'} be visible`;
        let isVisible = el &&
            el.offsetWidth &&
            el.offsetHeight;
        if (isVisible) {
            // This computation is a little more heavy and we only want to perform it
            // if the above assertion has failed.
            const rect = el.getBoundingClientRect();
            isVisible = rect.width + rect.height;
        }
        const condition = shouldBeVisible ? isVisible : !isVisible;
        QUnit.assert.ok(condition, msg);
    }

    //-------------------------------------------------------------------------
    // Public functions
    //-------------------------------------------------------------------------

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * contains exactly n matches for the selector.
     *
     * Example: assert.containsN(document.body, '.modal', 0)
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} selector
     * @param {number} n
     * @param {string} [msg]
     */
    function containsN(w, selector, n, msg) {
        if (typeof n !== 'number') {
            throw new Error("containsN assert should be called with a number as third argument");
        }
        let matches = [];
        if (w instanceof owl.Component) {
            if (!w.el) {
                throw new Error(`containsN assert with selector '${selector}' called on an unmounted component`);
            }
            matches = w.el.querySelectorAll(selector);
        } else {
            const $el = w instanceof Widget ? w.$el :
                w instanceof HTMLElement ? $(w) :
                    w;  // jquery element
            matches = $el.find(selector);
        }
        if (!msg) {
            msg = `Selector '${selector}' should have exactly ${n} matches (inside the target)`;
        }
        QUnit.assert.strictEqual(matches.length, n, msg);
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * contains exactly 0 match for the selector.
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} selector
     * @param {string} [msg]
     */
    function containsNone(w, selector, msg) {
        containsN(w, selector, 0, msg);
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * contains exactly 1 match for the selector.
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} selector
     * @param {string} [msg]
     */
    function containsOnce(w, selector, msg) {
        containsN(w, selector, 1, msg);
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * - exists
     * - is unique
     * - has the given class (specified by className)
     *
     * Note that it uses the hasClass jQuery method, so it can be used to check the
     * presence of more than one class ('some-class other-class'), but it is a
     * little brittle, because it depends on the order of these classes:
     *
     *  div.a.b.c: has class 'a b c', but does not have class 'a c b'
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} className
     * @param {string} [msg]
     */
    function hasClass(w, className, msg) {
        _checkClass(w, className, true, msg);
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * - exists
     * - is unique
     * - does not have the given class (specified by className)
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} className
     * @param {string} [msg]
     */
    function doesNotHaveClass(w, className, msg) {
        _checkClass(w, className, false, msg);
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * - exists
     * - is unique
     * - has the given attribute with the proper value
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} attr
     * @param {string} value
     * @param {string} [msg]
     */
    function hasAttrValue(w, attr, value, msg) {
        const $el = w instanceof Widget ? w.$el :
            w instanceof HTMLElement ? $(w) :
                w;  // jquery element

        if ($el.length !== 1) {
            const descr = `hasAttrValue (${attr}: ${value})`;
            QUnit.assert.ok(false,
                `Assertion '${descr}' targets ${$el.length} elements instead of 1`
            );
        } else {
            msg = msg || `attribute '${attr}' of target should be '${value}'`;
            QUnit.assert.strictEqual($el.attr(attr), value, msg);
        }
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * - exists
     * - is visible (as far as jQuery can tell: not in display none, ...)
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} [msg]
     */
    function isVisible(w, msg) {
        _checkVisible(w, true, msg);
    }

    /**
     * Checks that the target element (described by widget/jquery or html element)
     * - exists
     * - is not visible (as far as jQuery can tell: display none, ...)
     *
     * @param {Widget|jQuery|HTMLElement|owl.Component} w
     * @param {string} [msg]
     */
    function isNotVisible(w, msg) {
        _checkVisible(w, false, msg);
    }

    //-------------------------------------------------------------------------
    // Exposed API
    //-------------------------------------------------------------------------

    QUnit.assert.containsN = containsN;
    QUnit.assert.containsNone = containsNone;
    QUnit.assert.containsOnce = containsOnce;

    QUnit.assert.hasClass = hasClass;
    QUnit.assert.doesNotHaveClass = doesNotHaveClass;

    QUnit.assert.hasAttrValue = hasAttrValue;

    QUnit.assert.isVisible = isVisible;
    QUnit.assert.isNotVisible = isNotVisible;
});
