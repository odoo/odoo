odoo.define('mail.model.TimerTests', function (require) {
"use strict";

var testUtils = require("web.test_utils");
var Timer = require('mail.model.Timer');

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('Timer');

QUnit.test('start()', async function (assert) {
    assert.expect(2);

    var prom = testUtils.makeTestPromise();
    var t = new Timer({
        duration: 0,
        onTimeout: prom.resolve,
    });

    assert.verifySteps([], "should not have called the function");

    t.start();
    await prom.then(function () {
        assert.ok(true, "should have called the function");
    });
});

QUnit.test('clear()', function (assert) {
    var done = assert.async();
    assert.expect(1);

    var func = function () {
        assert.step('function_called');
    };
    var t = new Timer({
        duration: 0,
        onTimeout: func,
    });

    t.start();
    t.clear();

    // Called after timer timeout
    setTimeout(function () {
        assert.verifySteps([], "should not have called the function");
        done();
    }, 0);
});

QUnit.test('reset()', async function (assert) {
    assert.expect(4);

    var prom = testUtils.makeTestPromise();
    var func = function () {
        assert.step('function_called');
    };
    var t = new Timer({
        duration: 0,
        onTimeout: func,
    });

    t.start();

    // Called after 1st timer timeout
    await testUtils.nextTick();
    assert.verifySteps(['function_called'], "should have called the function once");
    t.reset();
    // Called after 2nd timer timeout
    setTimeout(function () {
        prom.resolve();
    }, 0);

    await prom.then(function () {
        assert.verifySteps(['function_called'],
            "should have called the function twice (2nd time from reset)");
    });
});

});
});
});
