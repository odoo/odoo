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
 */
function editAndTrigger($el, value, events) {
    if ($el.length !== 1) {
        throw new Error(`target ${$el.selector} has length ${$el.length} instead of 1`);
    }
    $el.val(value);
    events.forEach(function (event) {
        $el.trigger(event);
    });
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
 */
function editInput($el, value) {
    editAndTrigger($el, value, ['input']);
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
 */
function editSelect($el, value) {
    editAndTrigger($el, value, ['change']);
}

/**
 * Click to open the dropdown on a many2one
 *
 * @param {string} fieldName
 * @param {[string]} selector if set, this will restrict the search for the m2o
 *    input
 * @returns {HTMLInputElement} the main many2one input
 */
function clickOpenM2ODropdown(fieldName, selector) {
    var m2oSelector = `${selector || ''} .o_field_many2one[name=${fieldName}] input`;
    var matches = document.querySelectorAll(m2oSelector);
    if (matches.length !== 1) {
        throw new Error(`cannot open m2o: selector ${selector} has been found ${matches.length} instead of 1`);
    }
    matches[0].click();
    return matches[0];
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
 */
function clickM2OItem(fieldName, searchText) {
    var m2oSelector = `.o_field_many2one[name=${fieldName}] input`;
    var $dropdown = $(m2oSelector).autocomplete('widget');
    var $target = $dropdown.find(`li:contains(${searchText})`).first();
    if ($target.length !== 1 || !$target.is(':visible')) {
        throw new Error('Menu item should be unique and visible');
    }
    $target.mouseenter().click();
}

/**
 * This helper is useful to test many2one fields. Here is what it does:
 * - click to open the dropdown
 * - enter a search string in the input
 * - wait for the selection
 * - click on the active menuitem
 *
 * Example:
 *    testUtils.fields.many2one.searchAndClickM2OItem('partner_id', 'George');
 *
 * @param {string} fieldName
 * @param {[Object]} options
 * @param {[string]} options.selector
 * @param {[string]} options.search
 * @returns {Promise}
 */
function searchAndClickM2OItem(fieldName, options) {
    options = options || {};

    var input = clickOpenM2ODropdown(fieldName, options.selector);

    var def;
    if (options.search) {
        // jquery autocomplete refines the search in a setTimeout() parameterized
        // with a delay, so we force this delay to 0 s.t. the dropdown is filtered
        // directly on the next tick
        var $input = $(input);
        var delay = $input.autocomplete('option', 'delay');
        $input.autocomplete('option', 'delay', 0);
        input.value = options.search;
        input.dispatchEvent(new Event('input'));
        $input.autocomplete('option', 'delay', delay);
        def = concurrency.delay(0);
    }

    return $.when(def).then(function () {
        clickM2OHighlightedItem(fieldName, options.selector);
    });
}
return {
    clickOpenM2ODropdown: clickOpenM2ODropdown,
    clickM2OHighlightedItem: clickM2OHighlightedItem,
    clickM2OItem: clickM2OItem,
    editAndTrigger: editAndTrigger,
    editInput: editInput,
    editSelect: editSelect,
    searchAndClickM2OItem: searchAndClickM2OItem,
};

});
