odoo.define('web.popover_tests', function (require) {
    'use strict';

    const makeTestEnvironment = require('web.test_env');
    const Popover = require('web.Popover');
    const testUtils = require('web.test_utils');
    const { click, mount } = require("@web/../tests/helpers/utils");
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { useState, xml } = owl;

    QUnit.module('core', {}, function () {
        QUnit.module('Popover');

        QUnit.test('Basic rendering & props', async function (assert) {
            assert.expect(11);

            class SubComponent extends LegacyComponent {}
            SubComponent.template = xml`
                <div class="o_subcomponent" style="width: 280px;" t-esc="props.text"/>
            `;

            class Parent extends LegacyComponent {
                constructor() {
                    super(...arguments);
                    this.state = useState({
                        position: 'right',
                        title: '👋',
                        textContent: 'sup',
                    });
                }
            }
            Parent.components = { Popover, SubComponent };
            Parent.template = xml`
                <div>
                    <button id="passiveTarget">🚫</button>
                    <Popover
                        position="state.position"
                        title="state.title"
                        >
                        <t t-set-slot="opened">
                            <SubComponent text="state.textContent"/>
                        </t>
                        <button id="target">
                            Notice me, senpai 👀
                        </button>
                    </Popover>
                </div>`;

            const target = testUtils.prepareTarget();
            const env = makeTestEnvironment();

            /**
             * The component being tested behaves differently based on its
             * visibility (or not) in the viewport. The qunit target has to be
             * in the view port for these tests to be meaningful.
             */
            target.style.top = '300px';
            target.style.left = '150px';
            target.style.width = '300px';

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

            const parent = await mount(Parent, target, { env });
            const body = document.querySelector('body');
            let popover, title;
            // Show/hide
            assert.containsNone(body, '.o_popover');
            await click(body, '#target');
            assert.containsOnce(body, '.o_popover');
            assert.containsOnce(body, '.o_subcomponent');
            assert.containsOnce(body, '.o_popover--right');
            await click(body, '#passiveTarget');
            assert.containsNone(body, '.o_popover');
            // Reactivity of title
            await click(body, '#target');
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
            const element = document.getElementById("passiveTarget").nextSibling;
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
            await click(body, '#passiveTarget');
            // Requested position not fitting
            await changeProps('position', 'left');
            await click(body, '#target');
            assert.ok(
                pointsTo(document.querySelector('.o_popover'), element, 'right'),
                "Popover should be right-positioned because it doesn't fit left"
            );
            await click(body, '#passiveTarget');
        });

        QUnit.test('Multiple popovers', async function (assert) {
            assert.expect(9);

            class Parent extends LegacyComponent {}
            Parent.components = { Popover };
            Parent.template = xml`
                <div>
                    <Popover>
                        <button id="firstTarget">👋</button>
                        <t t-set-slot="opened">
                            <p id="firstContent">first popover</p>
                        </t>
                    </Popover>
                    <br/>
                    <Popover>
                        <button id="secondTarget">👏</button>
                        <t t-set-slot="opened">
                            <p id="secondContent">second popover</p>
                        </t>
                    </Popover>
                    <br/>
                    <span id="dismissPopovers">💀</span>
                </div>`;

            const target = testUtils.prepareTarget();
            const env = makeTestEnvironment();

            const body = document.querySelector('body');

            await mount(Parent, target, { env });
            // Show first popover
            assert.containsNone(body, '.o_popover');
            await click(body, '#firstTarget');
            assert.containsOnce(body, '#firstContent');
            assert.containsNone(body, '#secondContent');
            await click(body, '#dismissPopovers');
            assert.containsNone(body, '.o_popover');
            // Show first then display second
            await click(body, '#firstTarget');
            assert.containsOnce(body, '#firstContent');
            assert.containsNone(body, '#secondContent');
            await click(body, '#secondTarget');
            assert.containsNone(body, '#firstContent');
            assert.containsOnce(body, '#secondContent');
            await click(body, '#dismissPopovers');
            assert.containsNone(body, '.o_popover');
        });

        QUnit.test('toggle', async function (assert) {
            assert.expect(4);

            class Parent extends LegacyComponent {}
            Parent.template = xml`
                <div>
                    <Popover>
                        <button id="open">Open</button>
                        <t t-set-slot="opened">
                            Opened!
                        </t>
                    </Popover>
                </div>
            `;
            Parent.components = { Popover };

            const target = testUtils.prepareTarget();
            const env = makeTestEnvironment();

            await mount(Parent, target, { env });

            const body = document.querySelector('body');
            assert.containsOnce(body, '#open');
            assert.containsNone(body, '.o_popover');

            await click(body, '#open');
            assert.containsOnce(body, '.o_popover');

            await click(body, '#open');
            assert.containsNone(body, '.o_popover');
        });

        QUnit.test('close event', async function (assert) {
            assert.expect(7);

            // Needed to trigger the event from inside the Popover slot.
            class Content extends LegacyComponent {
                onClick() {
                    this.trigger("o-popover-close");
                }
            }
            Content.template = xml`
                <button id="close" t-on-click="onClick">
                    Close
                </button>
            `;

            class Parent extends LegacyComponent {}
            Parent.components = { Content, Popover };
            Parent.template = xml`
                <div>
                    <Popover>
                        <button id="open">Open</button>
                        <t t-set-slot="opened">
                            <Content/>
                        </t>
                    </Popover>
                </div>
            `;

            const target = testUtils.prepareTarget();
            const env = makeTestEnvironment();

            await mount(Parent, target, { env });

            const body = document.querySelector('body');
            assert.containsOnce(body, '#open');
            assert.containsNone(body, '.o_popover');
            assert.containsNone(body, '#close');

            await click(body, '#open');
            assert.containsOnce(body, '.o_popover');
            assert.containsOnce(body, '#close');

            await click(body, '#close');
            assert.containsNone(body, '.o_popover');
            assert.containsNone(body, '#close');
        });
    });
});
