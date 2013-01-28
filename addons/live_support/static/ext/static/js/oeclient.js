
define(["underscore", "jquery", "nova"], function(_, $, nova) {

    var oeclient = {};

    var genericJsonRPC = function(fct_name, params, fct) {
        var data = {
            jsonrpc: "2.0",
            method: fct_name,
            params: params,
            id: Math.floor(Math.random()* (1000*1000*1000)),
        };
        return fct(data).pipe(function(result) {
            if (result.error !== undefined) {
                console.error("Server application error", result.error);
                return $.Deferred().reject("server", result.error);
            } else {
                return result.result;
            }
        }, function() {
            console.error("JsonRPC communication error", _.toArray(arguments));
            var def = $.Deferred();
            return def.reject.apply(def, ["communication"].concat(_.toArray(arguments)));
        });
    };

    oeclient.jsonRpc = function(url, fct_name, params, settings) {
        return genericJsonRPC(fct_name, params, function(data) {
            return $.ajax(url, _.extend({}, settings, {
                url: url,
                dataType: 'json',
                type: 'POST',
                data: JSON.stringify(data),
                contentType: 'application/json',
            }));
        });
    };

    oeclient.jsonpRpc = function(url, fct_name, params, settings) {
        return genericJsonRPC(fct_name, params, function(data) {
            return $.ajax(url, _.extend({}, settings, {
                url: url,
                dataType: 'jsonp',
                jsonp: 'jsonp',
                type: 'GET',
                cache: false,
                data: {r: JSON.stringify(data)},
            }));
        });
    };

    oeclient.Connector = nova.Class.$extend({
        getService: function(serviceName) {
            return new oeclient.Service(this, serviceName);
        },
    });

    oeclient.JsonRPCConnector = oeclient.Connector.$extend({
        __init__: function(url) {
            this.url = url;
        },
        call: function(sub_url, content) {
            return oeclient.jsonRpc(this.url + sub_url, "call", content);
        },
        send: function(serviceName, method, args) {
            return this.call("/jsonrpc", {"service": serviceName, "method": method, "args": args});
        },
    });

    oeclient.JsonpRPCConnector = oeclient.JsonRPCConnector.$extend({
        call: function(sub_url, content) {
            return oeclient.jsonpRpc(this.url + sub_url, "call", content);
        },
    });

    oeclient.Service = nova.Class.$extend({
        __init__: function(connector, serviceName) {
            this.connector = connector;
            this.serviceName = serviceName;
        },
        call: function(method, args) {
            return this.connector.send(this.serviceName, method, args);
        },
    });

    oeclient.AuthenticationError = nova.Error.$extend({
        name: "oeclient.AuthenticationError",
        defaultMessage: "An error occured during authentication."
    });

    oeclient.Connection = nova.Class.$extend({
        __init__: function(connector, database, login, password, userId) {
            this.connector = connector;
            this.setLoginInfo(database, login, password, userId);
            this.userContext = null;
        },
        setLoginInfo: function(database, login, password, userId) {
            this.database = database;
            this.login = login;
            this.password = password;
            this.userId = userId;
        },
        checkLogin: function(force) {
            force = force === undefined ? true: force;
            if (this.userId && ! force)
                return $.when();

            if (! this.database || ! this.login || ! this.password)
                throw new oeclient.AuthenticationError();

            return this.getService("common").call("login", [this.database, this.login, this.password])
                    .then(_.bind(function(result) {
                this.userId = result;
                if (! this.userId) {
                    console.error("Authentication failure");
                    return $.Deferred().reject({message:"Authentication failure"});
                }
            }, this));
        },
        getUserContext: function() {
            if (! this.userContext) {
                return this.getModel("res.users").call("context_get").then(_.bind(function(result) {
                    this.userContext = result;
                    return this.userContext;
                }, this));
            }
            return $.when(this.userContext);
        },
        getModel: function(modelName) {
            return new oeclient.Model(this, modelName);
        },
        getService: function(serviceName) {
            return this.connector.getService(serviceName);
        },
    });

    oeclient.Model = nova.Class.$extend({
        __init__: function(connection, modelName) {
            this.connection = connection;
            this.modelName = modelName;
        },
        call: function(method, args, kw) {
            return this.connection.checkLogin().then(_.bind(function() {
                return this.connection.getService("object").call("execute_kw", [
                    this.connection.database,
                    this.connection.userId,
                    this.connection.password,
                    this.modelName,
                    method,
                    args || [],
                    kw || {},
                ]);
            }, this));
        },
        search_read: function(domain, fields, offset, limit, order, context) {
            return this.call("search", [domain || [], offset || 0, limit || false, order || false, context || {}]).then(_.bind(function(record_ids) {
                if (! record_ids) {
                    return [];
                }
                return this.call("read", [record_ids, fields || [], context || {}]).then(function(records) {
                    var index = {};
                    _.each(records, function(r) {
                        index[r.id] = r;
                    });
                    var res = [];
                    _.each(record_ids, function(id) {
                        if (index[id])
                            res.push(index[id]);
                    });
                    return res;
                });
            }, this));
        },
    });

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
    oeclient.str_to_datetime = function(str) {
        if(!str) {
            return str;
        }
        var regex = /^(\d\d\d\d)-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d(?:\.\d+)?)$/;
        var res = regex.exec(str);
        if ( !res ) {
            throw new Error("'" + str + "' is not a valid datetime");
        }
        var tmp = new Date();
        tmp.setUTCFullYear(parseFloat(res[1]));
        tmp.setUTCMonth(parseFloat(res[2]) - 1);
        tmp.setUTCDate(parseFloat(res[3]));
        tmp.setUTCHours(parseFloat(res[4]));
        tmp.setUTCMinutes(parseFloat(res[5]));
        tmp.setUTCSeconds(parseFloat(res[6]));
        return tmp;
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
    oeclient.str_to_date = function(str) {
        if(!str) {
            return str;
        }
        var regex = /^(\d\d\d\d)-(\d\d)-(\d\d)$/;
        var res = regex.exec(str);
        if ( !res ) {
            throw new Error("'" + str + "' is not a valid date");
        }
        var tmp = new Date();
        tmp.setFullYear(parseFloat(res[1]));
        tmp.setMonth(parseFloat(res[2]) - 1);
        tmp.setDate(parseFloat(res[3]));
        tmp.setHours(0);
        tmp.setMinutes(0);
        tmp.setSeconds(0);
        return tmp;
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
    oeclient.str_to_time = function(str) {
        if(!str) {
            return str;
        }
        var regex = /^(\d\d):(\d\d):(\d\d(?:\.\d+)?)$/;
        var res = regex.exec(str);
        if ( !res ) {
            throw new Error("'" + str + "' is not a valid time");
        }
        debugger;
        var tmp = new Date();
        tmp.setFullYear(1970);
        tmp.setMonth(0);
        tmp.setDate(1);
        tmp.setHours(parseFloat(res[1]));
        tmp.setMinutes(parseFloat(res[2]));
        tmp.setSeconds(parseFloat(res[3]));
        return tmp;
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
    oeclient.datetime_to_str = function(obj) {
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
    oeclient.date_to_str = function(obj) {
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
    oeclient.time_to_str = function(obj) {
        if (!obj) {
            return false;
        }
        return zpad(obj.getHours(),2) + ":" + zpad(obj.getMinutes(),2) + ":"
             + zpad(obj.getSeconds(),2);
    };

    return oeclient;

});