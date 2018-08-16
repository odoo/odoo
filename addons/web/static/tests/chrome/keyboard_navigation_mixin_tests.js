odoo.define('web.keyboard_navigation_mixin_tests', function (require) {
"use strict";

var KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
var Widget = require('web.Widget');

QUnit.module('KeyboardNavigationMixin', function () {
    QUnit.test('aria-keyshortcuts is added on elements with accesskey', function (assert) {
        assert.expect(1);
        var $target = $('#qunit-fixture');
        var KeyboardWidget = Widget.extend(KeyboardNavigationMixin, {
            start: function () {
                var $button = $('<button>').text('Click Me!').attr('accesskey', 'o');
                // we need to define the accesskey because it will not be assigned on invisible buttons
                this.$el.append($button);
                return this._super.apply(this, arguments);
            },
        });
        var w = new KeyboardWidget();
        w.appendTo($target);

        // minimum set of attribute to generate a native event that works with the mixin
        var e = new Event("keydown");
        e.key = '';
        e.altKey = true;
        w.$el[0].dispatchEvent(e);

        assert.ok(w.$el.find('button[aria-keyshortcuts]')[0], 'the aria-keyshortcuts is set on the button');
    });
});
});
