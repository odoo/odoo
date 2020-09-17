odoo.define('web.systray_tests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');
    const SystrayMenu = require('web.SystrayMenu');
    const Widget = require('web.Widget');

    QUnit.test('Adding async components to the registry respects the sequence', async function (assert) {
        assert.expect(2);
        const prom = testUtils.makeTestPromise();

        const synchronousFirstWidget = Widget.extend({
            sequence: 3, // bigger sequence means more to the left
            start: function () {
                this.$el.addClass('first');
            }
        });
        const asynchronousSecondWidget = Widget.extend({
            sequence: 1, // smaller sequence means more to the right
            willStart: function () {
                return prom;
            },
            start: function () {
                this.$el.addClass('second');
            }
        });

        SystrayMenu.Items = [synchronousFirstWidget, asynchronousSecondWidget];
        const menu = new SystrayMenu();

        menu.mount($('#qunit-fixture')[0]);
        await testUtils.nextTick();
        prom.resolve();
        await testUtils.nextTick();

        assert.hasClass(menu.el.querySelectorAll('div')[0], 'first');
        assert.hasClass(menu.el.querySelectorAll('div')[1], 'second');

        menu.destroy();
    });
});
