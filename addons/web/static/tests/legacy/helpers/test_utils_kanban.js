/** @odoo-module **/

/**
 * Kanban Test Utils
 *
 * This module defines various utility functions to help testing kanban views.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */

import { click } from "./test_utils_dom";
import { editAndTrigger } from "./test_utils_fields";

/**
 * Clicks on the Create button in a kanban view. Note that this method checks that
 * the Create button is visible.
 *
 * @param {KanbanController} kanban
 * @returns {Promise}
 */
export function clickCreate(kanban) {
    return click(kanban.$buttons.find('.o-kanban-button-new'));
}

/**
 * Open the settings menu for a column (in a grouped kanban view)
 *
 * @param {jQuery} $column
 * @returns {Promise}
 */
export function toggleGroupSettings($column) {
    var $dropdownToggler = $column.find('.o_kanban_config > a.dropdown-toggle');
    if (!$dropdownToggler.is(':visible')) {
        $dropdownToggler.css('display', 'block');
    }
    return click($dropdownToggler);
}

/**
 * Edit a value in a quickcreate form view (this method assumes that the quick
 * create feature is active, and a sub form view is open)
 *
 * @param {kanbanController} kanban
 * @param {string|number} value
 * @param {[string]} fieldName
 * @returns {Promise}
 */
export function quickCreate(kanban, value, fieldName) {
    var additionalSelector = fieldName ? ('[name=' + fieldName + ']'): '';
    var enterEvent = $.Event(
        'keydown',
        {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }
    );
    return editAndTrigger(
        kanban.$('.o_kanban_quick_create input' + additionalSelector),
        value,
        ['input', enterEvent]
    );
}

/**
 * Reloads a kanban view.
 *
 * @param {KanbanController} kanban
 * @param {[Object]} params given to the controller reload method
 * @returns {Promise}
 */
export function reload(kanban, params) {
    return kanban.reload(params);
}

/**
 * Open the setting dropdown of a kanban record.  Note that the template of a
 * kanban record is not standardized, so this method will fail if the template
 * does not comply with the usual dom structure.
 *
 * @param {jQuery} $record
 * @returns {Promise}
 */
export function toggleRecordDropdown($record) {
    var $dropdownToggler = $record.find('.o_dropdown_kanban > a.dropdown-toggle');
    if (!$dropdownToggler.is(':visible')) {
        $dropdownToggler.css('display', 'block');
    }
    return click($dropdownToggler);
}
