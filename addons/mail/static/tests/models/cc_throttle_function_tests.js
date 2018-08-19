odoo.define('mail.model.CCThrottleFunctionTests', function (require) {
"use strict";

var CCThrottleFunction = require('mail.model.CCThrottleFunction');
var CCThrottleFunctionObject = require('mail.model.CCThrottleFunctionObject');

var testUtils = require('web.test_utils');

QUnit.module('mail', {
    beforeEach: function () {

        var self = this;
        this.timeoutCDDef = $.Deferred();

        this.patch = function () {
            self.ORIGINAL_CCTFO_ON_CD_TIMEOUT = CCThrottleFunctionObject.prototype._onCooldownTimeout;
            CCThrottleFunctionObject.prototype._onCooldownTimeout = function () {
                self.timeoutCDDef.then(self.ORIGINAL_CCTFO_ON_CD_TIMEOUT.apply(this, arguments));
            };
        };
        this.unpatch = function () {
            CCThrottleFunctionObject.prototype._onCooldownTimeout = self.ORIGINAL_CCTFO_ON_CD_TIMEOUT;
        };
        this.patch();
    },
    afterEach: function () {
        this.unpatch();
    },
}, function () {

QUnit.module('model', {}, function () {
QUnit.module('CC Throttle Function');

QUnit.test('cancel()', function (assert) {
    var done = assert.async();
    assert.expect(3);

    var self = this;
    var def = $.Deferred();
    var step = 1;

    var widget = testUtils.createParent({
        mockRPC: function (route, args) {
            if (args.method === '__rpc__') {
                assert.step(args.method + args.args[0]);

                if (step === 1) {
                    def.resolve();
                }
                else {
                    assert.notOk(true, "should not perform rpc more than once");
                }
                step++;

                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    var func = function () {
        widget._rpc({
            method: '__rpc__',
            args: arguments,
        });
    };

    var cctFunc = CCThrottleFunction({
        duration: 0,
        func: func,
    });

    cctFunc(1);

    def.then(function () {
        assert.verifySteps(['__rpc__1'], "function should have been called once");
    }).then(function () {
        cctFunc(2);
        cctFunc.cancel();
        self.timeoutCDDef.resolve();
    });
    this.timeoutCDDef.then(function () {
        assert.verifySteps(['__rpc__1'],
            "function should still have been called once after 2nd function call cancelled");
        widget.destroy();
        done();
    });
});

QUnit.test('clear()', function (assert) {
    var done = assert.async();
    assert.expect(5);

    var self = this;
    var def1 = $.Deferred();
    var def2 = $.Deferred();
    var step = 1;

    var widget = testUtils.createParent({
        mockRPC: function (route, args) {
            if (args.method === '__rpc__') {
                assert.step(args.method + args.args[0]);

                if (step === 1) {
                    def1.resolve();
                } else if (step === 2) {
                    def2.resolve();
                } else {
                    assert.notOk(true, "should not perform rpc more than twice");
                }
                step++;

                return $.when();
            }
            return this._super.apply(this, arguments);
        },
    });

    var func = function () {
        widget._rpc({
            method: '__rpc__',
            args: arguments,
        });
    };

    var cctFunc = CCThrottleFunction({
        duration: 1000*1000,
        func: func,
    });

    cctFunc(1);

    def1.then(function () {
        assert.verifySteps(['__rpc__1'], "function should have been called once");
    }).then(function () {
        cctFunc(2);
    }).then(function () {
        assert.verifySteps(['__rpc__1'],
            "function should still have been called once (due to long throttle)");
        cctFunc.clear();
        self.timeoutCDDef.resolve();
        def2.resolve();
    });
    $.when(self.timeoutCDDef, def2).then(function () {
        assert.verifySteps(['__rpc__1', '__rpc__2'],
            "function should have been called twice after 'clear' (buffered 2nd function call)");
        widget.destroy();
        done();
    });
});

});
});
});
