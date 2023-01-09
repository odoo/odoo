odoo.define('web.test_utils_form', function (require) {
"use strict";

/**
 * Form Test Utils
 *
 * This module defines various utility functions to help test form views.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */

var testUtilsDom = require('web.test_utils_dom');

/**
 * Clicks on the Edit button in a form view, to set it to edit mode. Note that
 * it checks that the button is visible, so calling this method in edit mode
 * will fail.
 *
 * @param {FormController} form
 */
function clickEdit(form) {
    return testUtilsDom.click(form.$buttons.find('.o_form_button_edit'));
}

/**
 * Clicks on the Save button in a form view. Note that this method checks that
 * the Save button is visible.
 *
 * @param {FormController} form
 */
function clickSave(form) {
    return testUtilsDom.click(form.$buttons.find('.o_form_button_save'));
}

/**
 * Clicks on the Create button in a form view. Note that this method checks that
 * the Create button is visible.
 *
 * @param {FormController} form
 */
function clickCreate(form) {
    return testUtilsDom.click(form.$buttons.find('.o_form_button_create'));
}

/**
 * Clicks on the Discard button in a form view. Note that this method checks that
 * the Discard button is visible.
 *
 * @param {FormController} form
 */
function clickDiscard(form) {
    return testUtilsDom.click(form.$buttons.find('.o_form_button_cancel'));
}

/**
 * Reloads a form view.
 *
 * @param {FormController} form
 * @param {[Object]} params given to the controller reload method
 */
function reload(form, params) {
    return form.reload(params);
}

return {
    clickEdit: clickEdit,
    clickSave: clickSave,
    clickCreate: clickCreate,
    clickDiscard: clickDiscard,
    reload: reload,
};

});
