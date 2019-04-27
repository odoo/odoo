odoo.define('web.test_utils_pivot', function (require) {
"use strict";

var testUtilsDom = require('web.test_utils_dom');

/**
 * Pivot Test Utils
 *
 * This module defines various utility functions to help test pivot views.
 *
 * Note that all methods defined in this module are exported in the main
 * testUtils file.
 */


/**
 * Select a measure by clicking on the corresponding dropdown item (in the
 * control panel 'Measure' submenu).
 *
 * Note that this method assumes that the dropdown menu is open.
 * @see toggleMeasuresDropdown
 *
 * @param {PivotController} pivot
 * @param {string} measure
 */
function clickMeasure(pivot, measure) {
    return testUtilsDom.click(pivot.$buttons.find(`.dropdown-item[data-field=${measure}]`));
}

/**
 * Open the 'Measure' dropdown menu (in the control panel)
 *
 * @see clickMeasure
 *
 * @param {PivotController} pivot
 */
function toggleMeasuresDropdown(pivot) {
    return testUtilsDom.click(pivot.$buttons.filter('.btn-group:first').find('> button'));
}

/**
 * Reloads a graph view.
 *
 * @param {PivotController} pivot
 * @param {[Object]} params given to the controller reload method
 */
function reload(pivot, params) {
    return pivot.reload(params);
}

return {
    clickMeasure: clickMeasure,
    reload: reload,
    toggleMeasuresDropdown: toggleMeasuresDropdown,
};

});
