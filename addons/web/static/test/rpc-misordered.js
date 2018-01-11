openerp.testing.section('misordered resolution managemeng', {
    dependencies: ['web.data']
}, function (test) {
    test('Resolve all correctly ordered, sync', function (instance) {
        var dm = new instance.web.DropMisordered(), flag = false;

        var d1 = $.Deferred(), d2 = $.Deferred(),
            r1 = dm.add(d1), r2 = dm.add(d2);

        $.when(r1, r2).done(function () {
            flag = true;
        });
        d1.resolve();
        d2.resolve();

        ok(flag);
    });
    test("Don't resolve mis-ordered, sync", function (instance) {
        var dm = new instance.web.DropMisordered(),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(), d2 = $.Deferred();
        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();

        // d1 is in limbo
        ok(!done1);
        ok(!fail1);
        // d2 is resolved
        ok(done2);
        ok(!fail2);
    });
    test('Fail mis-ordered flag, sync', function (instance) {
        var dm = new instance.web.DropMisordered(true),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(), d2 = $.Deferred();
        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();

        // d1 is failed
        ok(!done1);
        ok(fail1);
        // d2 is resolved
        ok(done2);
        ok(!fail2);
    });

    test('Resolve all correctly ordered, async', {asserts: 1}, function (instance) {
        var dm = new instance.web.DropMisordered();

        var d1 = $.Deferred(), d2 = $.Deferred(),
            r1 = dm.add(d1), r2 = dm.add(d2);

        setTimeout(function () { d1.resolve(); }, 100);
        setTimeout(function () { d2.resolve(); }, 200);

        return $.when(r1, r2).done(function () {
            ok(true);
        });
    });
    test("Don't resolve mis-ordered, async", {asserts: 4}, function (instance) {
        var dm = new instance.web.DropMisordered(),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(), d2 = $.Deferred();
        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        setTimeout(function () { d1.resolve(); }, 200);
        setTimeout(function () { d2.resolve(); }, 100);

        var done = $.Deferred();
        setTimeout(function () {
            // d1 is in limbo
            ok(!done1);
            ok(!fail1);
            // d2 is resolved
            ok(done2);
            ok(!fail2);
            done.resolve();
        }, 400);
        return $.when(d1, d2, done);
    });
    test('Fail mis-ordered flag, async', {asserts: 4}, function (instance) {
        var dm = new instance.web.DropMisordered(true),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(), d2 = $.Deferred();
        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        setTimeout(function () { d1.resolve(); }, 200);
        setTimeout(function () { d2.resolve(); }, 100);

        var done = $.Deferred();
        setTimeout(function () {
            // d1 is failed
            ok(!done1);
            ok(fail1);
            // d2 is resolved
            ok(done2);
            ok(!fail2);
            done.resolve();
        }, 400);
        return $.when(d1, d2, done);
    });
});
