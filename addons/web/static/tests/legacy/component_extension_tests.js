odoo.define('web.component_extension_tests', function (require) {
    "use strict";

    const makeTestEnvironment = require("web.test_env");
    const testUtils = require("web.test_utils");
    const { destroy, getFixture, mount } = require("@web/../tests/helpers/utils");
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { xml } = owl;
    const { useListener } = require("@web/core/utils/hooks");

    let target;
    QUnit.module("web", { beforeEach() { target = getFixture(); }}, function () {
        QUnit.module("Component Extension");

        QUnit.test("Component destroyed while performing successful RPC", async function (assert) {
            assert.expect(1);

            class Parent extends LegacyComponent {}
            Parent.template = xml`<div/>`;

            const env = makeTestEnvironment({}, () => Promise.resolve());

            const parent = await mount(Parent, target, { env });

            parent.rpc({}).then(() => { throw new Error(); });
            destroy(parent);

            await testUtils.nextTick();

            assert.ok(true, "Promise should still be pending");
        });

        QUnit.test("Component destroyed while performing failed RPC", async function (assert) {
            assert.expect(1);

            class Parent extends LegacyComponent {}
            Parent.template = xml`<div/>`;

            const env = makeTestEnvironment({}, () => Promise.reject());
            const parent = await mount(Parent, target, { env });

            parent.rpc({}).catch(() => { throw new Error(); });
            destroy(parent);

            await testUtils.nextTick();

            assert.ok(true, "Promise should still be pending");
        });

        QUnit.module("Custom Hooks");

        QUnit.test("useListener handler type", async function (assert) {
            assert.expect(1);

            class Parent extends LegacyComponent {
                setup() {
                    useListener('custom1', '_onCustom1');
                }
            }
            Parent.template = xml`<div/>`;
            const env = makeTestEnvironment({}, () => Promise.reject());

            try {
                await mount(Parent, target, { env })
            } catch (e) {
                assert.strictEqual(e.message, 'The handler must be a function');
            }
        });

        QUnit.test("useListener in inheritance setting", async function (assert) {
            assert.expect(12);
            const env = makeTestEnvironment({}, () => Promise.reject());

            class Parent extends LegacyComponent {
                setup() {
                    useListener('custom1', this._onCustom1);
                    useListener('custom2', this._onCustom2);
                }
                _onCustom1() {
                    assert.step(`${this.constructor.name} custom1`);
                }
                _onCustom2() {
                    assert.step('parent custom2');
                }
            }
            Parent.template = xml`<div/>`;

            class Child extends Parent {
                setup() {
                    super.setup();
                    useListener('custom2', this._onCustom2);
                    useListener('custom3', this._onCustom3);
                }
                _onCustom2() {
                    assert.step('overriden custom2');
                }
                _onCustom3() {
                    assert.step('child custom3');
                }
            }

            const parent = await mount(Parent, target, { env });
            const child = await mount(Child, target, { env });

            parent.trigger('custom1');
            assert.verifySteps(['Parent custom1']);
            parent.trigger('custom2');
            assert.verifySteps(['parent custom2']);
            parent.trigger('custom3');
            assert.verifySteps([]);

            child.trigger('custom1');
            assert.verifySteps(['Child custom1']);
            // There are two handlers for that one (Parent and Child)
            // Although the handler is overriden in Child
            child.trigger('custom2');
            assert.verifySteps(['overriden custom2', 'overriden custom2']);
            child.trigger('custom3');
            assert.verifySteps(['child custom3']);
        });

        QUnit.test("useListener with native JS selector", async function (assert) {
            assert.expect(3);

            class Parent extends LegacyComponent {
                setup() {
                    useListener('custom1', 'div .custom-class', this._onCustom1);
                }
                _onCustom1() {
                    assert.step(`custom1`);
                }
            }
            Parent.template = xml`
                <div>
                    <p>no trigger</p>
                    <h1 class="custom-class">triggers</h1>
                </div>
            `;

            const env = makeTestEnvironment({}, () => Promise.reject());
            const parent = await mount(Parent, target, { env });

            parent.el.querySelector('p').dispatchEvent(new Event('custom1', {bubbles: true}));
            assert.verifySteps([]);
            parent.el.querySelector('h1').dispatchEvent(new Event('custom1', {bubbles: true}));
            assert.verifySteps(['custom1']);
        });

        QUnit.test("useListener with native JS selector delegation", async function (assert) {
            assert.expect(3);

            class Parent extends LegacyComponent {
                setup() {
                    useListener('custom1', '.custom-class', this._onCustom1);
                }
                _onCustom1() {
                    assert.step(`custom1`);
                }
            }
            Parent.template = xml`
                <div>
                    <p>no trigger</p>
                    <h1 class="custom-class"><h2>triggers</h2></h1>
                </div>`;

            target.classList.add('custom-class');
            const env = makeTestEnvironment({}, () => Promise.reject());

            const parent = await mount(Parent, target, { env });

            parent.el.querySelector('p').dispatchEvent(new Event('custom1', {bubbles: true}));
            assert.verifySteps([]);
            parent.el.querySelector('h2').dispatchEvent(new Event('custom1', {bubbles: true}));
            assert.verifySteps(['custom1']);
            target.classList.remove('custom-class');
        });

        QUnit.test("useListener with capture option", async function (assert) {
            assert.expect(7);

            class Leaf extends LegacyComponent {
                setup() {
                    useListener('custom1', this._onCustom1);
                }
                _onCustom1() {
                    assert.step(`${this.constructor.name} custom1`);
                }
            }
            Leaf.template = xml`<div class="leaf"/>`;

            class Root extends LegacyComponent {
                setup() {
                    useListener('custom1', this._onCustom1, { capture: true });
                }
                _onCustom1(event) {
                    assert.step(`${this.constructor.name} custom1`);
                    const detail = event.detail;
                    if (detail && detail.stopMe) {
                        event.stopPropagation();
                    }
                }
            }
            Root.template = xml`<div class="root"><Leaf/></div>`;
            Root.components = { Leaf };

            await mount(Root, target);

            const rootNode = document.body.querySelector('.root');
            const leafNode = document.body.querySelector('.leaf');
            rootNode.dispatchEvent(new CustomEvent('custom1', {
                bubbles: true,
                cancelable: true
            }));
            assert.verifySteps(['Root custom1']);

            // Dispatch custom1 on the leaf element.
            // Since we listen in the capture phase, Root is first triggered.
            // The event is stopped there.
            leafNode.dispatchEvent(new CustomEvent('custom1', {
                bubbles: true,
                cancelable: true,
                detail: {
                    stopMe: true
                },
            }));
            assert.verifySteps(['Root custom1']);

            // Same as before, except this time we don't stop the event
            leafNode.dispatchEvent(new CustomEvent('custom1', {
                bubbles: true,
                cancelable: true,
                detail: {
                    stopMe: false
                }
            }));
            assert.verifySteps(['Root custom1', 'Leaf custom1']);
        });
    });
});
