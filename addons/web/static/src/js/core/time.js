odoo.define('web.time', function (require) {
"use strict";

var translation = require('web.translation');
var utils = require('web.utils');

var lpad = utils.lpad;
var rpad = utils.rpad;
var _t = translation._t;

/**
 * Replacer function for JSON.stringify, serializes Date objects to UTC
 * datetime in the OpenERP Server format.
 *
 * However, if a serialized value has a toJSON method that method is called
 * *before* the replacer is invoked. Date#toJSON exists, and thus the value
 * passed to the replacer is a string, the original Date has to be fetched
 * on the parent object (which is provided as the replacer's context).
 *
 * @param {String} k
 * @param {Object} v
 * @returns {Object}
 */
function date_to_utc (k, v) {
    var value = this[k];
    if (!(value instanceof Date)) { return v; }

    return datetime_to_str(value);
}

/**
 * Converts a string to a Date javascript object using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35.832').
 * 
 * The time zone is assumed to be UTC (standard for OpenERP 6.1)
 * and will be converted to the browser's time zone.
 * 
 * @param {String} str A string representing a datetime.
 * @returns {Date}
 */
function str_to_datetime (str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d(?:\.(\d+))?)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid datetime");
    }
    var tmp = new Date(2000,0,1);
    tmp.setUTCMonth(1970);
    tmp.setUTCMonth(0);
    tmp.setUTCDate(1);
    tmp.setUTCFullYear(parseFloat(res[1]));
    tmp.setUTCMonth(parseFloat(res[2]) - 1);
    tmp.setUTCDate(parseFloat(res[3]));
    tmp.setUTCHours(parseFloat(res[4]));
    tmp.setUTCMinutes(parseFloat(res[5]));
    tmp.setUTCSeconds(parseFloat(res[6]));
    tmp.setUTCSeconds(parseFloat(res[6]));
    tmp.setUTCMilliseconds(parseFloat(utils.rpad((res[7] || "").slice(0, 3), 3)));
    return tmp;
}

/**
 * Converts a string to a Date javascript object using OpenERP's
 * date string format (exemple: '2011-12-01').
 * 
 * As a date is not subject to time zones, we assume it should be
 * represented as a Date javascript object at 00:00:00 in the
 * time zone of the browser.
 * 
 * @param {String} str A string representing a date.
 * @returns {Date}
 */
function str_to_date (str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid date");
    }
    var tmp = new Date(2000,0,1);
    tmp.setFullYear(parseFloat(res[1]));
    tmp.setMonth(parseFloat(res[2]) - 1);
    tmp.setDate(parseFloat(res[3]));
    tmp.setHours(0);
    tmp.setMinutes(0);
    tmp.setSeconds(0);
    return tmp;
}

/**
 * Converts a string to a Date javascript object using OpenERP's
 * time string format (exemple: '15:12:35').
 * 
 * The OpenERP times are supposed to always be naive times. We assume it is
 * represented using a javascript Date with a date 1 of January 1970 and a
 * time corresponding to the meant time in the browser's time zone.
 * 
 * @param {String} str A string representing a time.
 * @returns {Date}
 */
function str_to_time (str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d):(\d\d):(\d\d(?:\.(\d+))?)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid time");
    }
    var tmp = new Date();
    tmp.setFullYear(1970);
    tmp.setMonth(0);
    tmp.setDate(1);
    tmp.setHours(parseFloat(res[1]));
    tmp.setMinutes(parseFloat(res[2]));
    tmp.setSeconds(parseFloat(res[3]));
    tmp.setMilliseconds(parseFloat(rpad((res[4] || "").slice(0, 3), 3)));
    return tmp;
}

/**
 * Converts a Date javascript object to a string using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35').
 * 
 * The time zone of the Date object is assumed to be the one of the
 * browser and it will be converted to UTC (standard for OpenERP 6.1).
 * 
 * @param {Date} obj
 * @returns {String} A string representing a datetime.
 */
function datetime_to_str (obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getUTCFullYear(),4) + "-" + lpad(obj.getUTCMonth() + 1,2) + "-"
         + lpad(obj.getUTCDate(),2) + " " + lpad(obj.getUTCHours(),2) + ":"
         + lpad(obj.getUTCMinutes(),2) + ":" + lpad(obj.getUTCSeconds(),2);
}

/**
 * Converts a Date javascript object to a string using OpenERP's
 * date string format (exemple: '2011-12-01').
 * 
 * As a date is not subject to time zones, we assume it should be
 * represented as a Date javascript object at 00:00:00 in the
 * time zone of the browser.
 * 
 * @param {Date} obj
 * @returns {String} A string representing a date.
 */
function date_to_str (obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getFullYear(),4) + "-" + lpad(obj.getMonth() + 1,2) + "-"
         + lpad(obj.getDate(),2);
}

/**
 * Converts a Date javascript object to a string using OpenERP's
 * time string format (exemple: '15:12:35').
 * 
 * The OpenERP times are supposed to always be naive times. We assume it is
 * represented using a javascript Date with a date 1 of January 1970 and a
 * time corresponding to the meant time in the browser's time zone.
 * 
 * @param {Date} obj
 * @returns {String} A string representing a time.
 */
function time_to_str (obj) {
    if (!obj) {
        return false;
    }
    return lpad(obj.getHours(),2) + ":" + lpad(obj.getMinutes(),2) + ":"
         + lpad(obj.getSeconds(),2);
}

function auto_str_to_date (value) {
    try {
        return str_to_datetime(value);
    } catch(e) {}
    try {
        return str_to_date(value);
    } catch(e) {}
    try {
        return str_to_time(value);
    } catch(e) {}
    throw new Error(_.str.sprintf(_t("'%s' is not a correct date, datetime nor time"), value));
}

function auto_date_to_str (value, type) {
    switch(type) {
        case 'datetime':
            return datetime_to_str(value);
        case 'date':
            return date_to_str(value);
        case 'time':
            return time_to_str(value);
        default:
            throw new Error(_.str.sprintf(_t("'%s' is not convertible to date, datetime nor time"), type));
    }
}

/**
 * Convert Python strftime to escaped moment.js format.
 *
 * @param {String} value original format
 */
function strftime_to_moment_format (value) {
    if (_normalize_format_cache[value] === undefined) {
        var isletter = /[a-zA-Z]/,
            output = [],
            inToken = false;

        for (var index=0; index < value.length; ++index) {
            var character = value[index];
            if (character === '%' && !inToken) {
                inToken = true;
                continue;
            }
            if (isletter.test(character)) {
                if (inToken && normalize_format_table[character] !== undefined) {
                    character = normalize_format_table[character];
                } else {
                    character = '[' + character + ']'; // moment.js escape
                }
            }
            output.push(character);
            inToken = false;
        }
        _normalize_format_cache[value] = output.join('');
    }
    return _normalize_format_cache[value];
}

/**
 * Convert moment.js format to python strftime
 *
 * @param {String} value original format
 */
function moment_to_strftime_format(value) {
    var regex = /(MMMM|DDDD|dddd|YYYY|MMM|ddd|mm|ss|ww|WW|MM|YY|hh|HH|DD|A|d)/g;
    return value.replace(regex, function(val){
        return '%'+inverse_normalize_format_table[val];
    });
}

var _normalize_format_cache = {};
var normalize_format_table = {
    // Python strftime to moment.js conversion table
    // See openerp/addons/base/res/res_lang_view.xml
    // for details about supported directives
    'a': 'ddd',
    'A': 'dddd',
    'b': 'MMM',
    'B': 'MMMM',
    'd': 'DD',
    'H': 'HH',
    'I': 'hh',
    'j': 'DDDD',
    'm': 'MM',
    'M': 'mm',
    'p': 'A',
    'S': 'ss',
    'U': 'ww',
    'W': 'WW',
    'w': 'd',
    'y': 'YY',
    'Y': 'YYYY',
    // unsupported directives
    'c': 'ddd MMM D HH:mm:ss YYYY',
    'x': 'MM/DD/YY',
    'X': 'HH:mm:ss'
};
var inverse_normalize_format_table = _.invert(normalize_format_table);



return {
    date_to_utc: date_to_utc,
    str_to_datetime: str_to_datetime,
    str_to_date: str_to_date,
    str_to_time: str_to_time,
    datetime_to_str: datetime_to_str,
    date_to_str: date_to_str,
    time_to_str: time_to_str,
    auto_str_to_date: auto_str_to_date,
    auto_date_to_str: auto_date_to_str,
    strftime_to_moment_format: strftime_to_moment_format,
    moment_to_strftime_format: moment_to_strftime_format,
};

});

