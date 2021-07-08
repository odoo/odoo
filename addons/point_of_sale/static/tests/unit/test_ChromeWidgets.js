odoo.define('point_of_sale.tests.ChromeWidgets', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const PopupControllerMixin = require('point_of_sale.PopupControllerMixin');
    const testUtils = require('web.test_utils');
    const makePosTestEnv = require('point_of_sale.test_env');
    const { xml } = owl.tags;

    QUnit.module('unit tests for Chrome Widgets', {});

    QUnit.test('CashierName', async function (assert) {
        assert.expect(1);

        class Parent extends PosComponent {}
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div><CashierName></CashierName></div>
        `;
        Parent.env.pos.employee.name = 'Test Employee';

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());

        assert.strictEqual(parent.el.querySelector('span.username').innerText, 'Test Employee');

        parent.unmount();
        parent.destroy();
    });

    QUnit.test('SyncNotification', async function (assert) {
        assert.expect(5);

        class Parent extends PosComponent {}
        Parent.env = makePosTestEnv();
        Parent.template = xml/* html */ `
            <div>
                <SyncNotification></SyncNotification>
            </div>
        `;

        const pos = Parent.env.pos;
        pos.set('synch', { status: 'connected', pending: false });

        const parent = new Parent();
        await parent.mount(testUtils.prepareTarget());
        assert.ok(parent.el.querySelector('i.fa').parentElement.classList.contains('js_connected'));

        pos.set('synch', { status: 'connecting', pending: false });
        await testUtils.nextTick();
        assert.ok(parent.el.querySelector('i.fa').parentElement.classList.contains('js_connecting'));

        pos.set('synch', { status: 'disconnected', pending: false });
        await testUtils.nextTick();
        assert.ok(parent.el.querySelector('i.fa').parentElement.classList.contains('js_disconnected'));

        pos.set('synch', { status: 'error', pending: false });
        await testUtils.nextTick();
        assert.ok(parent.el.querySelector('i.fa').parentElement.classList.contains('js_error'));

        pos.set('synch', { status: 'error', pending: 10 });
        await testUtils.nextTick();
        assert.ok(parent.el.querySelector('.js_msg').innerText.includes('10'));

        parent.unmount();
        parent.destroy();
    });
});
