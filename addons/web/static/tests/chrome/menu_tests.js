odoo.define('web.menu_tests', function (require) {
    "use strict";

    const testUtils = require('web.test_utils');
    const Menu = require('web.Menu');
    const SystrayMenu = require('web.SystrayMenu');
    const Widget = require('web.Widget');


    QUnit.module('chrome', {}, function () {
        QUnit.module('Menu');

        QUnit.test('Systray on_attach_callback is called', async function (assert) {
            assert.expect(4);

            const parent = await testUtils.createParent({});

            // Add some widgets to the systray
            const Widget1 = Widget.extend({
                on_attach_callback: () => assert.step('on_attach_callback widget1')
            });
            const Widget2 = Widget.extend({
                on_attach_callback: () => assert.step('on_attach_callback widget2')
            });
            SystrayMenu.Items = [Widget1, Widget2];

            testUtils.mock.patch(SystrayMenu, {
                on_attach_callback: function () {
                    assert.step('on_attach_callback systray');
                    this._super(...arguments);
                }
            });

            const menu = new Menu(parent, {children: []});
            await menu.appendTo($('#qunit-fixture'));

            assert.verifySteps([
                'on_attach_callback systray',
                'on_attach_callback widget1',
                'on_attach_callback widget2',
            ]);
            testUtils.mock.unpatch(SystrayMenu);
            parent.destroy();
        });
    });

});
