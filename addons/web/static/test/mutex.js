openerp.testing.section('mutex', {
    dependencies: ['web.coresetup'],
    setup: function (instance) {
    }
}, function (test) {
    test('simpleScheduling', function (instance) {
        var m = new $.Mutex();
        var def1 = $.Deferred();
        var def2 = $.Deferred();
        var p1 = m.exec(function() { return def1; });
        var p2 = m.exec(function() { return def2; });
        equal(p1.state(), "pending");
        equal(p2.state(), "pending");
        def1.resolve();
        equal(p1.state(), "resolved");
        equal(p2.state(), "pending");
        def2.resolve();
        equal(p1.state(), "resolved");
        equal(p2.state(), "resolved");
    });
    test('simpleScheduling2', function (instance) {
        var m = new $.Mutex();
        var def1 = $.Deferred();
        var def2 = $.Deferred();
        var p1 = m.exec(function() { return def1; });
        var p2 = m.exec(function() { return def2; });
        equal(p1.state(), "pending");
        equal(p2.state(), "pending");
        def2.resolve();
        equal(p1.state(), "pending");
        equal(p2.state(), "pending");
        def1.resolve();
        equal(p1.state(), "resolved");
        equal(p2.state(), "resolved");
    });
    test('reject', function (instance) {
        var m = new $.Mutex();
        var def1 = $.Deferred();
        var def2 = $.Deferred();
        var def3 = $.Deferred();
        var p1 = m.exec(function() {return def1;});
        var p2 = m.exec(function() {return def2;});
        var p3 = m.exec(function() {return def3;});
        equal(p1.state(), "pending");
        equal(p2.state(), "pending");
        equal(p3.state(), "pending");
        def1.resolve();
        equal(p1.state(), "resolved");
        equal(p2.state(), "pending");
        equal(p3.state(), "pending");
        def2.reject();
        equal(p1.state(), "resolved");
        equal(p2.state(), "rejected");
        equal(p3.state(), "pending");
        def3.resolve();
        equal(p1.state(), "resolved");
        equal(p2.state(), "rejected");
        equal(p3.state(), "resolved");
    });
});
