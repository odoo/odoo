
openerp.base.formats = function(openerp) {

/**
 * Converts a string to a Date javascript object using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35').
 * 
 * The timezone is assumed to be UTC (standard for OpenERP 6.1)
 * and will be converted to the browser's timezone.
 * 
 * @param {String} str A string representing a datetime.
 * @returns {Date}
 */
openerp.base.parse_datetime = function(str) {
    if(!str) {
        return str;
    }
    var regex = /\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d/;
    var res = regex.exec(str);
    if ( res[0] != str ) {
        throw "'" + str + "' is not a valid datetime";
    }
    var obj = Date.parse(str + " GMT");
    if (! obj) {
        throw "'" + str + "' is not a valid datetime";
    }
    return obj;
};

/**
 * Converts a string to a Date javascript object using OpenERP's
 * date string format (exemple: '2011-12-01').
 * 
 * @param {String} str A string representing a date.
 * @returns {Date}
 */
openerp.base.parse_date = function(str) {
    if(!str) {
        return str;
    }
    var regex = /\d\d\d\d-\d\d-\d\d/;
    var res = regex.exec(str);
    if ( res[0] != str ) {
        throw "'" + str + "' is not a valid date";
    }
    var obj = Date.parse(str);
    if (! obj) {
        throw "'" + str + "' is not a valid date";
    }
    return obj;
};

/**
 * Converts a string to a Date javascript object using OpenERP's
 * time string format (exemple: '15:12:35').
 * 
 * @param {String} str A string representing a time.
 * @returns {Date}
 */
openerp.base.parse_time = function(str) {
    if(!str) {
        return str;
    }
    var regex = /\d\d:\d\d:\d\d/;
    var res = regex.exec(str);
    if ( res[0] != str ) {
        throw "'" + str + "' is not a valid time";
    }
    var obj = Date.parse(str);
    if (! obj) {
        throw "'" + str + "' is not a valid time";
    }
    return obj;
};

/*
 * Left-pad provided arg 1 with zeroes until reaching size provided by second
 * argument.
 *
 * @param {Number|String} str value to pad
 * @param {Number} size size to reach on the final padded value
 * @returns {String} padded string
 */
var zpad = function(str, size) {
    str = "" + str;
    return new Array(_.range(size - str.length)).join('0') + str;
};

/**
 * Converts a Date javascript object to a string using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35').
 * 
 * The timezone of the Date object is assumed to be the one of the
 * browser and it will be converted to UTC (standard for OpenERP 6.1).
 * 
 * @param {Date} obj
 * @returns {String} A string representing a datetime.
 */
openerp.base.format_datetime = function(obj) {
    if (!obj) {
        return false;
    }
    return zpad(obj.getUTCFullYear(),4) + "-" + zpad(obj.getUTCMonth() + 1,2) + "-"
         + zpad(obj.getUTCDate(),2) + " " + zpad(obj.getUTCHours(),2) + ":"
         + zpad(obj.getUTCMinutes(),2) + ":" + zpad(obj.getUTCSeconds(),2);
};

/**
 * Converts a Date javascript object to a string using OpenERP's
 * date string format (exemple: '2011-12-01').
 * 
 * @param {Date} obj
 * @returns {String} A string representing a date.
 */
openerp.base.format_date = function(obj) {
    if (!obj) {
        return false;
    }
    return zpad(obj.getFullYear(),4) + "-" + zpad(obj.getMonth() + 1,2) + "-"
         + zpad(obj.getDate(),2);
};

/**
 * Converts a Date javascript object to a string using OpenERP's
 * time string format (exemple: '15:12:35').
 * 
 * @param {Date} obj
 * @returns {String} A string representing a time.
 */
openerp.base.format_time = function(obj) {
    if (!obj) {
        return false;
    }
    return zpad(obj.getHours(),2) + ":" + zpad(obj.getMinutes(),2) + ":"
         + zpad(obj.getSeconds(),2);
};

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

    return openerp.base.format_value(
            row_data[column.id].value, column, value_if_empty);
}
    
};
