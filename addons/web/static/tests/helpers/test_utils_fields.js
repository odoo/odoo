odoo.define('web.test_utils_fields', function (require) {
"use strict";

/**
 * Field Test Utils
 *
 * This module defines various utility functions to help testing field widgets.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */

var concurrency = require('web.concurrency');
var domUtils = require('web.test_utils_dom');

//------------------------------------------------------------------------------
// Public functions
//------------------------------------------------------------------------------

/**
 * Sets the value of an element and then, trigger all specified events.
 * Note that this helper also checks the unicity of the target.
 *
 * Example:
 *     testUtils.fields.editAndTrigger($('selector'), 'test', ['input', 'change']);
 *
 * @param {jQuery} $el should target an input, textarea or select
 * @param {string|number} value
 * @param {string[]} events
 * @returns {Promise}
 */
function editAndTrigger($el, value, events) {
    if ($el.length !== 1) {
        throw new Error(`target ${$el.selector} has length ${$el.length} instead of 1`);
    }
    $el.val(value);
    return domUtils.triggerEvents($el, events);
}

/**
 * Sets the value of an input.
 *
 * Note that this helper also checks the unicity of the target.
 *
 * Example:
 *     testUtils.fields.editInput($('selector'), 'somevalue');
 *
 * @param {jQuery} $el
 * @param {string|number} value
 * @returns {Promise}
 */
function editInput($el, value) {
    return editAndTrigger($el, value, ['input']);
}

/**
 * Sets the value of a select.
 *
 * Note that this helper also checks the unicity of the target.
 *
 * Example:
 *     testUtils.fields.editSelect($('selector'), 'somevalue');
 *
 * @param {jQuery} $el
 * @param {string|number} value
 * @returns {Promise}
 */
function editSelect($el, value) {
    return editAndTrigger($el, value, ['change']);
}

/**
 * Click to open the dropdown on a many2one
 *
 * @param {string} fieldName
 * @param {[string]} selector if set, this will restrict the search for the m2o
 *    input
 * @returns {HTMLInputElement} the main many2one input
 */
async function clickOpenM2ODropdown(fieldName, selector) {
    var m2oSelector = `${selector || ''} .o_field_many2one[name=${fieldName}] input`;
    var matches = document.querySelectorAll(m2oSelector);
    if (matches.length !== 1) {
        throw new Error(`cannot open m2o: selector ${selector} has been found ${matches.length} instead of 1`);
    }
    matches[0].click();
    return await concurrency.delay(0).then(function () {
        return matches[0];
    });
}

/**
 * Click on the active (highlighted) selection in a m2o dropdown.
 *
 * @param {string} fieldName
 * @param {[string]} selector if set, this will restrict the search for the m2o
 *    input
 */
function clickM2OHighlightedItem(fieldName, selector) {
    var m2oSelector = `${selector || ''} .o_field_many2one[name=${fieldName}] input`;
    var $dropdown = $(m2oSelector).autocomplete('widget');
    // clicking on an li (no matter which one), will select the focussed one
    $dropdown.find('li:first()').click();
    return concurrency.delay(0);
}

/**
 * Click on a menuitem in the m2o dropdown.  This helper will target an element
 * which contains some specific text. Note that it assumes that the dropdown
 * is currently open.
 *
 * Example:
 *    testUtils.fields.many2one.clickM2OItem('partner_id', 'George');
 *
 * @param {string} fieldName
 * @param {string} searchText
 * @returns {Promise}
 */
function clickM2OItem(fieldName, searchText) {
    var m2oSelector = `.o_field_many2one[name=${fieldName}] input`;
    var $dropdown = $(m2oSelector).autocomplete('widget');
    var $target = $dropdown.find(`li:contains(${searchText})`).first();
    if ($target.length !== 1 || !$target.is(':visible')) {
        throw new Error('Menu item should be unique and visible');
    }
    $target.mouseenter();
    $target.click();

    return concurrency.delay(0);
}

/**
 * This helper is useful to test many2one fields. Here is what it does:
 * - click to open the dropdown
 * - enter a search string in the input
 * - wait for the selection
 * - click on the requested menuitem, or the active one by default
 *
 * Example:
 *    testUtils.fields.many2one.searchAndClickM2OItem('partner_id', {search: 'George'});
 *
 * @param {string} fieldName
 * @param {[Object]} options
 * @param {[string]} options.selector
 * @param {[string]} options.search
 * @param {[string]} options.item
 * @returns {Promise}
 */
function searchAndClickM2OItem(fieldName, options) {
    options = options || {};

    return clickOpenM2ODropdown(fieldName, options.selector).then(function (input) {
        var def;
        if (options.search) {
            input.value = options.search;
            input.dispatchEvent(new Event('input'));
            def = concurrency.delay(0);
        }
        return Promise.resolve(def).then(function () {
            if (options.item) {
                return clickM2OItem(fieldName, options.item);
            } else {
                return clickM2OHighlightedItem(fieldName, options.selector);
            }
        });
    });
}

/**
 * Helper to trigger a key event on an element.
 *
 * @param {string} type type of key event ('press', 'up' or 'down')
 * @param {jQuery} $el
 * @param {number|string} keyCode used as number, but if string, it'll check if
 *   the string corresponds to a key -otherwise it will keep only the first
 *   char to get a letter key- and convert it into a keyCode.
 * @returns {Promise}
 */
function triggerKey(type, $el, keyCode) {
    type = 'key' + type;
    if (typeof keyCode === 'string') {
        if (keyCode.length > 1) {
            keyCode = keyCode.toUpperCase();
            keyCode = $.ui.keyCode[keyCode];
        } else {
            keyCode = keyCode.charCodeAt(0);
        }
    }
    $el.trigger({type: type, which: keyCode, keyCode: keyCode});
    return concurrency.delay(0);
}

/**
 * Helper to trigger a keydown event on an element.
 *
 * @param {jQuery} $el
 * @param {number|string} keyCode @see triggerKey
 * @returns {Promise}
 */
function triggerKeydown($el, keyCode) {
    return triggerKey('down', $el, keyCode);
}

/**
 * Helper to trigger a keyup event on an element.
 *
 * @param {jQuery} $el
 * @param {number|string} keyCode @see triggerKey
 * @returns {Promise}
 */
function triggerKeyup($el, keyCode) {
    return triggerKey('up', $el, keyCode);
}

return {
    clickOpenM2ODropdown: clickOpenM2ODropdown,
    clickM2OHighlightedItem: clickM2OHighlightedItem,
    clickM2OItem: clickM2OItem,
    editAndTrigger: editAndTrigger,
    editInput: editInput,
    editSelect: editSelect,
    searchAndClickM2OItem: searchAndClickM2OItem,
    triggerKey: triggerKey,
    triggerKeydown: triggerKeydown,
    triggerKeyup: triggerKeyup,
};

});
