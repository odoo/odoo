odoo.define('web.keyboard_navigation_mixin_tests', function (require) {
"use strict";

var KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

QUnit.module('KeyboardNavigationMixin', function () {
    QUnit.test('aria-keyshortcuts is added on elements with accesskey', async function (assert) {
        assert.expect(1);
        var $target = $('#qunit-fixture');
        var KeyboardWidget = Widget.extend(KeyboardNavigationMixin, {
            init: function () {
                this._super.apply(this, arguments);
                KeyboardNavigationMixin.init.call(this);
            },
            start: function () {
                var $button = $('<button>').text('Click Me!').attr('accesskey', 'o');
                // we need to define the accesskey because it will not be assigned on invisible buttons
                this.$el.append($button);
                return this._super.apply(this, arguments);
            },
        });
        var parent = testUtils.createParent({});
        var w = new KeyboardWidget(parent);
        await w.appendTo($target);

        // minimum set of attribute to generate a native event that works with the mixin
        var e = new Event("keydown");
        e.key = '';
        e.altKey = true;
        w.$el[0].dispatchEvent(e);

        assert.ok(w.$el.find('button[aria-keyshortcuts]')[0], 'the aria-keyshortcuts is set on the button');

        parent.destroy();
    });

    QUnit.test('keep CSS position absolute for parent of overlay', async function (assert) {
        // If we change the CSS position of an 'absolute' element to 'relative',
        // we may likely change its position on the document. Since the overlay
        // CSS position is 'absolute', it will match the size and cover the
        // parent with 'absolute' > 'absolute', without altering the position
        // of the parent on the document.
        assert.expect(1);
        var $target = $('#qunit-fixture');
        var $button;
        var KeyboardWidget = Widget.extend(KeyboardNavigationMixin, {
            init: function () {
                this._super.apply(this, arguments);
                KeyboardNavigationMixin.init.call(this);
            },
            start: function () {
                $button = $('<button>').text('Click Me!').attr('accesskey', 'o');
                // we need to define the accesskey because it will not be assigned on invisible buttons
                this.$el.append($button);
                return this._super.apply(this, arguments);
            },
        });
        var parent = testUtils.createParent({});
        var w = new KeyboardWidget(parent);
        await w.appendTo($target);

        $button.css('position', 'absolute');

        // minimum set of attribute to generate a native event that works with the mixin
        var e = new Event("keydown");
        e.key = '';
        e.altKey = true;
        w.$el[0].dispatchEvent(e);

        assert.strictEqual($button.css('position'), 'absolute',
            "should not have kept the CSS position of the button");

        parent.destroy();
    });
});
});
