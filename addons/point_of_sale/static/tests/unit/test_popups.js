odoo.define('point_of_sale.test_popups', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const testUtils = require('web.test_utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const PopupControllerMixin = require('point_of_sale.PopupControllerMixin');
    const makePosTestEnv = require('point_of_sale.test_env');
    const { xml } = owl.tags;

    QUnit.module('unit tests for Popups', {
        before() {
            class Root extends PopupControllerMixin(PosComponent) { }
            Root.template = xml`
                    <div>
                        <t t-if="popup.isShown" t-component="popup.component" t-props="popupProps" t-key="popup.name" />
                    </div>
                `;
            Root.env = makePosTestEnv();
            this.Root = Root;
            Registries.Component.freeze();
        },
    });

    QUnit.test('ConfirmPopup', async function(assert) {
        assert.expect(6);

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

    QUnit.test('NumberPopup', async function(assert) {
        assert.expect(8);

        const root = new this.Root();
        await root.mount(testUtils.prepareTarget());

        let promResponse, userResponse;

        // Step: show NumberPopup and confirm with empty buffer
        promResponse = root.showPopup('NumberPopup', { startingValue: 1 });
        await testUtils.nextTick();
        testUtils.dom.triggerEvent(root.el.querySelector('.confirm'), 'mousedown');
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, true);
        assert.strictEqual(userResponse.payload, "1");

        // Step: show NumberPopup and cancel
        promResponse = root.showPopup('NumberPopup', {});
        await testUtils.nextTick();
        testUtils.dom.triggerEvent(root.el.querySelector('.cancel'), 'mousedown');
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, false);

        // Step: show NumberPopup and confirm with filled buffer, new title, new text
        promResponse = root.showPopup('NumberPopup', {
            title: 'Are you sure?',
            confirmText: 'Hell Yeah!',
            cancelText: 'Are you kidding me?',
        });
        await testUtils.nextTick();
        let nodes = Array.from(root.el.querySelectorAll('button'));
        testUtils.dom.triggerEvent(nodes.find(elem => elem.innerHTML === "7"), 'mousedown');
        await testUtils.nextTick();
        testUtils.dom.triggerEvent(nodes.find(elem => elem.innerHTML === "+10"), 'mousedown');
        await testUtils.nextTick();
        assert.strictEqual(root.el.querySelector('.title').innerText.trim(), 'Are you sure?');
        assert.strictEqual(root.el.querySelector('.confirm').innerText.trim(), 'Hell Yeah!');
        assert.strictEqual(root.el.querySelector('.cancel').innerText.trim(), 'Are you kidding me?');
        testUtils.dom.triggerEvent(root.el.querySelector('.confirm'), 'mousedown');
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, true);
        assert.strictEqual(userResponse.payload, "17");

        root.unmount();
        root.destroy();
    });

    QUnit.test('EditListPopup', async function(assert) {
        assert.expect(7);

        const root = new this.Root();
        await root.mount(testUtils.prepareTarget());

        let promResponse, userResponse;

        // Step: show popup and confirm
        promResponse = root.showPopup('EditListPopup', {});
        await testUtils.nextTick();
        testUtils.dom.click(root.el.querySelector('.confirm'));
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, true);
        assert.strictEqual(JSON.stringify(userResponse.payload.newArray), JSON.stringify([]));

        // Step: show popup and cancel
        promResponse = root.showPopup('EditListPopup', {});
        await testUtils.nextTick();
        testUtils.dom.click(root.el.querySelector('.cancel'));
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, false);

        // Step: show popup and confirm with a default array
        let defaultArray = ["Banana", "Cherry"];
        promResponse = root.showPopup('EditListPopup', {
                title: "Fruits",
                isSingleItem: false,
                array: defaultArray,
            });
        await testUtils.nextTick();
        testUtils.dom.click(root.el.querySelector('.confirm'));
        await testUtils.nextTick();
        userResponse = await promResponse;

        assert.strictEqual(userResponse.confirmed, true);
        let i = 0;
        defaultArray = defaultArray.map((item) => Object.assign({}, { _id: i++ }, { 'text': item}));
        assert.strictEqual(JSON.stringify(userResponse.payload.newArray), JSON.stringify(defaultArray));

        // Step: show popup and confirm with a new array
        promResponse = root.showPopup('EditListPopup', {
                title: "Fruits",
                isSingleItem: false,
                array: ["Banana", "Cherry"],
            });
        await testUtils.nextTick();
        testUtils.dom.click(root.el.querySelector('.fa-trash-o'));
        await testUtils.nextTick();
        testUtils.dom.click(root.el.querySelector('.confirm'));
        await testUtils.nextTick();
        userResponse = await promResponse;
        assert.strictEqual(userResponse.confirmed, true);
        assert.strictEqual(JSON.stringify(userResponse.payload.newArray), JSON.stringify([{ _id: 1, text: "Cherry"}]));

        root.unmount();
        root.destroy();
    });
});
