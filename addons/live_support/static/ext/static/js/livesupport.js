
define(["nova", "jquery", "underscore"], function(nova, $, _) {
    var livesupport = {};

    livesupport.main = function(server_url, db, login, password) {
        console.log("hello");
        var connection = new Connection(new JsonRPCConnector(server_url), db, login, password);
        var userModel = connection.getModel("res.users");
        userModel.call("search", [[["login", "=", "admin"]]]).then(function(result) {
            console.log(result);
        });
    };

    function jsonRpc(url, fct_name, params, settings) {
        var data = {
            jsonrpc: "2.0",
            method: fct_name,
            params: params,
            id: Math.floor(Math.random()* (1000*1000*1000)),
        };
        return $.ajax(url, _.extend({}, settings, {
            url: url,
            dataType: 'json',
            type: 'POST',
            data: JSON.stringify(data),
            contentType: 'application/json',
        })).pipe(function(result) {
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

    var JsonRPCConnector = nova.Class.$extend({
        __init__: function(url) {
            this.url = url + "/jsonrpc";
        },
        getService: function(serviceName) {
            return new Service(this, serviceName);
        },
        send: function(serviceName, method, args) {
            return jsonRpc(this.url, "call", {"service": serviceName, "method": method, "args": args});
        },
    });

    var Service = nova.Class.$extend({
        __init__: function(connector, serviceName) {
            this.connector = connector;
            this.serviceName = serviceName;
        },
        call: function(method, args) {
            return this.connector.send(this.serviceName, method, args);
        },
    });

    var AuthenticationError = nova.Error.$extend({
        name: "AuthenticationError",
        defaultMessage: "An error occured during authentication."
    });

    var Connection = nova.Class.$extend({
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
                throw new AuthenticationError();

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
            return new Model(this, modelName);
        },
        getService: function(serviceName) {
            return this.connector.getService(serviceName);
        },
    });

    var Model = nova.Class.$extend({
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

    return livesupport;
});
