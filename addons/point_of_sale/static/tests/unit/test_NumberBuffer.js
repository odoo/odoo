odoo.define('point_of_sale.tests.NumberBuffer', function(require) {
    'use strict';

    const { Component, useState } = owl;
    const { xml } = owl.tags;
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const makeTestEnvironment = require('web.test_env');
    const testUtils = require('web.test_utils');

    QUnit.module('unit tests for NumberBuffer', {
        before() {},
    });

    QUnit.test('simple fast inputs with capture in between', async function(assert) {
        assert.expect(3);

        class Root extends Component {
            constructor() {
                super();
                this.state = useState({ buffer: '' });
                NumberBuffer.activate();
                NumberBuffer.use({
                    nonKeyboardInputEvent: 'numpad-click-input',
                    state: this.state,
                });
            }
            resetBuffer() {
                NumberBuffer.capture();
                NumberBuffer.reset();
            }
        }
        Root.env = makeTestEnvironment();
        Root.template = xml/* html */ `
            <div>
                <p><t t-esc="state.buffer" /></p>
                <button class="one" t-on-click="trigger('numpad-click-input', { key: '1' })">1</button>
                <button class="two" t-on-click="trigger('numpad-click-input', { key: '2' })">2</button>
                <button class="reset" t-on-click="resetBuffer">reset</button>
            </div>
        `;

        const root = new Root();
        await root.mount(testUtils.prepareTarget());

        const oneButton = root.el.querySelector('button.one');
        const twoButton = root.el.querySelector('button.two');
        const resetButton = root.el.querySelector('button.reset');
        const bufferEl = root.el.querySelector('p');

        testUtils.dom.click(oneButton);
        testUtils.dom.click(twoButton);
        await testUtils.nextTick();
        assert.strictEqual(bufferEl.textContent, '12');
        testUtils.dom.click(resetButton);
        await testUtils.nextTick();
        assert.strictEqual(bufferEl.textContent, '');
        testUtils.dom.click(twoButton);
        testUtils.dom.click(oneButton);
        await testUtils.nextTick();
        assert.strictEqual(bufferEl.textContent, '21');

        root.unmount();
        root.destroy();
    });
});
