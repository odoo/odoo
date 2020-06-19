odoo.define('web.kanban_examples_registry', function (require) {
"use strict";

/**
 * This file instantiates and exports a registry. The purpose of this registry
 * is to store static data displayed in a dialog to help the end user to
 * configure its columns in the grouped Kanban view.
 *
 * To activate a link on the ColumnQuickCreate widget on open such a dialog, the
 * attribute 'examples' on the root arch node must be set to a valid key in this
 * registry.
 *
 * Each value in this registry must be an array of Objects containing the
 * following keys:
 *   - name (string)
 *   - columns (Array[string])
 *   - description (string, optional) BE CAREFUL [*]
 *
 * [*] The description is added with a t-raw so the translated texts must be
 *     properly escaped.
 */

var Registry = require('web.Registry');

return new Registry();

});
