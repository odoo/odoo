odoo.define('web.menu_tests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');
    const Menu = require('web.Menu');
    const SystrayMenu = require('web.SystrayMenu');
    const Widget = require('web.Widget');


    QUnit.module('chrome', {}, function () {
        QUnit.module('Menu');

        QUnit.test('Systray on_attach_callback is called', async function (assert) {
            assert.expect(3);

            const parent = await testUtils.createParent({});

            // Add some widgets to the systray
            const Widget1 = Widget.extend({
                on_attach_callback: () => assert.step('on_attach_callback widget1')
            });
            const Widget2 = Widget.extend({
                on_attach_callback: () => assert.step('on_attach_callback widget2')
            });
            SystrayMenu.Items = [Widget1, Widget2];

            const menu = new Menu(parent, {children: []});
            await menu.appendTo($('#qunit-fixture'));

            // on_attach_callback is called on reverse order(due to mounted call)
            assert.verifySteps([
                'on_attach_callback widget2',
                'on_attach_callback widget1',
            ]);

            parent.destroy();
        });
    });

});
