(function() {

var ropenerp = window.openerp;

var openerp = ropenerp.declare($, _, QWeb2);

ropenerp.testing.section('jsonrpc', {},
function (test) {
    test('basic-jsonrpc', {asserts: 1}, function () {
        var session = new openerp.Session();
        return session.rpc("/gen_session_id", {}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
    test('basic-jsonprpc', {asserts: 1}, function () {
        var session = new openerp.Session();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
    // desactivated because the phantomjs runner crash
    /*test('basic-jsonprpc2', {asserts: 1}, function () {
        var session = new openerp.Session();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}, {force2step: true}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });*/
    test('session-jsonrpc', {asserts: 2}, function () {
        var session = new openerp.Session();
        var tmp = _.uniqueId("something");
        return session.rpc("/web/tests/set_session_value", {value: tmp}).then(function() {
            ok(true, "set_session returned");
            return session.rpc("/web/tests/get_session_value", {});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
        });
    });
    test('session-jsonprpc', {asserts: 2}, function () {
        var session = new openerp.Session();
        session.origin_server = false;
        var tmp = _.uniqueId("something");
        return session.rpc("/web/tests/set_session_value", {value: tmp}).then(function() {
            ok(true, "set_session returned");
            return session.rpc("/web/tests/get_session_value", {});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
        });
    });
    // desactivated because the phantomjs runner crash
    /*test('session-jsonprpc2', {asserts: 2}, function () {
        var session = new openerp.Session();
        session.origin_server = false;
        var tmp = _.uniqueId("something");
        return session.rpc("/web/tests/set_session_value", {value: tmp}, {force2step: true}).then(function() {
            ok(true, "set_session returned");
            return session.rpc("/web/tests/get_session_value", {}, {force2step: true});
        }).then(function(result) {
            equal(result, tmp, "Got the same value from the session");
        });
    });*/
    test('overridesession-jsonrpc', {asserts: 4}, function () {
        var origin_session = new openerp.Session();
        var origin_tmp = _.uniqueId("something");
        var session = new openerp.Session(null, null, {override_session: true});
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
        var origin_session = new openerp.Session();
        var origin_tmp = _.uniqueId("something");
        var session = new openerp.Session(null, null, {override_session: true});
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
    // desactivated because the phantomjs runner crash
    /*test('overridesession-jsonprpc2', {asserts: 4}, function () {
        var origin_session = new openerp.Session();
        var origin_tmp = _.uniqueId("something");
        var session = new openerp.Session(null, null, {override_session: true});
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
    });*/
    test('timeout-jsonrpc', {asserts: 1}, function () {
        var session = new openerp.Session();
        return session.rpc("/gen_session_id", {}, {timeout: 1}).then(function() {
            ok(false, "the request incorrectly succeeded");
            return $.when();
        }, function(a, e) {
            e.preventDefault();
            ok(true, "the request correctly failed");
            return $.when();
        });
    });
    test('timeout-jsonprpc', {asserts: 1}, function () {
        var session = new openerp.Session();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}, {timeout: 1}).then(function() {
            ok(false, "the request incorrectly succeeded");
            return $.when();
        }, function(a, e) {
            e.preventDefault();
            ok(true, "the request correctly failed");
            return $.when();
        });
    });
    // desactivated because the phantomjs runner crash
    /*test('timeout-jsonprpc2', {asserts: 1}, function () {
        var session = new openerp.Session();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}, {force2step: true, timeout: 1}).then(function() {
            ok(false, "the request incorrectly succeeded");
            return $.when();
        }, function(a, e) {
            e.preventDefault();
            ok(true, "the request correctly failed");
            return $.when();
        });
    });*/
});

})();
