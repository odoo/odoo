
define(["nova", "jquery", "underscore", "oeclient"], function(nova, $, _, oeclient) {
    var livesupport = {};

    livesupport.main = function(server_url, db, login, password) {
        console.log("hello");
        var connection = new oeclient.Connection(new oeclient.JsonpRPCConnector(server_url), db, login, password);
        var userModel = connection.getModel("res.users");
        userModel.call("search", [[["login", "=", "admin"]]]).then(function(result) {
            console.log(result);
        });
    };

    return livesupport;
});
