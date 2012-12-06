
openerp.web.dates = function(instance) {
var _t = instance.web._t;

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
instance.web.str_to_datetime = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d)(?:\.\d+)?$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error(_.str.sprintf(_t("'%s' is not a valid datetime"), str));
    }
    var obj = Date.parseExact(res[1] + " UTC", 'yyyy-MM-dd HH:mm:ss zzz');
    if (! obj) {
        throw new Error(_.str.sprintf(_t("'%s' is not a valid datetime"), str));
    }
    return obj;
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
instance.web.str_to_date = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^\d\d\d\d-\d\d-\d\d$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error(_.str.sprintf(_t("'%s' is not a valid date"), str));
    }
    var obj = Date.parseExact(str, 'yyyy-MM-dd');
    if (! obj) {
        throw new Error(_.str.sprintf(_t("'%s' is not a valid date"), str));
    }
    return obj;
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
instance.web.str_to_time = function(str) {
    if(!str) {
        return str;
    }
    var regex = /^(\d\d:\d\d:\d\d)(?:\.\d+)?$/;
    var res = regex.exec(str);
    if ( !res ) {
        throw new Error(_.str.sprintf(_t("'%s' is not a valid time"), str));
    }
    var obj = Date.parseExact("1970-01-01 " + res[1], 'yyyy-MM-dd HH:mm:ss');
    if (! obj) {
        throw new Error(_.str.sprintf(_t("'%s' is not a valid time"), str));
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
instance.web.datetime_to_str = function(obj) {
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
instance.web.date_to_str = function(obj) {
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
instance.web.time_to_str = function(obj) {
    if (!obj) {
        return false;
    }
    return zpad(obj.getHours(),2) + ":" + zpad(obj.getMinutes(),2) + ":"
         + zpad(obj.getSeconds(),2);
};
    
};
