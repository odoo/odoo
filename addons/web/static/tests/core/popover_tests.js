odoo.define('web.popover_tests', function (require) {
    'use strict';

    const makeTestEnvironment = require('web.test_env');
    const Popover = require('web.Popover');
    const testUtils = require('web.test_utils');

    const { Component, tags, hooks } = owl;
    const { useRef, useState } = hooks;
    const { xml } = tags;

    QUnit.module('core', {}, function () {
        QUnit.module('Popover');

        QUnit.test('Basic rendering & props', async function (assert) {
            assert.expect(11);

            class SubComponent extends Component {}
            SubComponent.template = xml`
                <div class="o_subcomponent" style="width: 280px;" t-esc="props.text"/>
            `;

            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.state = useState({
                        position: 'right',
                        title: '👋',
                        textContent: 'sup',
                    });
                    this.popoverRef = useRef('popoverRef');
                }
            }
            // Popover should be included as a globally available Component
            Parent.components = { SubComponent };
            Parent.env = makeTestEnvironment();
            Parent.template = xml`
                <div>
                    <button id="passiveTarget">🚫</button>
                    <Popover t-ref="popoverRef"
                        position="state.position"
                        title="state.title"
                        >
                        <t t-set="opened">
                            <SubComponent text="state.textContent"/>
                        </t>
                        <button id="target">
                            Notice me, senpai 👀
                        </button>
                    </Popover>
                </div>`;

            const parent = new Parent();
            const fixture = testUtils.prepareTarget();
            /**
             * The component being tested behaves differently based on its
             * visibility (or not) in the viewport. The qunit fixture has to be
             * in the view port for these tests to be meaningful.
             */
            fixture.style.top = '300px';
            fixture.style.left = '150px';
            fixture.style.width = '300px';

            // Helper functions
            async function changeProps(key, value) {
                parent.state[key] = value;
                await testUtils.nextTick();
            }
            function pointsTo(popover, element, position) {
                const hasCorrectClass = popover.classList.contains(
                    `o_popover--${position}`
                );
                const expectedPosition = Popover.computePositioningData(
                    popover,
                    element
                )[position];
                const correctLeft =
                    parseFloat(popover.style.left) ===
                    Math.round(expectedPosition.left * 100) / 100;
                const correctTop =
                    parseFloat(popover.style.top) ===
                    Math.round(expectedPosition.top * 100) / 100;
                return hasCorrectClass && correctLeft && correctTop;
            }

            await parent.mount(fixture);
            const body = document.querySelector('body');
            let popover, title;
            // Show/hide
            assert.containsNone(body, '.o_popover');
            await testUtils.dom.click('#target');
            assert.containsOnce(body, '.o_popover');
            assert.containsOnce(body, '.o_subcomponent');
            assert.containsOnce(body, '.o_popover--right');
            await testUtils.dom.click('#passiveTarget');
            assert.containsNone(body, '.o_popover');
            // Reactivity of title
            await testUtils.dom.click('#target');
            popover = document.querySelector('.o_popover');
            title = popover.querySelector('.o_popover_header').innerText.trim();
            assert.strictEqual(title, '👋');
            await changeProps('title', '🤔');
            title = popover.querySelector('.o_popover_header').innerText.trim();
            assert.strictEqual(
                title,
                '🤔',
                'The title of the popover should have changed.'
            );
            // Position and target reactivity
            const element = parent.popoverRef.el;
            assert.ok(
                pointsTo(
                    document.querySelector('.o_popover'),
                    element,
                    parent.state.position
                ),
                'Popover should be visually aligned with its target'
            );
            await changeProps('position', 'bottom');
            assert.ok(
                pointsTo(
                    document.querySelector('.o_popover'),
                    element,
                    parent.state.position
                ),
                'Popover should be bottomed positioned'
            );
            // Reactivity of subcomponents
            await changeProps('textContent', 'wassup');
            assert.strictEqual(
                popover.querySelector('.o_subcomponent').innerText.trim(),
                'wassup',
                'Subcomponent should match with its given text'
            );
            await testUtils.dom.click('#passiveTarget');
            // Requested position not fitting
            await changeProps('position', 'left');
            await testUtils.dom.click('#target');
            assert.ok(
                pointsTo(document.querySelector('.o_popover'), element, 'right'),
                "Popover should be right-positioned because it doesn't fit left"
            );
            await testUtils.dom.click('#passiveTarget');
            parent.destroy();
        });

        QUnit.test('Multiple popovers', async function (assert) {
            assert.expect(9);

            class Parent extends Component {}
            Parent.components = { Popover };
            Parent.env = makeTestEnvironment();
            Parent.template = xml`
                <div>
                    <Popover>
                        <button id="firstTarget">👋</button>
                        <t t-set="opened">
                            <p id="firstContent">first popover</p>
                        </t>
                    </Popover>
                    <br/>
                    <Popover>
                        <button id="secondTarget">👏</button>
                        <t t-set="opened">
                            <p id="secondContent">second popover</p>
                        </t>
                    </Popover>
                    <br/>
                    <span id="dismissPopovers">💀</span>
                </div>`;

            const parent = new Parent();
            const fixture = testUtils.prepareTarget();

            const body = document.querySelector('body');
            await parent.mount(fixture);
            // Show first popover
            assert.containsNone(body, '.o_popover');
            await testUtils.dom.click('#firstTarget');
            assert.containsOnce(body, '#firstContent');
            assert.containsNone(body, '#secondContent');
            await testUtils.dom.click('#dismissPopovers');
            assert.containsNone(body, '.o_popover');
            // Show first then display second
            await testUtils.dom.click('#firstTarget');
            assert.containsOnce(body, '#firstContent');
            assert.containsNone(body, '#secondContent');
            await testUtils.dom.click('#secondTarget');
            assert.containsNone(body, '#firstContent');
            assert.containsOnce(body, '#secondContent');
            await testUtils.dom.click('#dismissPopovers');
            assert.containsNone(body, '.o_popover');
            parent.destroy();
        });

        QUnit.test('toggle', async function (assert) {
            assert.expect(4);

            class Parent extends Component {}
            // Popover should be included as a globally available Component
            Object.assign(Parent, {
                env: makeTestEnvironment(),
                template: xml`
                    <div>
                        <Popover>
                            <button id="open">Open</button>
                            <t t-set="opened">
                                Opened!
                            </t>
                        </Popover>
                    </div>
                `,
            });

            const parent = new Parent();
            const fixture = testUtils.prepareTarget();
            await parent.mount(fixture);

            const body = document.querySelector('body');
            assert.containsOnce(body, '#open');
            assert.containsNone(body, '.o_popover');

            await testUtils.dom.click('#open');
            assert.containsOnce(body, '.o_popover');

            await testUtils.dom.click('#open');
            assert.containsNone(body, '.o_popover');

            parent.destroy();
        });

        QUnit.test('close event', async function (assert) {
            assert.expect(7);

            // Needed to trigger the event from inside the Popover slot.
            class Content extends Component {}
            Content.template = xml`
                <button id="close" t-on-click="trigger('o-popover-close')">
                    Close
                </button>
            `;

            class Parent extends Component {}
            // Popover should be included as a globally available Component
            Object.assign(Parent, {
                components: { Content },
                env: makeTestEnvironment(),
                template: xml`
                    <div>
                        <Popover>
                            <button id="open">Open</button>
                            <t t-set="opened">
                                <Content/>
                            </t>
                        </Popover>
                    </div>
                `,
            });

            const parent = new Parent();
            const fixture = testUtils.prepareTarget();
            await parent.mount(fixture);

            const body = document.querySelector('body');
            assert.containsOnce(body, '#open');
            assert.containsNone(body, '.o_popover');
            assert.containsNone(body, '#close');

            await testUtils.dom.click('#open');
            assert.containsOnce(body, '.o_popover');
            assert.containsOnce(body, '#close');

            await testUtils.dom.click('#close');
            assert.containsNone(body, '.o_popover');
            assert.containsNone(body, '#close');

            parent.destroy();
        });
    });
});
