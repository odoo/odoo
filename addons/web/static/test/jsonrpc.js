(function() {

var ropenerp = window.openerp;

var openerp = ropenerp.declare($, _, QWeb2);

ropenerp.testing.section('jsonrpc', {},
function (test) {
    test('basic-jsonrpc', {asserts: 1}, function () {
        var session = new openerp.web.Session();
        return session.rpc("/gen_session_id", {}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
    test('basic-jsonprpc', {asserts: 1}, function () {
        var session = new openerp.web.Session();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
    test('basic-jsonprpc2', {asserts: 1}, function () {
        var session = new openerp.web.Session();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}, {force2step: true}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
    test('session-jsonrpc', {asserts: 2}, function () {
        var session = new openerp.web.Session();
        var tmp = _.uniqueId("something");
        return session.rpc("/web/tests/set_session_value", {value: tmp}).then(function() {
            ok(true, "set_session returned");
            return session.rpc("/web/tests/get_session_value", {});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
        });
    });
    test('session-jsonprpc', {asserts: 2}, function () {
        var session = new openerp.web.Session();
        session.origin_server = false;
        var tmp = _.uniqueId("something");
        return session.rpc("/web/tests/set_session_value", {value: tmp}).then(function() {
            ok(true, "set_session returned");
            return session.rpc("/web/tests/get_session_value", {});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
        });
    });
    test('session-jsonprpc2', {asserts: 2}, function () {
        var session = new openerp.web.Session();
        session.origin_server = false;
        var tmp = _.uniqueId("something");
        return session.rpc("/web/tests/set_session_value", {value: tmp}, {force2step: true}).then(function() {
            ok(true, "set_session returned");
            return session.rpc("/web/tests/get_session_value", {}, {force2step: true});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
        });
    });
    test('overridesession-jsonrpc', {asserts: 4}, function () {
        var origin_session = new openerp.web.Session();
        var origin_tmp = _.uniqueId("something");
        var session = new openerp.web.Session(null, null, {override_session: true});
        var tmp = _.uniqueId("something_else");
        return session.rpc("/web/tests/set_session_value", {value: tmp}).then(function() {
            ok(true, "set_session returned");
            return origin_session.rpc("/web/tests/set_session_value", {value: origin_tmp});
        }).then(function(result) {
            ok(true, "set_session on origin returned");
            return session.rpc("/web/tests/get_session_value", {});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
            notEqual(result, origin_tmp, "Values in the different sessions should be different");
        });
    });
    test('overridesession-jsonprpc', {asserts: 4}, function () {
        var origin_session = new openerp.web.Session();
        var origin_tmp = _.uniqueId("something");
        var session = new openerp.web.Session(null, null, {override_session: true});
        var tmp = _.uniqueId("something_else");
        session.origin_server = false;
        return session.rpc("/web/tests/set_session_value", {value: tmp}).then(function() {
            ok(true, "set_session returned");
            return origin_session.rpc("/web/tests/set_session_value", {value: origin_tmp});
        }).then(function(result) {
            ok(true, "set_session on origin returned");
            return session.rpc("/web/tests/get_session_value", {});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
            notEqual(result, origin_tmp, "Values in the different sessions should be different");
        });
    });
    test('overridesession-jsonprpc2', {asserts: 4}, function () {
        var origin_session = new openerp.web.Session();
        var origin_tmp = _.uniqueId("something");
        var session = new openerp.web.Session(null, null, {override_session: true});
        var tmp = _.uniqueId("something_else");
        session.origin_server = false;
        return session.rpc("/web/tests/set_session_value", {value: tmp}, {force2step: true}).then(function() {
            ok(true, "set_session returned");
            return origin_session.rpc("/web/tests/set_session_value", {value: origin_tmp});
        }).then(function(result) {
            ok(true, "set_session on origin returned");
            return session.rpc("/web/tests/get_session_value", {}, {force2step: true});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
            notEqual(result, origin_tmp, "Values in the different sessions should be different");
        });
    });
});

var login = "admin";
var password = "admin";
var db = null;

ropenerp.testing.section('jsonrpc-auth', {
    setup: function() {
        var session = new openerp.web.Session();
        return session.session_reload().then(function() {
            db = session.db;
            ok(db, "db must be valid");
        });
    },
},
function (test) {
    test('basic-auth', {asserts: 4}, function () {
        var session = new openerp.web.Session();
        equal(session.uid, undefined, "uid is expected to be undefined");
        return session.session_authenticate(db, login, password).then(function() {
            equal(session.uid, 1, "Admin's uid must be 1");
            return session.rpc("/web/dataset/call_kw", {
                model: "res.users",
                method: "read",
                args: [1, ["login"]],
                kwargs: {},
            }).then(function(result) {
                equal(result.login, "admin", "Admin's name must be 'admin'");
            });
        });
    });
    test('share-sessions', {asserts: 7}, function () {
        var session = new openerp.web.Session();
        var session2;
        return session.session_authenticate(db, login, password).then(function() {
            equal(session.uid, 1, "Admin's uid must be 1");
            session2 = new openerp.web.Session(null, null, {session_id: session.session_id});
            equal(session2.uid, undefined, "uid should be undefined");
            equal(session2.override_session, true, "overwrite_session should be true");
            return session2.session_reload();
        }).then(function() {
            equal(session2.uid, session.uid);
            equal(session2.uid, 1);
            return session2.rpc("/web/dataset/call_kw", {
                model: "res.users",
                method: "read",
                args: [1, ["login"]],
                kwargs: {},
            }).then(function(result) {
                equal(result.login, "admin", "Admin's name must be 'admin'");
            });
        });
    });
});

})();
