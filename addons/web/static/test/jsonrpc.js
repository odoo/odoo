openerp.testing.section('jsonrpc', {},
function (test) {
    test('basic', {asserts: 1}, function () {
        var session = new openerp.web.JsonRPC();
        session.setup();
        return session.rpc("/gen_session_id", {}).then(function(result) {
            ok(result.length > 0, "Result returned by /gen_session_id");
        });
    });
});
