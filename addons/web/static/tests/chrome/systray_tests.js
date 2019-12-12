odoo.define('web.systray_tests', function (require) {
    "use strict";

    const SystrayMenu = require('web.SystrayMenu');
    const testUtils = require('web.test_utils');
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

        const systray = new SystrayMenu();
        systray.mount(document.querySelector('#qunit-fixture'));
        await testUtils.nextTick();
        prom.resolve();
        await testUtils.nextTick();

        const items = systray.el.querySelectorAll('div');
        assert.hasClass(items[0], 'first');
        assert.hasClass(items[1], 'second');

        systray.destroy();
    });
});
