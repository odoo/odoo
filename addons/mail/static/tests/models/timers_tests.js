odoo.define('mail.model.TimersTests', function (require) {
"use strict";

var Timer = require('mail.model.Timer');
var Timers = require('mail.model.Timers');

QUnit.module('mail', {}, function () {
QUnit.module('model', {}, function () {
QUnit.module('Timers');

QUnit.test('register timers', function (assert) {
    assert.expect(4);

    // patch Timer so that there are immediate
    this.ORIGINAL_TIMER_START = Timer.prototype.start;
    Timer.prototype.start = function () { this._onTimeout(); };

    var func = function () {
        assert.step('function_called');
        if (arguments.length) {
            var args = Array.prototype.slice.call(arguments, 0);
            assert.deepEqual(args, ['a', 'b'],
                "should have called the function with some arguments");
        }
    };
    var timers = new Timers({
        duration: 0,
        onTimeout: func,
    });

    timers.registerTimer({ timerID: 1 });
    timers.registerTimer({
        timerID: 2,
        timeoutCallbackArguments: ['a', 'b']
    });

    assert.verifySteps(['function_called', 'function_called'],
        "should have called the function twice");

    // unpatch Timer
    Timer.prototype.start = this.ORIGINAL_TIMER_START;
});

QUnit.test('register timers once per ID', function (assert) {
    var done = assert.async();
    assert.expect(2);

    var func = function () {
        assert.step('function_called');
    };
    var timers = new Timers({
        duration: 0,
        onTimeout: func,
    });

    timers.registerTimer({ timerID: 1 });
    timers.registerTimer({ timerID: 1 });

    // Called after timer(s) timeout
    setTimeout(function () {
        assert.verifySteps(['function_called'], "should have called the function once");
        done();
    }, 0);
});

QUnit.test('unregister timers', function (assert) {
    var done = assert.async();
    assert.expect(1);

    var func = function () {
        assert.step('function_called');
    };
    var timers = new Timers({
        duration: 0,
        onTimeout: func,
    });

    timers.registerTimer({ timerID: 1 });
    timers.unregisterTimer({ timerID: 1 });

    // Called after timer(s) timeout
    setTimeout(function () {
        assert.verifySteps([], "should not have called the function");
        done();
    }, 0);
});

});
});
});
