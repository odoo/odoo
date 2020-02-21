odoo.define('point_of_sale.test_popups', async function(require) {
    'use strict';

    const makeTestEnvironment = require('web.test_env');
    const testUtils = require('web.test_utils');
    const { ConfirmPopup } = require('point_of_sale.ConfirmPopup');
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { useState } = owl;
    const { xml } = owl.tags;

    QUnit.module('Test Pos Popups', {
        before() {
            class Root extends PosComponent {
                popup = useState({ isShow: false, name: null, component: null, props: {} });
                static template = xml`
                    <div t-on-show-popup="__showPopup">
                        <t t-if="popup.isShow" t-component="popup.component" t-props="popup.props" t-key="popup.name" />
                    </div>
                `;
            }
            Root.env = makeTestEnvironment();
            this.Root = Root;
        },
    });

    QUnit.test('ConfirmPopup', async function(assert) {
        assert.expect(6);
        this.Root.addComponents([ConfirmPopup]);

        const root = new this.Root();
        await root.mount(testUtils.prepareTarget());

        let promResponse, userResponse;

        // Step: show popup and confirm
        promResponse = root.showPopup('ConfirmPopup', {});
        await testUtils.nextTick();
        testUtils.dom.click(root.el.querySelector('.confirm'));
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, true);

        // Step: show popup then cancel
        promResponse = root.showPopup('ConfirmPopup', {});
        await testUtils.nextTick();
        testUtils.dom.click(root.el.querySelector('.cancel'));
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, false);

        // Step: check texts
        promResponse = root.showPopup('ConfirmPopup', {
            title: 'Are you sure?',
            body: 'Are you having fun?',
            confirmText: 'Hell Yeah!',
            cancelText: 'Are you kidding me?',
        });
        await testUtils.nextTick();
        assert.strictEqual(root.el.querySelector('.title').innerText.trim(), 'Are you sure?');
        assert.strictEqual(root.el.querySelector('.body').innerText.trim(), 'Are you having fun?');
        assert.strictEqual(root.el.querySelector('.confirm').innerText.trim(), 'Hell Yeah!');
        assert.strictEqual(
            root.el.querySelector('.cancel').innerText.trim(),
            'Are you kidding me?'
        );

        root.unmount();
        root.destroy();
    });
});
