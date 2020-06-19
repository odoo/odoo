odoo.define('web.systray_tests', function (require) {
    "use strict";

    var testUtils = require('web.test_utils');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    QUnit.test('Adding async components to the registry respects the sequence', async function (assert) {
        assert.expect(2);
        var parent = await testUtils.createParent({});
        var prom = testUtils.makeTestPromise();

        var synchronousFirstWidget = Widget.extend({
            sequence: 3, // bigger sequence means more to the left
            start: function () {
                this.$el.addClass('first');
            }
        });
        var asynchronousSecondWidget = Widget.extend({
            sequence: 1, // smaller sequence means more to the right
            willStart: function () {
                return prom;
            },
            start: function () {
                this.$el.addClass('second');
            }
        });

        SystrayMenu.Items = [synchronousFirstWidget, asynchronousSecondWidget];
        var menu = new SystrayMenu(parent);

        menu.appendTo($('#qunit-fixture'));
        await testUtils.nextTick();
        prom.resolve();
        await testUtils.nextTick();

        assert.hasClass(menu.$('div:eq(0)'), 'first');
        assert.hasClass(menu.$('div:eq(1)'), 'second');

        parent.destroy();
    })
});
