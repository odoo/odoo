openerp.testing.section('testing.stack', function (test) {
    // I heard you like tests, so I put tests in your testing infrastructure,
    // so you can test what you test
    var reject = function () {
        // utility function, rejects a success
        var args = _.toArray(arguments);
        return $.Deferred(function (d) {
            d.reject.apply(d, ["unexpected success"].concat(args));
        });
    };
    test('direct, value, success', {asserts: 1}, function () {
        var s = openerp.testing.Stack();
        return s.execute(function () {
            return 42;
        }).then(function (val) {
            strictEqual(val, 42, "should return the handler value");
        });
    });
    test('direct, deferred, success', {asserts: 1}, function () {
        var s = openerp.testing.Stack();
        return s.execute(function () {
            return $.when(42);
        }).then(function (val) {
            strictEqual(val, 42, "should return the handler value");
        });
    });
    test('direct, deferred, failure', {asserts: 1}, function () {
        var s = openerp.testing.Stack();
        return s.execute(function () {
            return $.Deferred(function (d) {
                d.reject("failed");
            });
        }).then(reject, function (f) {
            strictEqual(f, "failed", "should propagate failure");
            return $.when();
        });
    });

    test('successful setup', {asserts: 2}, function () {
        var setup_done = false;
        var s = openerp.testing.Stack();
        return s.push(function () {
            return $.Deferred(function (d) {
                setTimeout(function () {
                    setup_done = true;
                    d.resolve(2);
                }, 50);
            });
        }).execute(function () {
            return 42;
        }).then(function (val) {
            ok(setup_done, "should have executed setup");
            strictEqual(val, 42, "should return executed function value (not setup)");
        });
    });
    test('successful teardown', {asserts: 2}, function () {
        var teardown = false;
        var s = openerp.testing.Stack();
        return s.push(null, function () {
            return $.Deferred(function (d) {
                setTimeout(function () {
                    teardown = true;
                    d.resolve(2);
                }, 50);
            });
        }).execute(function () {
            return 42;
        }).then(function (val) {
            ok(teardown, "should have executed teardown");
            strictEqual(val, 42, "should return executed function value (not setup)");
        });
    });
    test('successful setup and teardown', {asserts: 3}, function () {
        var setup = false, teardown = false;
        var s = openerp.testing.Stack();
        return s.push(function () {
            return $.Deferred(function (d) {
                setTimeout(function () {
                    setup = true;
                    d.resolve(2);
                }, 50);
            });
        }, function () {
            return $.Deferred(function (d) {
                setTimeout(function () {
                    teardown = true;
                    d.resolve(2);
                }, 50);
            });
        }).execute(function () {
            return 42;
        }).then(function (val) {
            ok(setup, "should have executed setup");
            ok(teardown, "should have executed teardown");
            strictEqual(val, 42, "should return executed function value (not setup)");
        });
    });

    test('multiple setups', {asserts: 2}, function () {
        var setups = 0;
        var s = openerp.testing.Stack();
        return s.push(function () {
            setups++;
        }).push(function () {
            setups++;
        }).push(function () {
            setups++;
        }).push(function () {
            setups++;
        }).execute(function () {
            return 42;
        }).then(function (val) {
            strictEqual(setups, 4, "should have executed all setups of stack");
            strictEqual(val, 42);
        });
    });
    test('multiple teardowns', {asserts: 2}, function () {
        var teardowns = 0;
        var s = openerp.testing.Stack();
        return s.push(null, function () {
            teardowns++;
        }).push(null, function () {
            teardowns++;
        }).push(null, function () {
            teardowns++;
        }).push(null, function () {
            teardowns++;
        }).execute(function () {
            return 42;
        }).then(function (val) {
            strictEqual(teardowns, 4, "should have executed all teardowns of stack");
            strictEqual(val, 42);
        });
    });
    test('holes in setups', {asserts: 2}, function () {
        var setups = [];
        var s = openerp.testing.Stack();
        return s.push(function () {
            setups.push(0);
        }).push().push().push(function () {
            setups.push(3);
        }).push(function () {
            setups.push(4);
        }).push().push(function () {
            setups.push(6);
        }).execute(function () {
            return 42;
        }).then(function (val) {
            deepEqual(setups, [0, 3, 4, 6],
                "should have executed setups in correct order");
            strictEqual(val, 42);
        });
    });
    test('holes in teardowns', {asserts: 2}, function () {
        var teardowns = [];
        var s = openerp.testing.Stack();
        return s.push(null, function () {
            teardowns.push(0);
        }).push().push().push(null, function () {
            teardowns.push(3);
        }).push(null, function () {
            teardowns.push(4);
        }).push().push(null, function () {
            teardowns.push(6);
        }).execute(function () {
            return 42;
        }).then(function (val) {
            deepEqual(teardowns, [6, 4, 3, 0],
                "should have executed teardowns in correct order");
            strictEqual(val, 42);
        });

    });

    test('failed setup', {asserts: 5}, function () {
        var setup, teardown, teardown2, code;
        return openerp.testing.Stack().push(function () {
            setup = true;
        }, function () {
            teardown = true;
        }).push(function () {
            return $.Deferred().reject("Fail!");
        }, function () {
            teardown2 = true;
        }).execute(function () {
            code = true;
            return 42;
        }).then(reject, function (m) {
            ok(setup, "should have executed first setup function");
            ok(teardown, "should have executed first teardown function");
            ok(!teardown2, "should not have executed second teardown function");
            strictEqual(m, "Fail!", "should return setup failure message");
            ok(!code, "should not have executed callback");
            return $.when();
        });
    });
    test('failed teardown', {asserts: 2}, function () {
        var teardowns = 0;
        return openerp.testing.Stack().push(null, function () {
            teardowns++;
            return $.Deferred().reject('Fail 1');
        }).push(null, function () {
            teardowns++;
        }).push(null, function () {
            teardowns++;
            return $.Deferred().reject('Fail 3');
        }).execute(function () {
            return 42;
        }).then(reject, function (m) {
            strictEqual(teardowns, 3,
                "should have tried executing all teardowns");
            strictEqual(m, "Fail 3", "should return first failure message");
                    return $.when();
        });
    });
    test('failed call + teardown', {asserts: 2}, function () {
        var teardowns = 0;
        return openerp.testing.Stack().push(null, function () {
            teardowns++;
        }).push(null, function () {
            teardowns++;
            return $.Deferred().reject('Fail 2');
        }).execute(function () {
            return $.Deferred().reject("code");
        }).then(reject, function (m) {
            strictEqual(teardowns, 2,
                "should have tried executing all teardowns");
            strictEqual(m, "code", "should return first failure message");
                    return $.when();
        });
    });

    test('arguments passing', {asserts: 9}, function () {
        var asserter = function (a, b, c) {
            strictEqual(a, 1);
            strictEqual(b, "foo");
            deepEqual(c, {bar: "baz", qux: 42});
        };

        return openerp.testing.Stack()
            .push(asserter, asserter)
            .execute(asserter, 1, "foo", {bar: 'baz', qux: 42});
    });
});
