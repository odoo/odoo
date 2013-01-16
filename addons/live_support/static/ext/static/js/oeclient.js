
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
            this.url = url + "/jsonrpc";
        },
        send: function(serviceName, method, args) {
            return oeclient.jsonRpc(this.url, "call", {"service": serviceName, "method": method, "args": args});
        },
    });

    oeclient.JsonpRPCConnector = oeclient.JsonRPCConnector.$extend({
        send: function(serviceName, method, args) {
            return oeclient.jsonpRpc(this.url, "call", {"service": serviceName, "method": method, "args": args});
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
    });

    return oeclient;

});