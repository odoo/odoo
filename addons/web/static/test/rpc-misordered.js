odoo.define_section('web.misordered-resolution', ['web.utils'], function (test) {

    test('resolve all correctly ordered, sync', function (assert, utils) {
        var dm = new utils.DropMisordered(),
            flag = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        var r1 = dm.add(d1),
            r2 = dm.add(d2);

        $.when(r1, r2).done(function () {
            flag = true;
        });

        d1.resolve();
        d2.resolve();

        assert.ok(flag);
    });

    test("don't resolve mis-ordered, sync", function (assert, utils) {
        var dm = new utils.DropMisordered(),
            done1 = false,
            done2 = false,
            fail1 = false,
            fail2 = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();

        // d1 is in limbo
        assert.ok(!done1);
        assert.ok(!fail1);

        // d2 is resolved
        assert.ok(done2);
        assert.ok(!fail2);
    });

    test('fail mis-ordered flag, sync', function (assert, utils) {
        var dm = new utils.DropMisordered(true),
            done1 = false,
            done2 = false,
            fail1 = false,
            fail2 = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        d2.resolve();
        d1.resolve();

        // d1 is in limbo
        assert.ok(!done1);
        assert.ok(fail1);

        // d2 is resolved
        assert.ok(done2);
        assert.ok(!fail2);

    });

    test('resolve all correctly ordered, async', function (assert, utils) {
        var done = assert.async();
        assert.expect(1);

        var dm = new utils.DropMisordered();

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        var r1 = dm.add(d1),
            r2 = dm.add(d2);

        setTimeout(function () { d1.resolve(); }, 50);
        setTimeout(function () { d2.resolve(); }, 100);

        $.when(r1, r2).done(function () {
            assert.ok(true);
            done();
        });
    });

    test("don't resolve mis-ordered, async", function (assert, utils) {
        var done = assert.async();
        assert.expect(4);

        var dm = new utils.DropMisordered(),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(), 
            d2 = $.Deferred();
        
        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        setTimeout(function () { d1.resolve(); }, 100);
        setTimeout(function () { d2.resolve(); }, 50);

        setTimeout(function () {
            // d1 is in limbo
            assert.ok(!done1);
            assert.ok(!fail1);

            // d2 is resolved
            assert.ok(done2);
            assert.ok(!fail2);
            done();
        }, 150);
    });

    test('fail mis-ordered flag, async', function (assert, utils) {
        var done = assert.async();
        assert.expect(4);

        var dm = new utils.DropMisordered(true),
            done1 = false, done2 = false,
            fail1 = false, fail2 = false;

        var d1 = $.Deferred(),
            d2 = $.Deferred();

        dm.add(d1).done(function () { done1 = true; })
                  .fail(function () { fail1 = true; });
        dm.add(d2).done(function () { done2 = true; })
                  .fail(function () { fail2 = true; });

        setTimeout(function () { d1.resolve(); }, 100);
        setTimeout(function () { d2.resolve(); }, 50);

        setTimeout(function () {
            // d1 is failed
            assert.ok(!done1);
            assert.ok(fail1);

            // d2 is resolved
            assert.ok(done2);
            assert.ok(!fail2);
            done();
        }, 150);
    });

});



