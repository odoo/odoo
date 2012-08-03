
openerp.web.dates = function(openerp) {

/**
 * Converts a string to a Date javascript object using OpenERP's
 * datetime string format (exemple: '2011-12-01 15:12:35').
 * 
 * The time zone is assumed to be UTC (standard for OpenERP 6.1)
 * and will be converted to the browser's time zone.
 * 
 * @param {String} str A string representing a datetime.
 * @returns {Date}
 */
openerp.web.str_to_datetime = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)(?:\.\d+)?$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid datetime");
    }
    return new Date(Date.UTC(
        parseInt(res[1], 10),
        parseInt(res[2], 10) - 1,
        parseInt(res[3], 10),
        parseInt(res[4], 10),
        parseInt(res[5], 10),
        parseInt(res[6], 10)
    ));
};

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
openerp.web.str_to_date = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid date");
    }
    return new Date(
        parseInt(res[1], 10),
        parseInt(res[2], 10) - 1,
        parseInt(res[3], 10)
    );
};

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
openerp.web.str_to_time = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d):(\d\d):(\d\d)(?:\.\d+)?$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error("'" + str + "' is not a valid time");
    }
    return new Date(
        1970, 0, 1, parseInt(res[1], 10), parseInt(res[2], 10), parseInt(res[3], 10));
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
    return new Array(size - str.length + 1).join('0') + str;
};

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
openerp.web.datetime_to_str = function(obj) {
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
 * As a date is not subject to time zones, we assume it should be
 * represented as a Date javascript object at 00:00:00 in the
 * time zone of the browser.
 * 
 * @param {Date} obj
 * @returns {String} A string representing a date.
 */
openerp.web.date_to_str = function(obj) {
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
 * The OpenERP times are supposed to always be naive times. We assume it is
 * represented using a javascript Date with a date 1 of January 1970 and a
 * time corresponding to the meant time in the browser's time zone.
 * 
 * @param {Date} obj
 * @returns {String} A string representing a time.
 */
openerp.web.time_to_str = function(obj) {
    if (!obj) {
        return false;
    }
    return zpad(obj.getHours(),2) + ":" + zpad(obj.getMinutes(),2) + ":"
         + zpad(obj.getSeconds(),2);
};
    
};
