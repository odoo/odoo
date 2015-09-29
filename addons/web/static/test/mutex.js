odoo.define_section('web.mutex', ['web.utils'], function (test) {

    test('simple scheduling', function (assert, utils) {
        var m = new utils.Mutex();

        var def1 = $.Deferred(),
            def2 = $.Deferred();

        var p1 = m.exec(function () { return def1; });
        var p2 = m.exec(function () { return def2; });

        assert.equal(p1.state(), "pending");
        assert.equal(p2.state(), "pending");

        def1.resolve();
        assert.equal(p1.state(), "resolved");
        assert.equal(p2.state(), "pending");

        def2.resolve();
        assert.equal(p1.state(), "resolved");
        assert.equal(p2.state(), "resolved");
    });

    test('simpleScheduling2', function (assert, utils) {
        var m = new utils.Mutex();

        var def1 = $.Deferred(),
            def2 = $.Deferred();

        var p1 = m.exec(function() { return def1; });
        var p2 = m.exec(function() { return def2; });

        assert.equal(p1.state(), "pending");
        assert.equal(p2.state(), "pending");
        
        def2.resolve();
        assert.equal(p1.state(), "pending");
        assert.equal(p2.state(), "pending");
        
        def1.resolve();
        assert.equal(p1.state(), "resolved");
        assert.equal(p2.state(), "resolved");
    });

    test('reject', function (assert, utils) {
        var m = new utils.Mutex();

        var def1 = $.Deferred(),
            def2 = $.Deferred(),
            def3 = $.Deferred();
        
        var p1 = m.exec(function() {return def1;});
        var p2 = m.exec(function() {return def2;});
        var p3 = m.exec(function() {return def3;});
        
        assert.equal(p1.state(), "pending");
        assert.equal(p2.state(), "pending");
        assert.equal(p3.state(), "pending");

        def1.resolve();
        assert.equal(p1.state(), "resolved");
        assert.equal(p2.state(), "pending");
        assert.equal(p3.state(), "pending");

        def2.reject();
        assert.equal(p1.state(), "resolved");
        assert.equal(p2.state(), "rejected");
        assert.equal(p3.state(), "pending");

        def3.resolve();
        assert.equal(p1.state(), "resolved");
        assert.equal(p2.state(), "rejected");
        assert.equal(p3.state(), "resolved");
    });
});

