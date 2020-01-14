odoo.define('web.OwlCompatibilityTests', function (require) {
    "use strict";

    const { ComponentAdapter } = require('web.OwlCompatibility');
    const testUtils = require('web.test_utils');
    const Widget = require('web.Widget');

    const getMockedOwlEnv = testUtils.mock.getMockedOwlEnv;
    const makeTestPromise = testUtils.makeTestPromise;
    const nextTick = testUtils.nextTick;

    const { Component, tags, useState } = owl;
    const { xml } = tags;

    QUnit.module("Owl Compatibility", function () {
        QUnit.module("ComponentAdapter");

        QUnit.test("sub widget with no argument", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                start: function () {
                    this.$el.text('Hello World!');
                }
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');

            parent.destroy();
        });

        QUnit.test("sub widget with one argument", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                init: function (parent, name) {
                    this._super.apply(this, arguments);
                    this.name = name;
                },
                start: function () {
                    this.$el.text(`Hello ${this.name}!`);
                }
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget" name="'World'"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');

            parent.destroy();
        });

        QUnit.test("sub widget with several arguments (common Adapter)", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                init: function (parent, a1, a2) {
                    this._super.apply(this, arguments);
                    this.a1 = a1;
                    this.a2 = a2;
                },
                start: function () {
                    this.$el.text(`${this.a1} ${this.a2}!`);
                }
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget" a1="'Hello'" a2="'World'"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            try {
                await parent.mount(target);
            } catch (e) {
                assert.strictEqual(e.toString(),
                    `Error: ComponentAdapter has more than 1 argument, 'widgetArgs' must be overriden.`);
            }

            parent.destroy();
        });

        QUnit.test("sub widget with several arguments (specific Adapter)", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                init: function (parent, a1, a2) {
                    this._super.apply(this, arguments);
                    this.a1 = a1;
                    this.a2 = a2;
                },
                start: function () {
                    this.$el.text(`${this.a1} ${this.a2}!`);
                }
            });
            class MyWidgetAdapter extends ComponentAdapter {
                get widgetArgs() {
                    return [this.props.a1, this.props.a2];
                }
            }
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.template = xml`
                <div>
                    <MyWidgetAdapter Component="MyWidget" a1="'Hello'" a2="'World'"/>
                </div>`;
            Parent.components = { MyWidgetAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');

            parent.destroy();
        });

        QUnit.test("sub widget and widgetArgs props", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                init: function (parent, a1, a2) {
                    this._super.apply(this, arguments);
                    this.a1 = a1;
                    this.a2 = a2;
                },
                start: function () {
                    this.$el.text(`${this.a1} ${this.a2}!`);
                }
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget" a1="'Hello'" a2="'World'" widgetArgs="['Hello', 'World']"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');

            parent.destroy();
        });

        QUnit.test("sub widget is updated when props change", async function (assert) {
            assert.expect(2);

            const MyWidget = Widget.extend({
                init: function (parent, name) {
                    this._super.apply(this, arguments);
                    this.name = name;
                },
                start: function () {
                    this.render();
                },
                render: function () {
                    this.$el.text(`Hello ${this.name}!`);
                },
                update: function (name) {
                    this.name = name;
                },
            });
            class MyWidgetAdapter extends ComponentAdapter {
                update(nextProps) {
                    return this.widget.update(nextProps.name);
                }
                render() {
                    this.widget.render();
                }
            }
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                    this.state = useState({
                        name: "World",
                    });
                }
            }
            Parent.template = xml`
                <div>
                    <MyWidgetAdapter Component="MyWidget" name="state.name"/>
                </div>`;
            Parent.components = { MyWidgetAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');

            parent.state.name = "GED";
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hello GED!</div>');

            parent.destroy();
        });

        QUnit.test("sub widget is updated when props change (async)", async function (assert) {
            assert.expect(7);

            const prom = makeTestPromise();
            const MyWidget = Widget.extend({
                init: function (parent, name) {
                    this._super.apply(this, arguments);
                    this.name = name;
                },
                start: function () {
                    this.render();
                },
                render: function () {
                    this.$el.text(`Hello ${this.name}!`);
                    assert.step('render');
                },
                update: function (name) {
                    assert.step('update');
                    this.name = name;
                },
            });
            class MyWidgetAdapter extends ComponentAdapter {
                update(nextProps) {
                    return this.widget.update(nextProps.name);
                }
                render() {
                    this.widget.render();
                }
            }
            class AsyncComponent extends Component {
                willUpdateProps() {
                    return prom;
                }
            }
            AsyncComponent.template = xml`<div>Hi <t t-esc="props.name"/>!</div>`;
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                    this.state = useState({
                        name: "World",
                    });
                }
            }
            Parent.template = xml`
                <div>
                    <AsyncComponent name="state.name"/>
                    <MyWidgetAdapter Component="MyWidget" name="state.name"/>
                </div>`;
            Parent.components = { AsyncComponent, MyWidgetAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hi World!</div><div>Hello World!</div>');

            parent.state.name = "GED";
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hi World!</div><div>Hello World!</div>');

            prom.resolve();
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hi GED!</div><div>Hello GED!</div>');

            assert.verifySteps(['render', 'update', 'render']);

            parent.destroy();
        });

        QUnit.test("sub widget methods are correctly called", async function (assert) {
            assert.expect(8);

            const MyWidget = Widget.extend({
                on_attach_callback: function () {
                    assert.step('on_attach_callback');
                },
                on_detach_callback: function () {
                    assert.step('on_detach_callback');
                },
                destroy: function () {
                    assert.step('destroy');
                    this._super.apply(this, arguments);
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.verifySteps(['on_attach_callback']);

            parent.unmount();
            await parent.mount(target);

            assert.verifySteps(['on_detach_callback', 'on_attach_callback']);

            parent.destroy();

            assert.verifySteps(['on_detach_callback', 'destroy']);
        });

        QUnit.test("dynamic sub widget/component", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                start: function () {
                    this.$el.text('widget');
                },
            });
            class MyComponent extends Component {}
            MyComponent.template = xml`<div>component</div>`;
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.Children = [MyWidget, MyComponent];
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter t-foreach="Children" t-as="Child" Component="Child"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>widget</div><div>component</div>');

            parent.destroy();
        });

        QUnit.test("sub widget that triggers events", async function (assert) {
            assert.expect(5);

            let widget;
            const MyWidget = Widget.extend({
                init: function () {
                    this._super.apply(this, arguments);
                    widget = this;
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
                onSomeEvent(ev) {
                    assert.step(ev.detail.value);
                    assert.ok(ev.detail.__targetWidget instanceof MyWidget);
                }
            }
            Parent.template = xml`
                <div t-on-some-event="onSomeEvent">
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            widget.trigger_up('some-event', { value: 'a' });
            widget.trigger_up('some_event', { value: 'b' }); // _ are converted to -

            assert.verifySteps(['a', 'b']);

            parent.destroy();
        });

        QUnit.test("sub widget that calls _rpc", async function (assert) {
            assert.expect(3);

            const MyWidget = Widget.extend({
                willStart: function () {
                    return this._rpc({ route: 'some/route', params: { val: 2 } });
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.env = getMockedOwlEnv({
                mockRPC: function (route, args) {
                    assert.step(`${route} ${args.val}`);
                    return Promise.resolve();
                },
            });
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div></div>');
            assert.verifySteps(['some/route 2']);

            parent.destroy();
        });

        QUnit.test("sub widget that calls a service", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                start: function () {
                    let result;
                    this.trigger_up('call_service', {
                        service: 'math',
                        method: 'sqrt',
                        args: [9],
                        callback: r => {
                            result = r;
                        },
                    });
                    assert.strictEqual(result, 3);
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            const env = getMockedOwlEnv();
            env.services.math = {
                sqrt: v => Math.sqrt(v),
            };
            Parent.env = env;
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            parent.destroy();
        });

        QUnit.test("sub widget that requests the session", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                start: function () {
                    assert.strictEqual(this.getSession().key, 'value');
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.env = getMockedOwlEnv({
                session: { key: 'value' },
            });
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            parent.destroy();
        });

        QUnit.test("sub widget that calls load_views", async function (assert) {
            assert.expect(4);

            const MyWidget = Widget.extend({
                willStart: function () {
                    return this.loadViews('some_model', { x: 2 }, [[false, 'list']]);
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
            }
            Parent.env = getMockedOwlEnv({
                mockRPC: function (route, args) {
                    assert.strictEqual(route, '/web/dataset/call_kw/some_model');
                    assert.deepEqual(args.kwargs.context, { x: 2 });
                    assert.deepEqual(args.kwargs.views, [[false, 'list']]);
                    return Promise.resolve();
                },
            });
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div></div>');

            parent.destroy();
        });

        QUnit.test("sub widgets in a t-if/t-else", async function (assert) {
            assert.expect(3);

            const MyWidget1 = Widget.extend({
                start: function () {
                    this.$el.text('Hi');
                },
            });
            const MyWidget2 = Widget.extend({
                start: function () {
                    this.$el.text('Hello');
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget1 = MyWidget1;
                    this.MyWidget2 = MyWidget2;
                    this.state = useState({
                        flag: true,
                    });
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter t-if="state.flag" Component="MyWidget1"/>
                    <ComponentAdapter t-else="" Component="MyWidget2"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hi</div>');

            parent.state.flag = false;
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hello</div>');

            parent.state.flag = true;
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hi</div>');

            parent.destroy();
        });

        QUnit.test("sub widget in a t-if, and events", async function (assert) {
            assert.expect(6);

            let myWidget;
            const MyWidget = Widget.extend({
                start: function () {
                    myWidget = this;
                    this.$el.text('Hi');
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                    this.state = useState({
                        flag: true,
                    });
                }
                onSomeEvent(ev) {
                    assert.step(ev.detail.value);
                }
            }
            Parent.template = xml`
                <div t-on-some-event="onSomeEvent">
                    <ComponentAdapter t-if="state.flag" Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hi</div>');
            myWidget.trigger_up('some-event', { value: 'a' });

            parent.state.flag = false;
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '');
            myWidget.trigger_up('some-event', { value: 'b' });

            parent.state.flag = true;
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hi</div>');
            myWidget.trigger_up('some-event', { value: 'c' });

            assert.verifySteps(['a', 'c']);

            parent.destroy();
        });
    });
});
