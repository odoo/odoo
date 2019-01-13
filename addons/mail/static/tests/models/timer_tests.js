odoo.define('mail.model.TimerTests', function (require) {
"use strict";

var Timer = require('mail.model.Timer');

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('Timer');

QUnit.test('start()', function (assert) {
    var done = assert.async();
    assert.expect(2);

    var def = $.Deferred();
    var func = function () {
        def.resolve();
    };
    var t = new Timer({
        duration: 0,
        onTimeout: func,
    });

    assert.verifySteps([], "should not have called the function");

    t.start();
    def.then(function () {
        assert.ok(true, "should have called the function");
        done();
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

QUnit.test('reset()', function (assert) {
    var done = assert.async();
    assert.expect(4);

    var def = $.Deferred();
    var func = function () {
        assert.step('function_called');
    };
    var t = new Timer({
        duration: 0,
        onTimeout: func,
    });

    t.start();

    // Called after 1st timer timeout
    setTimeout(function () {
        assert.verifySteps(['function_called'], "should have called the function once");
        t.reset();
        // Called after 2nd timer timeout
        setTimeout(function () {
            def.resolve();
        }, 0);
    }, 0);

    def.then(function () {
        assert.verifySteps(['function_called', 'function_called'],
            "should have called the function twice (2nd time from reset)");
        done();
    });
});

});
});
});
