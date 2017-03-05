odoo.define('web.pager_tests', function (require) {
"use strict";

var Pager = require('web.Pager');

QUnit.module('chrome', {}, function () {

    QUnit.module('Pager');

    QUnit.test('basic stuff', function(assert) {
        assert.expect(1);

        var pager = new Pager(null, 10, 1, 4);
        pager.appendTo($("<div>"));
        assert.strictEqual(pager.state.current_min, 1, "current_min should be set to 1");
    });
});

});