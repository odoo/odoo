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
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');

//------------------------------------------------------------------------------
// Formatting
//------------------------------------------------------------------------------

/**
 * @todo Really? it returns a jqueryElement...  We should try to move this to a
 * module with dom helpers functions, such as web.dom, maybe. And replace this
 * with a function that returns a string
 *
 * @param {boolean} value
 * @returns {jQueryElement}
 */
function formatBoolean (value) {
    var $input = $('<input type="checkbox">')
                .prop('checked', value)
                .prop('disabled', true);
    return $('<div>')
                .addClass('o_checkbox')
                .append($input)
                .append($('<span>'));
}

/**
 * Returns a string representing a char.  If the value is false, then we return
 * an empty string.
 *
 * @param {string|false} value
 * @returns {string}
 */
function formatChar (value) {
    return typeof value === 'string' ? value : '';
}

/**
 * Returns a string representing a date.  If the value is false, then we return
 * an empty string. Note that this is dependant on the localization settings
 *
 * @param {Moment|false}
 * @returns {string}
 */
function formatDate (value) {
    if (!value) {
        return "";
    }
    var l10n = core._t.database.parameters;
    var date_format = time.strftime_to_moment_format(l10n.date_format);
    return value.format(date_format);
}

/**
 * Returns a string representing a datetime.  If the value is false, then we
 * return an empty string.  Note that this is dependant on the localization
 * settings
 *
 * @params {Moment|false}
 * @returns {string}
 */
function formatDateTime (value) {
    if (!value) {
        return "";
    }
    var l10n = core._t.database.parameters;
    var date_format = time.strftime_to_moment_format(l10n.date_format);
    var time_format = time.strftime_to_moment_format(l10n.time_format);
    var datetime_format = date_format + ' ' + time_format;
    return value.format(datetime_format);
}

/**
 * Returns a string representing a float.  The result takes into account the
 * user settings (to display the correct decimal separator).
 *
 * @param {float} value the value that should be formatted
 * @param {Object} [field] a description of the field (returned by fields_get
 *   for example).  It may contain a description of the number of digits that
 *   should be used.
 * @returns {string}
 */
function formatFloat (value, field) {
    var l10n = core._t.database.parameters;
    var precision = (field && field.digits) ? field.digits[1] : 2;
    var formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
    formatted[0] = utils.insert_thousand_seps(formatted[0]);
    return formatted.join(l10n.decimal_point);
}

/**
 * Returns a string representing a time value, from a float.  The idea is that
 * we sometimes want to display something like 1:45 instead of 1.75, or 0:15
 * instead of 0.25.
 *
 * @param {float} value
 * @returns {string}
 */
function formatFloatTime (value) {
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
 * Returns a string representing an ID.  If the value is false, then we
 * return an empty string.
 *
 * @param {integer|false} value
 * @returns {string}
 */
function formatID (value) {
    return value ? value.toString() : '';
}

/**
 * Returns a string representing an integer.  If the value is false, then we
 * return an empty string.
 *
 * @param {integer|false} value
 * @returns {string}
 */
function formatInteger (value) {
    if (!value && value !== 0) {
        // previously, it returned 'false'. I don't know why.  But for the Pivot
        // view, I want to display the concept of 'no value' with an empty
        // string.
        return "";
    }
    return utils.insert_thousand_seps(_.str.sprintf('%d', value));
}

/**
 * Returns a string representing an many2one.  If the value is false, then we
 * return an empty string.  Note that it accepts two types of input parameters:
 * an array, in that case we assume that the many2one value is of the form
 * [id, nameget], and we return the nameget, or it can be an object, and in that
 * case, we assume that it is a record from a BasicModel.
 *
 * @param {Array|Object|false} value
 * @returns {string}
 */
function formatMany2one (value) {
    return value && (_.isArray(value) ? value[1] : value.data.display_name) || '';
}

/**
 * Returns a string representing an many2one.  That is a string containing all
 * the display_name, concatenated.
 *
 * @param {Object} value a valid element from a BasicModel, that represents a
 *   list of values
 * @returns {string}
 */
function formatMany2Many (value) {
    var names = _.map(value.data, function(p) {
        return p.data.display_name;
    });
    return names.join(', ');
}

function formatMonetary (value, field, options) {
    options = options || {};
    var currency_id = options.currency_id;
    if (!currency_id && options.data) {
        var currency_field = options.currency_field || field.currency_field || 'currency_id';
        currency_id = options.data[currency_field] && options.data[currency_field].res_id;
    }
    var currency = session.get_currency(currency_id);

    var digits_precision = (currency && currency.digits) || [69,2];
    var precision = digits_precision[1];
    var formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
    formatted[0] = utils.insert_thousand_seps(formatted[0]);
    var l10n = core._t.database.parameters;
    var formatted_value = formatted.join(l10n.decimal_point);

    if (!currency) {
        return formatted_value;
    }
    if (currency.position === "after") {
        return formatted_value += '&nbsp;' + currency.symbol;
    } else {
        return currency.symbol + '&nbsp;' + formatted_value;
    }
}

function formatSelection (value, field) {
    if (!value) {
        return '';
    }
    var val = _.find(field.selection, function(option) {
        return option[0] === value;
    });
    return val[1];
}

////////////////////////////////////////////////////////////////////////////////
// Parse
////////////////////////////////////////////////////////////////////////////////

/**
 * create an Date object
 * The method toJSON return the formated value to send value server side
 *
 * @params {string}
 * @returns {Moment|false} Moment date object
 */
function parseDate (value) {
    if (!value) {
        return false;
    }
    var date_pattern = time.strftime_to_moment_format(core._t.database.parameters.date_format);
    var date_pattern_wo_zero = date_pattern.replace('MM','M').replace('DD','D');
    var date = moment(value, [date_pattern, date_pattern_wo_zero, moment.ISO_8601], true);
    if (date.isValid() && date.year() >= 1900) {
        date.toJSON = time.date_to_str.bind(time, date.toDate());
        return date;
    }
    date = moment(value, [date_pattern, date_pattern_wo_zero, moment.ISO_8601]);
    if (date.isValid()) {
        if (date.year() === 0) {
            date.year(moment.utc().year());
        }
        if (date.year() >= 1900) {
            date.toJSON = time.date_to_str.bind(time, date.toDate());
            return date;
        }
    }
    throw new Error(_.str.sprintf(core._t("'%s' is not a correct date"), value));
}

/**
 * create an Date object
 * The method toJSON return the formated value to send value server side
 *
 * @params {string}
 * @returns {Moment|false} Moment date object
 */
function parseDateTime (value) {
    if (!value) {
        return false;
    }
    var date_pattern = time.strftime_to_moment_format(core._t.database.parameters.date_format),
        time_pattern = time.strftime_to_moment_format(core._t.database.parameters.time_format);
    var date_pattern_wo_zero = date_pattern.replace('MM','M').replace('DD','D'),
        time_pattern_wo_zero = time_pattern.replace('HH','H').replace('mm','m').replace('ss','s');
    var pattern1 = date_pattern + ' ' + time_pattern;
    var pattern2 = date_pattern_wo_zero + ' ' + time_pattern_wo_zero;
    var datetime = moment(value, [pattern1, pattern2, moment.ISO_8601], true);
    if (datetime.isValid() && datetime.year() >= 1900) {
        datetime.toJSON = time.datetime_to_str.bind(time, datetime.toDate());
        return datetime;
    }
    datetime = moment(value, [pattern1, pattern2, moment.ISO_8601]);
    if (datetime.isValid()) {
        if (datetime.year() === 0) {
            datetime.year(moment.utc().year());
        }
        if (datetime.year() >= 1900) {
            datetime.toJSON = time.datetime_to_str.bind(time, datetime.toDate());
            return datetime;
        }
    }
    throw new Error(_.str.sprintf(core._t("'%s' is not a correct datetime"), value));
}

function parseFloat (value) {
    value = value.replace(new RegExp(core._t.database.parameters.thousands_sep, "g"), '');
    value = value.replace(core._t.database.parameters.decimal_point, '.');
    var parsed = Number(value);
    if (isNaN(parsed)) {
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct float"), value));
    }
    return parsed;
}

function parseFloatTime (value) {
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

function parseInteger (value) {
    value = value.replace(new RegExp(core._t.database.parameters.thousands_sep, "g"), '');
    var parsed = Number(value);
    // do not accept not numbers or float values
    if (isNaN(parsed) || parsed % 1) {
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct integer"), value));
    }
    return parsed;
}

function parseMonetary (formatted_value) {
    var l10n = core._t.database.parameters;
    var value = formatted_value.replace(l10n.thousands_sep, '')
        .replace(l10n.decimal_point, '.')
        .match(/([0-9]+(\.[0-9]*)?)/)[1];
    return parseFloat(value);
}

function identity(value) {
    return value;
}


return {
    format: {
        binary: identity, // todo
        boolean: formatBoolean,
        char: formatChar,
        date: formatDate,
        datetime: formatDateTime,
        float: formatFloat,
        float_time: formatFloatTime,
        html: identity, // todo
        id: formatID,
        integer: formatInteger,
        many2many: formatMany2Many,
        many2one: formatMany2one,
        monetary: formatMonetary,
        one2many: identity, // todo
        reference: identity, // todo
        selection: formatSelection,
        text: formatChar,
    },
    parse: {
        binary: identity,
        boolean: identity, // todo
        char: identity, // todo
        date: parseDate, // todo
        datetime: parseDateTime, // todo
        float: parseFloat,
        float_time: parseFloatTime,
        html: identity, // todo
        id: identity,
        integer: parseInteger,
        many2many: identity, // todo
        many2one: identity,
        monetary: parseMonetary,
        one2many: identity,
        reference: identity, // todo
        selection: identity, // todo
        text: identity, // todo
    },
};

});
