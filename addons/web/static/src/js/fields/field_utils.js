odoo.define('web.field_utils', function (require) {
"use strict";

/**
 * Field Utils
 *
 * This file contains two types of functions: formatting functions and parsing
 * functions.
 *
 * Each field type has to display in string form at some point, but it should be
 * stored in memory with the actual value.  For example, a float value of 0.5 is
 * represented as the string "0.5" but is kept in memory as a float.  A date
 * (or datetime) value is always stored as a Moment.js object, but displayed as
 * a string.  This file contains all sort of functions necessary to perform the
 * conversions.
 */

var core = require('web.core');
var dom = require('web.dom');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');

var _t = core._t;

const NBSP = "\u00a0";

//------------------------------------------------------------------------------
// Formatting
//------------------------------------------------------------------------------

/**
 * Convert binary to bin_size
 *
 * @param {string} [value] base64 representation of the binary (might be already a bin_size!)
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options (note: this parameter is ignored)
 *
 * @returns {string} bin_size (which is human-readable)
 */
function formatBinary(value, field, options) {
    if (!value) {
        return '';
    }
    return utils.binaryToBinsize(value);
}

/**
 * @todo Really? it returns a jQuery element...  We should try to avoid this and
 * let DOM utility functions handle this directly. And replace this with a
 * function that returns a string so we can get rid of the forceString.
 *
 * @param {boolean} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.forceString=false] if true, returns a string
*    representation of the boolean rather than a jQueryElement
 * @returns {jQuery|string}
 */
function formatBoolean(value, field, options) {
    if (options && options.forceString) {
        return value ? _t('True') : _t('False');
    }
    return dom.renderCheckbox({
        prop: {
            checked: value,
            disabled: true,
        },
    });
}

/**
 * Returns a string representing a char.  If the value is false, then we return
 * an empty string.
 *
 * @param {string|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 * @param {boolean} [options.isPassword=false] if true, returns '********'
 *   instead of the formatted value
 * @returns {string}
 */
function formatChar(value, field, options) {
    value = typeof value === 'string' ? value : '';
    if (options && options.isPassword) {
        return _.str.repeat('*', value ? value.length : 0);
    }
    if (options && options.escape) {
        value = _.escape(value);
    }
    return value;
}

/**
 * Returns a string representing a date.  If the value is false, then we return
 * an empty string. Note that this is dependant on the localization settings
 *
 * @param {Moment|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.timezone=true] use the user timezone when formating the
 *        date
 * @returns {string}
 */
function formatDate(value, field, options) {
    if (value === false || isNaN(value)) {
        return "";
    }
    if (field && field.type === 'datetime') {
        if (!options || !('timezone' in options) || options.timezone) {
            value = value.clone().add(session.getTZOffset(value), 'minutes');
        }
    }
    var date_format = time.getLangDateFormat();
    return value.format(date_format);
}

/**
 * Returns a string representing a datetime.  If the value is false, then we
 * return an empty string.  Note that this is dependant on the localization
 * settings
 *
 * @params {Moment|false}
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.timezone=true] use the user timezone when formating the
 *        date
 * @returns {string}
 */
function formatDateTime(value, field, options) {
    if (value === false) {
        return "";
    }
    if (!options || !('timezone' in options) || options.timezone) {
        value = value.clone().add(session.getTZOffset(value), 'minutes');
    }
    return value.format(time.getLangDatetimeFormat());
}

/**
 * Returns a string representing a float.  The result takes into account the
 * user settings (to display the correct decimal separator).
 *
 * @param {float|false} value the value that should be formatted
 * @param {Object} [field] a description of the field (returned by fields_get
 *   for example).  It may contain a description of the number of digits that
 *   should be used.
 * @param {Object} [options] additional options to override the values in the
 *   python description of the field.
 * @param {integer[]} [options.digits] the number of digits that should be used,
 *   instead of the default digits precision in the field.
 * @param {function} [options.humanReadable] if returns true,
 *   formatFloat acts like utils.human_number
 * @returns {string}
 */
function formatFloat(value, field, options) {
    options = options || {};
    if (value === false) {
        return "";
    }
    if (options.humanReadable && options.humanReadable(value)) {
        return utils.human_number(value, options.decimals, options.minDigits, options.formatterCallback);
    }
    var l10n = core._t.database.parameters;
    var precision;
    if (options.digits) {
        precision = options.digits[1];
    } else if (field && field.digits) {
        precision = field.digits[1];
    } else {
        precision = 2;
    }
    var formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
    formatted[0] = utils.insert_thousand_seps(formatted[0]);
    return formatted.join(l10n.decimal_point);
}


/**
 * Returns a string representing a float value, from a float converted with a
 * factor.
 *
 * @param {number} value
 * @param {number} [options.factor]
 *          Conversion factor, default value is 1.0
 * @returns {string}
 */
function formatFloatFactor(value, field, options) {
    var factor = options.factor || 1;
    return formatFloat(value * factor, field, options);
}

/**
 * Returns a string representing a time value, from a float.  The idea is that
 * we sometimes want to display something like 1:45 instead of 1.75, or 0:15
 * instead of 0.25.
 *
 * @param {float} value
 * @returns {string}
 */
function formatFloatTime(value) {
    var pattern = '%02d:%02d';
    if (value < 0) {
        value = Math.abs(value);
        pattern = '-' + pattern;
    }
    var hour = Math.floor(value);
    var min = Math.round((value % 1) * 60);
    if (min === 60){
        min = 0;
        hour = hour + 1;
    }
    return _.str.sprintf(pattern, hour, min);
}

/**
 * Returns a string representing an integer.  If the value is false, then we
 * return an empty string.
 *
 * @param {integer|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.isPassword=false] if true, returns '********'
 * @param {function} [options.humanReadable] if returns true,
 *   formatFloat acts like utils.human_number
 * @returns {string}
 */
function formatInteger(value, field, options) {
    options = options || {};
    if (options.isPassword) {
        return _.str.repeat('*', String(value).length);
    }
    if (!value && value !== 0) {
        // previously, it returned 'false'. I don't know why.  But for the Pivot
        // view, I want to display the concept of 'no value' with an empty
        // string.
        return "";
    }
    if (options.humanReadable && options.humanReadable(value)) {
        return utils.human_number(value, options.decimals, options.minDigits, options.formatterCallback);
    }
    return utils.insert_thousand_seps(_.str.sprintf('%d', value));
}

/**
 * Returns a string representing an many2one.  If the value is false, then we
 * return an empty string.  Note that it accepts two types of input parameters:
 * an array, in that case we assume that the many2one value is of the form
 * [id, nameget], and we return the nameget, or it can be an object, and in that
 * case, we assume that it is a record datapoint from a BasicModel.
 *
 * @param {Array|Object|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 * @returns {string}
 */
function formatMany2one(value, field, options) {
    if (!value) {
        value = '';
    } else if (_.isArray(value)) {
        // value is a pair [id, nameget]
        value = value[1];
    } else {
        // value is a datapoint, so we read its display_name field, which
        // may in turn be a datapoint (if the name field is a many2one)
        while (value.data) {
            value = value.data.display_name || '';
        }
    }
    if (options && options.escape) {
        value = _.escape(value);
    }
    return value;
}

/**
 * Returns a string indicating the number of records in the relation.
 *
 * @param {Object} value a valid element from a BasicModel, that represents a
 *   list of values
 * @returns {string}
 */
function formatX2Many(value) {
    if (value.data.length === 0) {
        return _t('No records');
    } else if (value.data.length === 1) {
        return _t('1 record');
    } else {
        return value.data.length + _t(' records');
    }
}

/**
 * Returns a string representing a monetary value. The result takes into account
 * the user settings (to display the correct decimal separator, currency, ...).
 *
 * @param {float|false} value the value that should be formatted
 * @param {Object} [field]
 *        a description of the field (returned by fields_get for example). It
 *        may contain a description of the number of digits that should be used.
 * @param {Object} [options]
 *        additional options to override the values in the python description of
 *        the field.
 * @param {Object} [options.currency] the description of the currency to use
 * @param {integer} [options.currency_id]
 *        the id of the 'res.currency' to use (ignored if options.currency)
 * @param {string} [options.currency_field]
 *        the name of the field whose value is the currency id
 *        (ignore if options.currency or options.currency_id)
 *        Note: if not given it will default to the field currency_field value
 *        or to 'currency_id'.
 * @param {Object} [options.data]
 *        a mapping of field name to field value, required with
 *        options.currency_field
 * @param {integer[]} [options.digits]
 *        the number of digits that should be used, instead of the default
 *        digits precision in the field. Note: if the currency defines a
 *        precision, the currency's one is used.
 * @returns {string}
 */
function formatMonetary(value, field, options) {
    if (value === false) {
        return "";
    }
    options = options || {};

    var currency = options.currency;
    if (!currency) {
        var currency_id = options.currency_id;
        if (!currency_id && options.data) {
            var currency_field = options.currency_field || field.currency_field || 'currency_id';
            currency_id = options.data[currency_field] && options.data[currency_field].res_id;
        }
        currency = session.get_currency(currency_id);
    }

    var digits = (currency && currency.digits) || options.digits;
    if (options.field_digits === true) {
        digits = field.digits || digits;
    }
    var formatted_value = formatFloat(value, field,
        _.extend({}, options , {digits: digits})
    );

    if (!currency || options.noSymbol) {
        return formatted_value;
    }
    if (currency.position === "after") {
        return formatted_value += NBSP + currency.symbol;
    } else {
        return currency.symbol + NBSP + formatted_value;
    }
}
/**
 * Returns a string representing the given value (multiplied by 100)
 * concatenated with '%'.
 *
 * @param {number | false} value
 * @param {Object} [field]
 * @param {Object} [options]
 * @param {function} [options.humanReadable] if returns true, parsing is avoided
 * @returns {string}
 */
function formatPercentage(value, field, options) {
    options = options || {};
    var result = formatFloat(value * 100, field, options) || '0';
    if (options.humanReadable && options.humanReadable(value * 100)) {
        return result + "%";
    }
    return (parseFloat(result) + "%").replace('.', _t.database.parameters.decimal_point);
}
/**
 * Returns a string representing the value of the selection.
 *
 * @param {string|false} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.escape=false] if true, escapes the formatted value
 */
function formatSelection(value, field, options) {
    var val = _.find(field.selection, function (option) {
        return option[0] === value;
    });
    if (!val) {
        return '';
    }
    value = val[1];
    if (options && options.escape) {
        value = _.escape(value);
    }
    return value;
}

////////////////////////////////////////////////////////////////////////////////
// Parse
////////////////////////////////////////////////////////////////////////////////

/**
 * Create an Date object
 * The method toJSON return the formated value to send value server side
 *
 * @param {string} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.isUTC] the formatted date is utc
 * @param {boolean} [options.timezone=false] format the date after apply the timezone
 *        offset
 * @returns {Moment|false} Moment date object
 */
function parseDate(value, field, options) {
    if (!value) {
        return false;
    }
    var datePattern = time.getLangDateFormat();
    var datePatternWoZero = datePattern.replace('MM','M').replace('DD','D');
    var date;
    if (options && options.isUTC) {
        date = moment.utc(value);
    } else {
        date = moment.utc(value, [datePattern, datePatternWoZero, moment.ISO_8601]);
    }
    if (date.isValid()) {
        if (date.year() === 0) {
            date.year(moment.utc().year());
        }
        if (date.year() >= 1900) {
            date.toJSON = function () {
                return this.clone().locale('en').format('YYYY-MM-DD');
            };
            return date;
        }
    }
    throw new Error(_.str.sprintf(core._t("'%s' is not a correct date"), value));
}

/**
 * Create an Date object
 * The method toJSON return the formated value to send value server side
 *
 * @param {string} value
 * @param {Object} [field]
 *        a description of the field (note: this parameter is ignored)
 * @param {Object} [options] additional options
 * @param {boolean} [options.isUTC] the formatted date is utc
 * @param {boolean} [options.timezone=false] format the date after apply the timezone
 *        offset
 * @returns {Moment|false} Moment date object
 */
function parseDateTime(value, field, options) {
    if (!value) {
        return false;
    }
    var datePattern = time.getLangDateFormat(),
        timePattern = time.getLangTimeFormat();
    var datePatternWoZero = datePattern.replace('MM','M').replace('DD','D'),
        timePatternWoZero = timePattern.replace('HH','H').replace('mm','m').replace('ss','s');
    var pattern1 = datePattern + ' ' + timePattern;
    var pattern2 = datePatternWoZero + ' ' + timePatternWoZero;
    var datetime;
    if (options && options.isUTC) {
        // phatomjs crash if we don't use this format
        datetime = moment.utc(value.replace(' ', 'T') + 'Z');
    } else {
        datetime = moment.utc(value, [pattern1, pattern2, moment.ISO_8601]);
        if (options && options.timezone) {
            datetime.add(-session.getTZOffset(datetime), 'minutes');
        }
    }
    if (datetime.isValid()) {
        if (datetime.year() === 0) {
            datetime.year(moment.utc().year());
        }
        if (datetime.year() >= 1900) {
            datetime.toJSON = function () {
                return this.clone().locale('en').format('YYYY-MM-DD HH:mm:ss');
            };
            return datetime;
        }
    }
    throw new Error(_.str.sprintf(core._t("'%s' is not a correct datetime"), value));
}

/**
 * Parse a String containing number in language formating
 *
 * @param {string} value
 *                The string to be parsed with the setting of thousands and
 *                decimal separator
 * @returns {float|NaN} the number value contained in the string representation
 */
function parseNumber(value) {
    if (core._t.database.parameters.thousands_sep) {
        var escapedSep = _.str.escapeRegExp(core._t.database.parameters.thousands_sep);
        value = value.replace(new RegExp(escapedSep, 'g'), '');
    }
    if (core._t.database.parameters.decimal_point) {
        value = value.replace(core._t.database.parameters.decimal_point, '.');
    }
    return Number(value);
}

/**
 * Parse a String containing float in language formating
 *
 * @param {string} value
 *                The string to be parsed with the setting of thousands and
 *                decimal separator
 * @returns {float}
 * @throws {Error} if no float is found respecting the language configuration
 */
function parseFloat(value) {
    var parsed = parseNumber(value);
    if (isNaN(parsed)) {
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct float"), value));
    }
    return parsed;
}

/**
 * Parse a String containing currency symbol and returns amount
 *
 * @param {string} value
 *                The string to be parsed
 *                We assume that a monetary is always a pair (symbol, amount) separated
 *                by a non breaking space. A simple float can also be accepted as value
 * @param {Object} [field]
 *        a description of the field (returned by fields_get for example).
 * @param {Object} [options] additional options.
 * @param {Object} [options.currency] - the description of the currency to use
 * @param {integer} [options.currency_id]
 *        the id of the 'res.currency' to use (ignored if options.currency)
 * @param {string} [options.currency_field]
 *        the name of the field whose value is the currency id
 *        (ignore if options.currency or options.currency_id)
 *        Note: if not given it will default to the field currency_field value
 *        or to 'currency_id'.
 * @param {Object} [options.data]
 *        a mapping of field name to field value, required with
 *        options.currency_field
 *
 * @returns {float} the float value contained in the string representation
 * @throws {Error} if no float is found or if parameter does not respect monetary condition
 */
function parseMonetary(value, field, options) {
    if (!value.includes(NBSP) && !value.includes('&nbsp;')) {
        return parseFloat(value);
    }
    options = options || {};
    var currency = options.currency;
    if (!currency) {
        var currency_id = options.currency_id;
        if (!currency_id && options.data) {
            var currency_field = options.currency_field || field.currency_field || 'currency_id';
            currency_id = options.data[currency_field] && options.data[currency_field].res_id;
        }
        currency = session.get_currency(currency_id);
    }
    if (!currency) {
        return parseFloat(value);
    }
    if (!value.includes(currency.symbol)) {
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct monetary field"), value));
    }
    if (currency.position === 'before') {
        return parseFloat(value
            .replace(`${ currency.symbol }${ NBSP }`, '')
            .replace(`${ currency.symbol }&nbsp;`, ''));
    } else {
        return parseFloat(value
            .replace(`${ NBSP }${ currency.symbol }`, '')
            .replace(`&nbsp;${ currency.symbol }`, ''));
    }
}

/**
 * Parse a String containing float and unconvert it with a conversion factor
 *
 * @param {number} [options.factor]
 *          Conversion factor, default value is 1.0
 */
function parseFloatFactor(value, field, options) {
    var parsed = parseFloat(value);
    var factor = options.factor || 1.0;
    return parsed / factor;
}

function parseFloatTime(value) {
    var factor = 1;
    if (value[0] === '-') {
        value = value.slice(1);
        factor = -1;
    }
    var float_time_pair = value.split(":");
    if (float_time_pair.length !== 2)
        return factor * parseFloat(value);
    var hours = parseInteger(float_time_pair[0]);
    var minutes = parseInteger(float_time_pair[1]);
    return factor * (hours + (minutes / 60));
}

/**
 * Parse a String containing a percentage and convert it to float.
 * The percentage can be a regular xx.xx float or a xx%.
 *
 * @param {string} value
 *                The string to be parsed
 * @returns {float}
 * @throws {Error} if the value couldn't be converted to float
 */
function parsePercentage(value) {
    if (value.slice(-1) === '%') {
        return parseFloat(value.slice(0, -1)) / 100;
    }
    return parseFloat(value);
}

/**
 * Parse a String containing integer with language formating
 *
 * @param {string} value
 *                The string to be parsed with the setting of thousands and
 *                decimal separator
 * @returns {integer}
 * @throws {Error} if no integer is found respecting the language configuration
 */
function parseInteger(value) {
    var parsed = parseNumber(value);
    // do not accept not numbers or float values
    if (isNaN(parsed) || parsed % 1 || parsed < -2147483648 || parsed > 2147483647) {
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct integer"), value));
    }
    return parsed;
}

/**
 * Creates an object with id and display_name.
 *
 * @param {Array|number|string|Object} value
 *        The given value can be :
 *        - an array with id as first element and display_name as second element
 *        - a number or a string representing the id (the display_name will be
 *          returned as undefined)
 *        - an object, simply returned untouched
 * @returns {Object} (contains the id and display_name)
 *                   Note: if the given value is not an array, a string or a
 *                   number, the value is returned untouched.
 */
function parseMany2one(value) {
    if (_.isArray(value)) {
        return {
            id: value[0],
            display_name: value[1],
        };
    }
    if (_.isNumber(value) || _.isString(value)) {
        return {
            id: parseInt(value, 10),
        };
    }
    return value;
}

return {
    format: {
        binary: formatBinary,
        boolean: formatBoolean,
        char: formatChar,
        date: formatDate,
        datetime: formatDateTime,
        float: formatFloat,
        float_factor: formatFloatFactor,
        float_time: formatFloatTime,
        html: _.identity, // todo
        integer: formatInteger,
        many2many: formatX2Many,
        many2one: formatMany2one,
        many2one_reference: formatInteger,
        monetary: formatMonetary,
        one2many: formatX2Many,
        percentage: formatPercentage,
        reference: formatMany2one,
        selection: formatSelection,
        text: formatChar,
    },
    parse: {
        binary: _.identity,
        boolean: _.identity, // todo
        char: _.identity, // todo
        date: parseDate, // todo
        datetime: parseDateTime, // todo
        float: parseFloat,
        float_factor: parseFloatFactor,
        float_time: parseFloatTime,
        html: _.identity, // todo
        integer: parseInteger,
        many2many: _.identity, // todo
        many2one: parseMany2one,
        many2one_reference: parseInteger,
        monetary: parseMonetary,
        one2many: _.identity,
        percentage: parsePercentage,
        reference: parseMany2one,
        selection: _.identity, // todo
        text: _.identity, // todo
    },
};

});
