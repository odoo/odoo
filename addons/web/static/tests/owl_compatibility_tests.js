odoo.define('web.OwlCompatibilityTests', function (require) {
    "use strict";

    const { ComponentAdapter, ComponentWrapper, WidgetAdapterMixin } = require('web.OwlCompatibility');
    const testUtils = require('web.test_utils');
    const Widget = require('web.Widget');

    const makeTestPromise = testUtils.makeTestPromise;
    const nextTick = testUtils.nextTick;
    const addMockEnvironmentOwl = testUtils.mock.addMockEnvironmentOwl;

    const { Component, tags, useState } = owl;
    const { xml } = tags;


    const WidgetAdapter = Widget.extend(WidgetAdapterMixin, {
        destroy() {
            this._super(...arguments);
            WidgetAdapterMixin.destroy.call(this, ...arguments);
        },
    });

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
                updateWidget(nextProps) {
                    return this.widget.update(nextProps.name);
                }
                renderWidget() {
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
                updateWidget(nextProps) {
                    return this.widget.update(nextProps.name);
                }
                renderWidget() {
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
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };
            const cleanUp = await addMockEnvironmentOwl(Parent, {
                mockRPC: function (route, args) {
                    assert.step(`${route} ${args.val}`);
                    return Promise.resolve();
                },
            });

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div></div>');
            assert.verifySteps(['some/route 2']);

            parent.destroy();
            cleanUp();
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
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };
            Parent.env.services.math = {
                sqrt: v => Math.sqrt(v),
            };

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
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };
            const cleanUp = await addMockEnvironmentOwl(Parent, {
                session: { key: 'value' },
            });

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            parent.destroy();
            cleanUp();
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
            Parent.template = xml`
                <div>
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };
            const cleanUp = await addMockEnvironmentOwl(Parent, {
                mockRPC: function (route, args) {
                    assert.strictEqual(route, '/web/dataset/call_kw/some_model');
                    assert.deepEqual(args.kwargs.context, { x: 2 });
                    assert.deepEqual(args.kwargs.views, [[false, 'list']]);
                    return Promise.resolve();
                },
            });

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div></div>');

            parent.destroy();
            cleanUp();
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

        QUnit.test("adapter keeps same el as sub widget (modify)", async function (assert) {
            assert.expect(7);

            let myWidget;
            const MyWidget = Widget.extend({
                events: {
                    click: "_onClick",
                },
                init: function (parent, name) {
                    myWidget = this;
                    this._super.apply(this, arguments);
                    this.name = name;
                },
                start: function () {
                    this.render();
                },
                render: function () {
                    this.$el.text("Click me!");
                },
                update: function (name) {
                    this.name = name;
                },
                _onClick: function () {
                    assert.step(this.name);
                },
            });
            class MyWidgetAdapter extends ComponentAdapter {
                updateWidget(nextProps) {
                    return this.widget.update(nextProps.name);
                }
                renderWidget() {
                    this.widget.render();
                }
            }
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                    this.state = useState({
                        name: "GED",
                    });
                }
            }
            Parent.template = xml`
                <MyWidgetAdapter Component="MyWidget" name="state.name"/>
            `;
            Parent.components = { MyWidgetAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el, myWidget.el);
            await testUtils.dom.click(parent.el);

            parent.state.name = "AAB";
            await nextTick();

            assert.strictEqual(parent.el, myWidget.el);
            await testUtils.dom.click(parent.el);

            parent.state.name = "MCM";
            await nextTick();

            assert.strictEqual(parent.el, myWidget.el);
            await testUtils.dom.click(parent.el);

            assert.verifySteps(["GED", "AAB", "MCM"]);

            parent.destroy();
        });

        QUnit.test("adapter keeps same el as sub widget (replace)", async function (assert) {
            assert.expect(7);

            let myWidget;
            const MyWidget = Widget.extend({
                events: {
                    click: "_onClick",
                },
                init: function (parent, name) {
                    myWidget = this;
                    this._super.apply(this, arguments);
                    this.name = name;
                },
                start: function () {
                    this.render();
                },
                render: function () {
                    this._replaceElement("<div>Click me!</div>");
                },
                update: function (name) {
                    this.name = name;
                },
                _onClick: function () {
                    assert.step(this.name);
                },
            });
            class MyWidgetAdapter extends ComponentAdapter {
                updateWidget(nextProps) {
                    return this.widget.update(nextProps.name);
                }
                renderWidget() {
                    this.widget.render();
                }
            }
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                    this.state = useState({
                        name: "GED",
                    });
                }
            }
            Parent.template = xml`
                <MyWidgetAdapter Component="MyWidget" name="state.name"/>
            `;
            Parent.components = { MyWidgetAdapter };

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el, myWidget.el);
            await testUtils.dom.click(parent.el);

            parent.state.name = "AAB";
            await nextTick();

            assert.strictEqual(parent.el, myWidget.el);
            await testUtils.dom.click(parent.el);

            parent.state.name = "MCM";
            await nextTick();

            assert.strictEqual(parent.el, myWidget.el);
            await testUtils.dom.click(parent.el);

            assert.verifySteps(["GED", "AAB", "MCM"]);

            parent.destroy();
        });

        QUnit.module('WidgetAdapterMixin and ComponentWrapper');

        QUnit.test("widget with sub component", async function (assert) {
            assert.expect(1);

            class MyComponent extends Component {}
            MyComponent.template = xml`<div>Component</div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    const component = new ComponentWrapper(this, MyComponent, {});
                    return component.mount(this.el);
                }
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, '<div>Component</div>');

            widget.destroy();
        });

        QUnit.test("sub component hooks are correctly called", async function (assert) {
            assert.expect(14);

            let component;
            class MyComponent extends Component {
                constructor(parent) {
                    super(parent);
                    assert.step("init");
                }
                async willStart() {
                    assert.step("willStart");
                }
                mounted() {
                    assert.step("mounted");
                }
                willUnmount() {
                    assert.step("willUnmount");
                }
                __destroy() {
                    super.__destroy();
                    assert.step("__destroy");
                }
            }
            MyComponent.template = xml`<div>Component</div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    component = new ComponentWrapper(this, MyComponent, {});
                    return component.mount(this.el);
                }
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.verifySteps(['init', 'willStart', 'mounted']);
            assert.ok(component.__owl__.isMounted);

            widget.$el.detach();
            widget.on_detach_callback();

            assert.verifySteps(['willUnmount']);
            assert.ok(!component.__owl__.isMounted);

            widget.$el.appendTo(target);
            widget.on_attach_callback();

            assert.verifySteps(['mounted']);
            assert.ok(component.__owl__.isMounted);

            widget.destroy();

            assert.verifySteps(['willUnmount', '__destroy']);
        });

        QUnit.test("isMounted with several sub components", async function (assert) {
            assert.expect(11);

            let c1;
            let c2;
            class MyComponent extends Component {}
            MyComponent.template = xml`<div>Component <t t-esc="props.id"/></div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    c1 = new ComponentWrapper(this, MyComponent, {id: 1});
                    c2 = new ComponentWrapper(this, MyComponent, {id: 2});
                    return Promise.all([c1.mount(this.el), c2.mount(this.el)]);
                }
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, '<div>Component 1</div><div>Component 2</div>');
            assert.ok(c1.__owl__.isMounted);
            assert.ok(c2.__owl__.isMounted);

            widget.$el.detach();
            widget.on_detach_callback();

            assert.ok(!c1.__owl__.isMounted);
            assert.ok(!c2.__owl__.isMounted);

            widget.$el.appendTo(target);
            widget.on_attach_callback();

            assert.ok(c1.__owl__.isMounted);
            assert.ok(c2.__owl__.isMounted);

            widget.destroy();

            assert.ok(!c1.__owl__.isMounted);
            assert.ok(!c2.__owl__.isMounted);
            assert.ok(c1.__owl__.isDestroyed);
            assert.ok(c2.__owl__.isDestroyed);
        });

        QUnit.test("isMounted with several levels of sub components", async function (assert) {
            assert.expect(6);

            let child;
            class MyChildComponent extends Component {
                constructor() {
                    super(...arguments);
                    child = this;
                }
            }
            MyChildComponent.template = xml`<div>child</div>`;
            class MyComponent extends Component {}
            MyComponent.template = xml`<div><MyChildComponent/></div>`;
            MyComponent.components = { MyChildComponent };
            const MyWidget = WidgetAdapter.extend({
                start() {
                    let component = new ComponentWrapper(this, MyComponent, {});
                    return component.mount(this.el);
                }
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, '<div><div>child</div></div>');
            assert.ok(child.__owl__.isMounted);

            widget.$el.detach();
            widget.on_detach_callback();

            assert.ok(!child.__owl__.isMounted);

            widget.$el.appendTo(target);
            widget.on_attach_callback();

            assert.ok(child.__owl__.isMounted);

            widget.destroy();

            assert.ok(!child.__owl__.isMounted);
            assert.ok(child.__owl__.isDestroyed);
        });

        QUnit.test("sub component can be updated (in DOM)", async function (assert) {
            assert.expect(2);

            class MyComponent extends Component {}
            MyComponent.template = xml`<div>Component <t t-esc="props.val"/></div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    this.component = new ComponentWrapper(this, MyComponent, {val: 1});
                    return this.component.mount(this.el);
                },
                update() {
                    return this.component.update({val: 2});
                },
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, '<div>Component 1</div>');

            await widget.update();

            assert.strictEqual(widget.el.innerHTML, '<div>Component 2</div>');

            widget.destroy();
        });

        QUnit.test("sub component can be updated (not in DOM)", async function (assert) {
            assert.expect(4);

            class MyComponent extends Component {}
            MyComponent.template = xml`<div>Component <t t-esc="props.val"/></div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    this.component = new ComponentWrapper(this, MyComponent, {val: 1});
                    return this.component.mount(this.el);
                },
                update() {
                    return this.component.update({val: 2});
                },
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, '<div>Component 1</div>');

            widget.$el.detach();
            widget.on_detach_callback();

            assert.ok(!widget.component.__owl__.isMounted);

            await widget.update();

            widget.$el.appendTo(target);
            widget.on_attach_callback();

            assert.ok(widget.component.__owl__.isMounted);
            assert.strictEqual(widget.el.innerHTML, '<div>Component 2</div>');

            widget.destroy();
        });

        QUnit.test("update a destroyed sub component", async function (assert) {
            assert.expect(1);

            class MyComponent extends Component {}
            MyComponent.template = xml`<div>Component <t t-esc="props.val"/></div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    this.component = new ComponentWrapper(this, MyComponent, {val: 1});
                    return this.component.mount(this.el);
                },
                update() {
                    this.component.update({val: 2});
                },
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, '<div>Component 1</div>');

            widget.destroy();

            widget.update(); // should not crash
        });

        QUnit.test("sub component that triggers events", async function (assert) {
            assert.expect(3);

            class WidgetComponent extends Component {}
            WidgetComponent.template = xml`<div>Component</div>`;

            const MyWidget = WidgetAdapter.extend({
                custom_events: _.extend({}, Widget.custom_events, {
                    some_event: function (ev) {
                        assert.step(ev.data.value);
                    }
                }),
                start() {
                    this.component = new ComponentWrapper(this, WidgetComponent, {});
                    return this.component.mount(this.el);
                },
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            widget.component.trigger('some_event', { value: 'a' });
            widget.component.trigger('some-event', { value: 'b' }); // - are converted to _

            assert.verifySteps(['a', 'b']);

            widget.destroy();
        });

        QUnit.test("change parent of ComponentWrapper", async function (assert) {
            assert.expect(7);

            let myComponent;
            let widget1;
            let widget2;
            class WidgetComponent extends Component {}
            WidgetComponent.template = xml`<div>Component</div>`;
            const MyWidget = WidgetAdapter.extend({
                custom_events: _.extend({}, Widget.custom_events, {
                    some_event: function (ev) {
                        assert.strictEqual(this, ev.data.widget);
                        assert.step(ev.data.value);
                    }
                }),
            });
            const Parent = Widget.extend({
                start() {
                    const proms = [];
                    myComponent = new ComponentWrapper(null, WidgetComponent, {});
                    widget1 = new MyWidget();
                    widget2 = new MyWidget();
                    proms.push(myComponent.mount(this.el));
                    proms.push(widget1.appendTo(this.$el));
                    proms.push(widget2.appendTo(this.$el));
                    return Promise.all(proms);
                }
            });

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.appendTo(target);

            // 1. No parent
            myComponent.trigger('some-event', { value: 'a', widget: null });

            assert.verifySteps([]);

            // 2. No parent --> parent (widget1)
            myComponent.unmount();
            await myComponent.mount(widget1.el);
            myComponent.setParent(widget1);

            myComponent.trigger('some-event', { value: 'b', widget: widget1 });

            assert.verifySteps(['b']);

            // 3. Parent (widget1) --> new parent (widget2)
            myComponent.unmount();
            await myComponent.mount(widget2.el);
            myComponent.setParent(widget2);

            myComponent.trigger('some-event', { value: 'c', widget: widget2 });

            assert.verifySteps(['c']);

            parent.destroy();
        });

        QUnit.module('Several layers of legacy widgets and Owl components');

        QUnit.test("Owl over legacy over Owl", async function (assert) {
            assert.expect(7);

            let leafComponent;
            class MyComponent extends Component {}
            MyComponent.template = xml`<span>Component</span>`;
            const MyWidget = WidgetAdapter.extend({
                custom_events: {
                    widget_event: function (ev) {
                        assert.step(`[widget] widget-event ${ev.data.value}`);
                    },
                    both_event: function (ev) {
                        assert.step(`[widget] both-event ${ev.data.value}`);
                        if (ev.data.value === 4) {
                            ev.stopPropagation();
                        }
                    }
                },
                start() {
                    leafComponent = new ComponentWrapper(this, MyComponent, {});
                    return leafComponent.mount(this.el);
                },
            });
            class Parent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
                onRootEvent(ev) {
                    assert.step(`[root] root-event ${ev.detail.value}`);
                }
                onBothEvent(ev) {
                    assert.step(`[root] both-event ${ev.detail.value}`);
                }
            }
            Parent.template = xml`
                <div t-on-root-event="onRootEvent" t-on-both-event="onBothEvent">
                    <ComponentAdapter Component="MyWidget"/>
                </div>`;
            Parent.components = { ComponentAdapter };


            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.mount(target);

            assert.strictEqual(parent.el.innerHTML, '<div><span>Component</span></div>');

            leafComponent.trigger('root-event', { value: 1 });
            leafComponent.trigger('widget-event', { value: 2 });
            leafComponent.trigger('both-event', { value: 3 });
            leafComponent.trigger('both-event', { value: 4 }); // will be stopped by widget

            assert.verifySteps([
                '[root] root-event 1',
                '[widget] widget-event 2',
                '[widget] both-event 3',
                '[root] both-event 3',
                '[widget] both-event 4',
            ]);

            parent.destroy();
        });

        QUnit.test("Legacy over Owl over legacy", async function (assert) {
            assert.expect(7);

            let leafWidget;
            const MyWidget = Widget.extend({
                start: function () {
                    leafWidget = this;
                    this.$el.text('Widget');
                }
            });
            class MyComponent extends Component {
                constructor() {
                    super(...arguments);
                    this.MyWidget = MyWidget;
                }
                onComponentEvent(ev) {
                    assert.step(`[component] component-event ${ev.detail.value}`);
                }
                onBothEvent(ev) {
                    assert.step(`[component] both-event ${ev.detail.value}`);
                    if (ev.detail.value === 4) {
                        ev.stopPropagation();
                    }
                }
            }
            MyComponent.template = xml`
                <span t-on-component-event="onComponentEvent" t-on-both-event="onBothEvent">
                    <ComponentAdapter Component="MyWidget"/>
                </span>`;
            MyComponent.components = { ComponentAdapter };
            const Parent = WidgetAdapter.extend({
                custom_events: {
                    root_event: function (ev) {
                        assert.step(`[root] root-event ${ev.data.value}`);
                    },
                    both_event: function (ev) {
                        assert.step(`[root] both-event ${ev.data.value}`);
                    },
                },
                start() {
                    const component = new ComponentWrapper(this, MyComponent, {});
                    return component.mount(this.el);
                }
            });

            const target = testUtils.prepareTarget();
            const parent = new Parent();
            await parent.appendTo(target);

            assert.strictEqual(parent.el.innerHTML, '<span><div>Widget</div></span>');

            leafWidget.trigger_up('root-event', { value: 1 });
            leafWidget.trigger_up('component-event', { value: 2 });
            leafWidget.trigger_up('both-event', { value: 3 });
            leafWidget.trigger_up('both-event', { value: 4 }); // will be stopped by component

            assert.verifySteps([
                '[root] root-event 1',
                '[component] component-event 2',
                '[component] both-event 3',
                '[root] both-event 3',
                '[component] both-event 4',
            ]);

            parent.destroy();
        });
    });
});
