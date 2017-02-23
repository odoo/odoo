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
 * represented as the string "0.5".
 */

var core = require('web.core');
var session = require('web.session');
var time = require('web.time');
var utils = require('web.utils');

////////////////////////////////////////////////////////////////////////////////
// Format
////////////////////////////////////////////////////////////////////////////////

function format_boolean(value) {
    var $input = $('<input type="checkbox">')
                .prop('checked', value)
                .prop('disabled', true);
    return $('<div>')
                .addClass('o_checkbox')
                .append($input)
                .append($('<span>'));
}

function format_char(value) {
    return typeof value === 'string' ? value : '';
}

/**
 * @params {Moment}
 * @returns {string}
 */
function format_date(value) {
    var l10n = core._t.database.parameters;
    var date_format = time.strftime_to_moment_format(l10n.date_format);
    return value.format(date_format);
}

/**
 * @params {Moment}
 * @returns {string}
 */
function format_datetime(value) {
    var l10n = core._t.database.parameters;
    var date_format = time.strftime_to_moment_format(l10n.date_format);
    var time_format = time.strftime_to_moment_format(l10n.time_format);
    var datetime_format = date_format + ' ' + time_format;
    return value.format(datetime_format);
}

// Format a float, according to the local settings
// Params:
// * value: a number describing the raw value of the float
// * field [optional]: a description of a field, that may contains extra
//   information, such as a given precision
function format_float(value, field) {
    var l10n = core._t.database.parameters;
    var precision = (field && field.digits) ? field.digits[1] : 2;
    var formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
    formatted[0] = utils.insert_thousand_seps(formatted[0]);
    return formatted.join(l10n.decimal_point);
}

function format_float_time(value) {
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

function format_id(value) {
    return value ? value.toString() : false;
}

function format_integer(value) {
    if (!value && value !== 0) {
        // previously, it returned 'false'. I don't know why.  But for the Pivot
        // view, I want to display the concept of 'no value' with an empty
        // string.
        return "";
    }
    return utils.insert_thousand_seps(_.str.sprintf('%d', value));
}

function format_many2one(value) {
    return value && (_.isArray(value) ? value[1] : value.data.display_name) || '';
}

function format_many2many(value) {
    var names = _.map(value.data, function(p) {
        return p.data.display_name;
    });
    return names.join(', ');
}

function format_monetary(value, field, options) {
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

function format_field(value, field, options) {
    var formatter = result['format_' + field.type];
    return formatter(value, field, options);
}

function format_selection(value, field) {
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
 * @returns {Moment} Moment date object
 */
function parse_date(value) {
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
 * @returns {Moment} Moment date object
 */
function parse_datetime(value) {
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

function parse_field(value, field) {
    var parser = result['parse_' + field.type];
    return parser(value, field);
}

function parse_float(value) {
    value = value.replace(new RegExp(core._t.database.parameters.thousands_sep, "g"), '');
    value = value.replace(core._t.database.parameters.decimal_point, '.');
    var parsed = Number(value);
    if (isNaN(parsed)) {
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct float"), value));
    }
    return parsed;
}

function parse_float_time(value) {
    var factor = 1;
    if (value[0] === '-') {
        value = value.slice(1);
        factor = -1;
    }
    var float_time_pair = value.split(":");
    if (float_time_pair.length !== 2)
        return factor * parse_float(value);
    var hours = parse_integer(float_time_pair[0]);
    var minutes = parse_integer(float_time_pair[1]);
    return factor * (hours + (minutes / 60));
}

function parse_integer(value) {
    value = value.replace(new RegExp(core._t.database.parameters.thousands_sep, "g"), '');
    var parsed = Number(value);
    // do not accept not numbers or float values
    if (isNaN(parsed) || parsed % 1) {
        throw new Error(_.str.sprintf(core._t("'%s' is not a correct integer"), value));
    }
    return parsed;
}

function parse_monetary(formatted_value) {
    var l10n = core._t.database.parameters;
    var value = formatted_value.replace(l10n.thousands_sep, '')
        .replace(l10n.decimal_point, '.')
        .match(/([0-9]+(\.[0-9]*)?)/)[1];
    return parseFloat(value);
}

function identity(value) {
    return value;
}

var result = {
    format_binary: identity, // todo
    format_boolean: format_boolean,
    format_char: format_char,
    format_date: format_date,
    format_datetime: format_datetime,
    format_float: format_float,
    format_float_time: format_float_time,
    format_html: identity, // todo
    format_id: format_id,
    format_integer: format_integer,
    format_many2many: format_many2many,
    format_many2one: format_many2one,
    format_monetary: format_monetary,
    format_one2many: identity, // todo
    format_reference: identity, // todo
    format_selection: format_selection,
    format_text: format_char,

    format_field: format_field,

    parse_binary: identity, // todo
    parse_boolean: identity, // todo
    parse_char: identity, // todo
    parse_date: parse_date, // todo
    parse_datetime: parse_datetime, // todo
    parse_float: parse_float,
    parse_float_time: parse_float_time,
    parse_html: identity, // todo
    parse_id: identity,
    parse_integer: parse_integer,
    parse_many2many: identity, // todo
    parse_many2one: identity,
    parse_monetary: parse_monetary,
    parse_one2many: identity,
    parse_reference: identity, // todo
    parse_selection: identity, // todo
    parse_text: identity, // todo

    parse_field: parse_field,
};

return result;

});
