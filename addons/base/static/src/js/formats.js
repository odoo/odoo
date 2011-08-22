
openerp.base.formats = function(openerp) {

/**
 * Formats a single atomic value based on a field descriptor
 *
 * @param {Object} value read from OpenERP
 * @param {Object} descriptor union of orm field and view field
 * @param {Object} [descriptor.widget] widget to use to display the value
 * @param {Object} descriptor.type fallback if no widget is provided, or if the provided widget is unknown
 * @param {Object} [descriptor.digits] used for the formatting of floats
 * @param {String} [value_if_empty=''] returned if the ``value`` argument is considered empty
 */
openerp.base.format_value = function (value, descriptor, value_if_empty) {
    // If NaN value, display as with a `false` (empty cell)
    if (typeof value === 'number' && isNaN(value)) {
        value = false;
    }
    switch (value) {
        case false:
        case Infinity:
        case -Infinity:
            return value_if_empty === undefined ?  '' : value_if_empty;
    }
    switch (descriptor.widget || descriptor.type) {
        case 'integer':
            return _.sprintf('%d', value);
        case 'float':
            var precision = descriptor.digits ? descriptor.digits[1] : 2;
            return _.sprintf('%.' + precision + 'f', value);
        case 'float_time':
            return _.sprintf("%02d:%02d",
                    Math.floor(value),
                    Math.round((value % 1) * 60));
        case 'progressbar':
            return _.sprintf(
                '<progress value="%.2f" max="100.0">%.2f%%</progress>',
                    value, value);
        case 'many2one':
            // name_get value format
            return value[1];
        default:
            return value;
    }
};

/**
 * Formats a provided cell based on its field type
 *
 * @param {Object} row_data record whose values should be displayed in the cell
 * @param {Object} column column descriptor
 * @param {"button"|"field"} column.tag base control type
 * @param {String} column.type widget type for a field control
 * @param {String} [column.string] button label
 * @param {String} [column.icon] button icon
 * @param {String} [value_if_empty=''] what to display if the field's value is ``false``
 */
openerp.base.format_cell = function (row_data, column, value_if_empty) {
    var attrs = column.modifiers_for(row_data);
    if (attrs.invisible) { return ''; }
    if (column.tag === 'button') {
        return [
            '<button type="button" title="', column.string || '', '">',
                '<img src="/base/static/src/img/icons/', column.icon, '.png"',
                    ' alt="', column.string || '', '"/>',
            '</button>'
        ].join('')
    }

    if (!row_data[column.id]) {
        return value_if_empty === undefined ? '' : value_if_empty;
    }
    return openerp.base.format_value(
            row_data[column.id].value, column, value_if_empty);
}
    
};
