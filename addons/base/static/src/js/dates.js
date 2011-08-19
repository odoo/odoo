
openerp.base.dates = function(openerp) {

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
openerp.base.str_to_datetime = function(str) {
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
openerp.base.str_to_date = function(str) {
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
openerp.base.str_to_time = function(str) {
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
    return new Array(size - str.length + 1).join('0') + str;
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
openerp.base.datetime_to_str = function(obj) {
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
openerp.base.date_to_str = function(obj) {
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
openerp.base.time_to_str = function(obj) {
    if (!obj) {
        return false;
    }
    return zpad(obj.getHours(),2) + ":" + zpad(obj.getMinutes(),2) + ":"
         + zpad(obj.getSeconds(),2);
};
    
};
