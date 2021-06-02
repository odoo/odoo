odoo.define('web.test_utils_modal', function (require) {
"use strict";

/**
 * Modal Test Utils
 *
 * This module defines various utility functions to help test pivot views.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */

var core = require('web.core');
var concurrency = require('web.concurrency');

/**
 * Click on a button in the footer of a modal (which contains a given string).
 * Note that this method checks the unicity of the button.
 *
 * @param {string} text (in english: this method will perform the translation)
 */
function clickButton(text) {
    var selector = `.modal-footer button:contains(${core._t(text)})`;
    var $button = $(selector);
    if ($button.length !== 1) {
        throw new Error(`Found ${$button.length} button(s) containing '${text}'`);
    }
    $button.click();
    return concurrency.delay(0);
}

return {
    clickButton: clickButton,
};

});
