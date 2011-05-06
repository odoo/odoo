
openerp.base.dates = function(openerp) {

openerp.base.parse_datetime = function(str) {
    if(!str) {
        return str;
    }
    var regex = /\d\d\d\d-\d\d-\d\) \d\d:\d\d:\d\d/;
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

/**
 * Just a simple function to add some '0' if an integer it too small.
 */
var fts = function(str, size) {
    str = "" + str;
    var to_add = "";
    _.each(_.range(size - str.length), function() {
        to_add = to_add + "0";
    });
    return to_add + str;
};

openerp.base.format_datetime = function(obj) {
    if(! str) {
        return false;
    }
    return fts(obj.getUTCFullYear(),4) + "-" + fts(obj.getUTCMonth() + 1,2) + "-"
        + fts(obj.getUTCDate(),2) + " " + fts(obj.getUTCHours(),2) + ":"
        + fts(obj.getUTCMinutes(),2) + ":" + fts(obj.getUTCSeconds(),2);
};

openerp.base.format_date = function(obj) {
    if(! str) {
        return false;
    }
    return fts(obj.getFullYear(),4) + "-" + fts(obj.getMonth() + 1,2) + "-"
        + fts(obj.getDate(),2);
};

openerp.base.format_time = function(obj) {
    if(! str) {
        return false;
    }
    return fts(obj.getHours(),2) + ":" + fts(obj.getMinutes(),2) + ":"
        + fts(obj.getSeconds(),2);
};
    
};