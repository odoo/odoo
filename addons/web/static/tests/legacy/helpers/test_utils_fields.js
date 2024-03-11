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

    const testUtilsDom = require('web.test_utils_dom');

    const ARROW_KEYS_MAPPING = {
        down: 'ArrowDown',
        left: 'ArrowLeft',
        right: 'ArrowRight',
        up: 'ArrowUp',
    };

    //-------------------------------------------------------------------------
    // Public functions
    //-------------------------------------------------------------------------

    /**
     * Autofills the input of a many2one field and clicks on the "Create and Edit" option.
     *
     * @param {string} fieldName
     * @param {string} text Used as default value for the record name
     * @see clickM2OItem
     */
    async function clickM2OCreateAndEdit(fieldName, text = "ABC") {
        await clickOpenM2ODropdown(fieldName);
        const match = document.querySelector(`.o_field_many2one[name=${fieldName}] input`);
        await editInput(match, text);
        return clickM2OItem(fieldName, "Create and Edit");
    }

    /**
     * Click on the active (highlighted) selection in a m2o dropdown.
     *
     * @param {string} fieldName
     * @param {[string]} selector if set, this will restrict the search for the m2o
     *    input
     * @returns {Promise}
     */
    async function clickM2OHighlightedItem(fieldName, selector) {
        const m2oSelector = `${selector || ''} .o_field_many2one[name=${fieldName}] input`;
        const $dropdown = $(m2oSelector).autocomplete('widget');
        // clicking on an li (no matter which one), will select the focussed one
        return testUtilsDom.click($dropdown[0].querySelector('li'));
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
    async function clickM2OItem(fieldName, searchText) {
        const m2oSelector = `.o_field_many2one[name=${fieldName}] input`;
        const $dropdown = $(m2oSelector).autocomplete('widget');
        const $target = $dropdown.find(`li:contains(${searchText})`).first();
        if ($target.length !== 1 || !$target.is(':visible')) {
            throw new Error('Menu item should be visible');
        }
        $target.mouseenter(); // This is NOT a mouseenter event. See jquery.js:5516 for more headaches.
        return testUtilsDom.click($target);
    }

    /**
     * Click to open the dropdown on a many2one
     *
     * @param {string} fieldName
     * @param {[string]} selector if set, this will restrict the search for the m2o
     *    input
     * @returns {Promise<HTMLInputElement>} the main many2one input
     */
    async function clickOpenM2ODropdown(fieldName, selector) {
        const m2oSelector = `${selector || ''} .o_field_many2one[name=${fieldName}] input`;
        const matches = document.querySelectorAll(m2oSelector);
        if (matches.length !== 1) {
            throw new Error(`cannot open m2o: selector ${selector} has been found ${matches.length} instead of 1`);
        }

        await testUtilsDom.click(matches[0]);
        return matches[0];
    }

    /**
     * Sets the value of an element and then, trigger all specified events.
     * Note that this helper also checks the unicity of the target.
     *
     * Example:
     *     testUtils.fields.editAndTrigger($('selector'), 'test', ['input', 'change']);
     *
     * @param {jQuery|EventTarget} el should target an input, textarea or select
     * @param {string|number} value
     * @param {string[]} events
     * @returns {Promise}
     */
    async function editAndTrigger(el, value, events) {
        if (el instanceof jQuery) {
            if (el.length !== 1) {
                throw new Error(`target ${el.selector} has length ${el.length} instead of 1`);
            }
            el.val(value);
        } else {
            el.value = value;
        }
        return testUtilsDom.triggerEvents(el, events);
    }

    /**
     * Sets the value of an input.
     *
     * Note that this helper also checks the unicity of the target.
     *
     * Example:
     *     testUtils.fields.editInput($('selector'), 'somevalue');
     *
     * @param {jQuery|EventTarget} el should target an input, textarea or select
     * @param {string|number} value
     * @returns {Promise}
     */
    async function editInput(el, value) {
        return editAndTrigger(el, value, ['input']);
    }

    /**
     * Sets the value of a select.
     *
     * Note that this helper also checks the unicity of the target.
     *
     * Example:
     *     testUtils.fields.editSelect($('selector'), 'somevalue');
     *
     * @param {jQuery|EventTarget} el should target an input, textarea or select
     * @param {string|number} value
     * @returns {Promise}
     */
    function editSelect(el, value) {
        return editAndTrigger(el, value, ['change']);
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
     * @param {[Object]} [options = {}]
     * @param {[string]} [options.selector]
     * @param {[string]} [options.search]
     * @param {[string]} [options.item]
     * @returns {Promise}
     */
    async function searchAndClickM2OItem(fieldName, options = {}) {
        const input = await clickOpenM2ODropdown(fieldName, options.selector);
        if (options.search) {
            await editInput(input, options.search);
        }
        if (options.item) {
            return clickM2OItem(fieldName, options.item);
        } else {
            return clickM2OHighlightedItem(fieldName, options.selector);
        }
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
        const params = {};
        if (typeof keyCode === 'string') {
            // Key (new API)
            if (keyCode in ARROW_KEYS_MAPPING) {
                params.key = ARROW_KEYS_MAPPING[keyCode];
            } else {
                params.key = keyCode[0].toUpperCase() + keyCode.slice(1).toLowerCase();
            }
            // KeyCode/which (jQuery)
            if (keyCode.length > 1) {
                keyCode = keyCode.toUpperCase();
                keyCode = $.ui.keyCode[keyCode];
            } else {
                keyCode = keyCode.charCodeAt(0);
            }
        }
        params.keyCode = keyCode;
        params.which = keyCode;
        return testUtilsDom.triggerEvent($el, type, params);
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
        clickM2OCreateAndEdit,
        clickM2OHighlightedItem,
        clickM2OItem,
        clickOpenM2ODropdown,
        editAndTrigger,
        editInput,
        editSelect,
        searchAndClickM2OItem,
        triggerKey,
        triggerKeydown,
        triggerKeyup,
    };
});
