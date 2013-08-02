openerp.testing.section('jsonrpc', {},
function (test) {
    test('basic', {asserts: 1}, function () {
        var session = new openerp.web.JsonRPC();
        return session.rpc("/gen_session_id", {}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
    test('jsonprpc', {asserts: 1}, function () {
        var session = new openerp.web.JsonRPC();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
    test('jsonprpc2', {asserts: 1}, function () {
        var session = new openerp.web.JsonRPC();
        session.origin_server = false;
        return session.rpc("/gen_session_id", {}, {force2step: true}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
});
