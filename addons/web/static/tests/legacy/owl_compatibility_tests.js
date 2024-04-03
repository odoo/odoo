odoo.define('web.OwlCompatibilityTests', function (require) {
    "use strict";

    const fieldRegistry = require('web.field_registry');
    const widgetRegistry = require('web.widgetRegistry');
    const FormView = require('web.FormView');

    const {
        ComponentAdapter,
        ComponentWrapper,
        WidgetAdapterMixin,
        standaloneAdapter,
    } = require('web.OwlCompatibility');
    const testUtils = require('web.test_utils');
    const Widget = require('web.Widget');
    const Dialog = require("web.Dialog");
    const { registry } = require("@web/core/registry");
    const { LegacyComponent } = require("@web/legacy/legacy_component");
    const { mapLegacyEnvToWowlEnv, useWowlService } = require("@web/legacy/utils");

    const { legacyServiceProvider } = require("@web/legacy/legacy_service_provider");
    const { click } = require("@web/../tests/helpers/utils");

    const makeTestEnvironment = require("web.test_env");
    const { makeTestEnv } = require("@web/../tests/helpers/mock_env");
    const { getFixture, mount, useLogLifeCycle, destroy } = require("@web/../tests/helpers/utils");

    const makeTestPromise = testUtils.makeTestPromise;
    const nextTick = testUtils.nextTick;
    const addMockEnvironmentOwl = testUtils.mock.addMockEnvironmentOwl;

    const {
        Component,
        EventBus,
        onError,
        onMounted,
        onWillDestroy,
        onWillStart,
        onWillUnmount,
        onWillUpdateProps,
        useState,
        xml,
    } = owl;

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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');
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
            class Parent extends LegacyComponent {
                setup() {
                    this.MyWidget = MyWidget;
                    this.error = false;
                    onError((e) => {
                        assert.strictEqual(
                            e.toString(),
                            // eslint-disable-next-line no-useless-escape
                            `Error: The following error occurred in onWillStart: \"ComponentAdapter has more than 1 argument, 'widgetArgs' must be overriden.\"`
                        );
                        this.error = true;
                        this.render();
                    });
                }
            }
            Parent.template = xml`
                <div>
                    <t t-if="error">Error</t>
                    <ComponentAdapter t-else="" Component="MyWidget" a1="'Hello'" a2="'World'"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            await mount(Parent, target);
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hello World!</div>');

            parent.state.name = "GED";
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hello GED!</div>');
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
            class AsyncComponent extends LegacyComponent {
                setup() {
                    onWillUpdateProps(() => prom);
                }
            }
            AsyncComponent.template = xml`<div>Hi <t t-esc="props.name"/>!</div>`;
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hi World!</div><div>Hello World!</div>');

            parent.state.name = "GED";
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hi World!</div><div>Hello World!</div>');

            prom.resolve();
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hi GED!</div><div>Hello GED!</div>');

            assert.verifySteps(['render', 'update', 'render']);
        });

        QUnit.test("sub widget methods are correctly called", async function (assert) {
            assert.expect(6);

            const MyWidget = Widget.extend({
                on_attach_callback: function () {
                    assert.step('on_attach_callback');
                },
                on_detach_callback: function () {
                    assert.ok(document.body.contains(this.el));
                    assert.step('on_detach_callback');
                },
                destroy: function () {
                    assert.step('destroy');
                    this._super.apply(this, arguments);
                },
            });
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.verifySteps(['on_attach_callback']);

            destroy(parent);

            assert.verifySteps(['on_detach_callback', 'destroy']);
        });

        QUnit.test("dynamic sub widget/component", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                start: function () {
                    this.$el.text('widget');
                },
            });
            class MyComponent extends LegacyComponent {}
            MyComponent.template = xml`<div>component</div>`;
            class Parent extends LegacyComponent {
                constructor() {
                    super(...arguments);
                    this.Children = [MyWidget, MyComponent];
                }
            }
            Parent.template = xml`
                <div>
                    <ComponentAdapter t-foreach="Children" t-as="Child" Component="Child" t-key="Child"/>
                </div>`;
            Parent.components = { ComponentAdapter };

            const target = testUtils.prepareTarget();
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>widget</div><div>component</div>');
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
            class Parent extends LegacyComponent {
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
            await mount(Parent, target);

            widget.trigger_up('some-event', { value: 'a' });
            widget.trigger_up('some_event', { value: 'b' }); // _ are converted to -

            assert.verifySteps(['a', 'b']);
        });

        QUnit.test("sub widget that calls _rpc", async function (assert) {
            assert.expect(3);

            const MyWidget = Widget.extend({
                willStart: function () {
                    return this._rpc({ route: 'some/route', params: { val: 2 } });
                },
            });
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target, { env: owl.Component.env });

            assert.strictEqual(parent.el.innerHTML, '<div></div>');
            assert.verifySteps(['some/route 2']);
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
            class Parent extends LegacyComponent {
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

            const env = {
                services: {
                    math: {
                        sqrt: v => Math.sqrt(v),
                    }
                }
            };

            const target = testUtils.prepareTarget();
            await mount(Parent, target, { env });
        });

        QUnit.test("sub widget that requests the session", async function (assert) {
            assert.expect(1);

            const MyWidget = Widget.extend({
                start: function () {
                    assert.strictEqual(this.getSession().key, 'value');
                },
            });
            class Parent extends LegacyComponent {
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
            await mount(Parent, target, { env: owl.Component.env });
            cleanUp();
        });

        QUnit.test("sub widget that calls load_views", async function (assert) {
            assert.expect(4);

            const MyWidget = Widget.extend({
                willStart: function () {
                    return this.loadViews('some_model', { x: 2 }, [[false, 'list']]);
                },
            });
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target, { env: owl.Component.env });

            assert.strictEqual(parent.el.innerHTML, '<div></div>');

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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.strictEqual(parent.el.innerHTML, '<div>Hi</div>');

            parent.state.flag = false;
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hello</div>');

            parent.state.flag = true;
            await nextTick();

            assert.strictEqual(parent.el.innerHTML, '<div>Hi</div>');
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

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
        });

        QUnit.test("adapter contains the el of sub widget as firstChild (modify)", async function (assert) {
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            const widgetEl = myWidget.el;

            assert.strictEqual(target.firstChild, widgetEl);
            await testUtils.dom.click(widgetEl);

            parent.state.name = "AAB";
            await nextTick();

            assert.strictEqual(widgetEl, myWidget.el);
            await testUtils.dom.click(widgetEl);

            parent.state.name = "MCM";
            await nextTick();

            assert.strictEqual(widgetEl, myWidget.el);
            await testUtils.dom.click(widgetEl);

            assert.verifySteps(["GED", "AAB", "MCM"]);
        });

        QUnit.test("adapter handles a widget that replaces its el", async function (assert) {
            assert.expect(10);

            let renderId = 0;
            const MyWidget = Widget.extend({
                events: {
                    click: "_onClick",
                },
                init: function (parent, name) {
                    this._super.apply(this, arguments);
                    this.name = name;
                },
                start: function () {
                    this.render();
                },
                render: function () {
                    this._replaceElement("<div>Click me!</div>");
                    this.el.classList.add(`widget_id_${renderId++}`);
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

            assert.containsOnce(target, ".widget_id_0");

            await testUtils.dom.click(target.querySelector(".widget_id_0"));

            parent.state.name = "AAB";
            await nextTick();

            assert.containsNone(target, ".widget_id_0");
            assert.containsOnce(target, ".widget_id_1");
            await testUtils.dom.click(target.querySelector(".widget_id_1"));

            parent.state.name = "MCM";
            await nextTick();

            assert.containsNone(target, ".widget_id_0");
            assert.containsNone(target, ".widget_id_1");
            assert.containsOnce(target, ".widget_id_2");
            await testUtils.dom.click(target.querySelector(".widget_id_2"));

            assert.verifySteps(["GED", "AAB", "MCM"]);
        });

        QUnit.test("standaloneAdapter can trigger in the DOM and execute action", async (assert) => {
            assert.expect(3)
            const done = assert.async();

            const MyDialog = Dialog.extend({
                async start() {
                    const res = await this._super(...arguments);
                    const btn = document.createElement("button");
                    btn.classList.add("myButton");
                    btn.addEventListener("click", () => {
                        this.trigger_up("execute_action", {
                            action_data: {},
                            env: {},
                        });
                    });
                    this.el.appendChild(btn);
                    return res;
                }
            });

            const dialogOpened = makeTestPromise();
            class MyComp extends Component {
                setup() {
                    onWillDestroy(() => {
                        this.dialog.destroy();
                    })
                }
                async spawnDialog() {
                    const parent = standaloneAdapter();
                    this.dialog = new MyDialog(parent);
                    await this.dialog.open();
                    dialogOpened.resolve();
                }
            }
            MyComp.template = xml`<button class="spawnDialog" t-on-click="spawnDialog"/>`;

            const actionService = {
                start() {
                    return {
                        async doActionButton() {
                            assert.step("doActionButton");
                        }
                    }
                }
            }

            registry.category("services").add("action", actionService);
            registry.category("services").add("legacy_service_provider", legacyServiceProvider);

            const env = await makeTestEnv();
            await addMockEnvironmentOwl(Component);

            const target = getFixture()
            await mount(MyComp, target, {env});
            await click(target.querySelector(".spawnDialog"));
            await dialogOpened;

            assert.containsOnce(document.body, ".modal"); // legacy modal
            await click(document.body.querySelector(".modal .myButton"));
            assert.verifySteps(["doActionButton"]);
            done();
        })

        QUnit.module('WidgetAdapterMixin and ComponentWrapper');

        QUnit.test("widget with sub component", async function (assert) {
            assert.expect(2);

            let component;
            let wrapper;
            class MyComponent extends LegacyComponent {
                setup() {
                    component = this;
                }
            }
            MyComponent.template = xml`<div>Component</div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    wrapper = new ComponentWrapper(this, MyComponent, {});
                    return wrapper.mount(this.el);
                },
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, "<div>Component</div>");
            assert.strictEqual(wrapper.componentRef.comp, component);

            widget.destroy();
        });

        QUnit.test("sub component hooks are correctly called", async function (assert) {
            assert.expect(13);

            class MyComponent extends LegacyComponent {
                setup() {
                    assert.step("setup");
                    onWillStart(() => {
                        assert.step("willStart");
                    });
                    onMounted(() => {
                        assert.step("mounted");
                    });
                    onWillUnmount(() => {
                        assert.step("willUnmount");
                    });
                    onWillDestroy(() => {
                        assert.step("willDestroy");
                    });
                }
            }
            MyComponent.template = xml`<div>Component</div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    const component = new ComponentWrapper(this, MyComponent, {});
                    return component.mount(this.el);
                },
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.verifySteps(["setup", "willStart", "mounted"]);
            assert.strictEqual(widget.el.innerHTML, "<div>Component</div>");

            widget.$el.detach();
            widget.on_detach_callback();

            assert.verifySteps(["willUnmount"]);

            widget.$el.appendTo(target);
            widget.on_attach_callback();

            assert.verifySteps(["mounted"]);
            assert.strictEqual(widget.el.innerHTML, "<div>Component</div>");

            widget.destroy();

            assert.verifySteps(["willUnmount", "willDestroy"]);
        });

        QUnit.test("sub component hooks are correctly called when appended in iframe", async function (assert) {
            assert.expect(13);

            class MyComponent extends LegacyComponent {
                setup() {
                    assert.step("setup");
                    onWillStart(() => {
                        assert.step("willStart");
                    });
                    onMounted(() => {
                        assert.step("mounted");
                    });
                    onWillUnmount(() => {
                        assert.step("willUnmount");
                    });
                    onWillDestroy(() => {
                        assert.step("willDestroy");
                    });
                }
            }
            MyComponent.template = xml`<div>Component</div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    const component = new ComponentWrapper(this, MyComponent, {});
                    return component.mount(this.el);
                },
            });

            const widget = new MyWidget();
            const target = testUtils.prepareTarget();
            const iframe = document.createElement("iframe");
            target.appendChild(iframe);
            await widget.appendTo(iframe.contentWindow.document.body);

            assert.verifySteps(["setup", "willStart", "mounted"]);
            assert.strictEqual(widget.el.innerHTML, "<div>Component</div>");

            widget.$el.detach();
            widget.on_detach_callback();

            assert.verifySteps(["willUnmount"]);

            widget.$el.appendTo(iframe.contentWindow.document.body);
            widget.on_attach_callback();

            assert.verifySteps(["mounted"]);
            assert.strictEqual(widget.el.innerHTML, "<div>Component</div>");

            widget.destroy();

            assert.verifySteps(["willUnmount", "willDestroy"]);
        });

        QUnit.test("lifecycle with several sub components", async function (assert) {
            assert.expect(21);

            class MyComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert), this.props.id);
                }
            }
            MyComponent.template = xml`<div>Component <t t-esc="props.id"/></div>`;
            const MyWidget = WidgetAdapter.extend({
                start() {
                    const c1 = new ComponentWrapper(this, MyComponent, {id: 1});
                    const c2 = new ComponentWrapper(this, MyComponent, {id: 2});
                    return Promise.all([c1.mount(this.el), c2.mount(this.el)]);
                }
            });

            const target = testUtils.prepareTarget();
            const widget = new MyWidget();
            await widget.appendTo(target);

            assert.strictEqual(widget.el.innerHTML, '<div>Component 1</div><div>Component 2</div>');
            assert.verifySteps([
                "onWillStart MyComponent 1",
                "onWillStart MyComponent 2",
                "onWillRender MyComponent 1",
                "onRendered MyComponent 1",
                "onWillRender MyComponent 2",
                "onRendered MyComponent 2",
                "onMounted MyComponent 1",
                "onMounted MyComponent 2"
            ]);

            widget.$el.detach();
            widget.on_detach_callback();
            assert.verifySteps([
                "onWillUnmount MyComponent 1",
                "onWillUnmount MyComponent 2"
            ]);

            widget.$el.appendTo(target);
            widget.on_attach_callback();
            assert.verifySteps([
                "onMounted MyComponent 1",
                "onMounted MyComponent 2"
            ]);

            widget.destroy();
            assert.verifySteps([
                "onWillUnmount MyComponent 1",
                "onWillDestroy MyComponent 1",
                "onWillUnmount MyComponent 2",
                "onWillDestroy MyComponent 2"
            ]);
        });

        QUnit.test("lifecycle with several levels of sub components", async function (assert) {
            assert.expect(21);

            class MyChildComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyChildComponent.template = xml`<div>child</div>`;
            class MyComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
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
            assert.verifySteps([
                "onWillStart MyComponent",
                "onWillRender MyComponent",
                "onWillStart MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);

            widget.$el.detach();
            widget.on_detach_callback();
            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillUnmount MyChildComponent"
            ]);

            widget.$el.appendTo(target);
            widget.on_attach_callback();
            assert.verifySteps([
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);

            widget.destroy();
            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillUnmount MyChildComponent",
                "onWillDestroy MyChildComponent",
                "onWillDestroy MyComponent"
            ]);
        });

        QUnit.test("lifecycle mount in fragment", async function (assert) {
            assert.expect(17);

            class MyChildComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyChildComponent.template = xml`<div>child</div>`;
            class MyComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
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
            const fragment = document.createElement("div");
            await widget.appendTo(fragment);

            assert.strictEqual(widget.el.innerHTML, '<div><div>child</div></div>');
            assert.verifySteps([
                "onWillStart MyComponent",
                "onWillRender MyComponent",
                "onWillStart MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
            ]);

            widget.$el.appendTo(target);
            widget.on_attach_callback();
            assert.verifySteps([
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);

            widget.on_attach_callback();
            assert.verifySteps([]);

            widget.destroy();
            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillUnmount MyChildComponent",
                "onWillDestroy MyChildComponent",
                "onWillDestroy MyComponent"
            ]);
        });

        QUnit.test("lifecycle mount/unmount", async function (assert) {
            assert.expect(37);

            class MyChildComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyChildComponent.template = xml`<div>child</div>`;
            class MyComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyComponent.template = xml`<div><MyChildComponent/></div>`;
            MyComponent.components = { MyChildComponent };

            const target = testUtils.prepareTarget();
            const widget = new ComponentWrapper(null, MyComponent, {});
            await widget.mount(target);

            assert.strictEqual(target.innerHTML, "<div><div>child</div></div>");
            assert.verifySteps([
                "onWillStart MyComponent",
                "onWillRender MyComponent",
                "onWillStart MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);

            widget.unmount();
            assert.strictEqual(target.innerHTML, "");
            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillUnmount MyChildComponent",
            ]);

            await widget.mount();

            assert.verifySteps([
                "onWillUpdateProps MyComponent",
                "onWillRender MyComponent",
                "onWillUpdateProps MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);
            assert.strictEqual(target.innerHTML, "<div><div>child</div></div>");

            widget.unmount();
            assert.strictEqual(target.innerHTML, "");
            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillUnmount MyChildComponent",
            ]);

            await widget.mount();

            assert.verifySteps([
                "onWillUpdateProps MyComponent",
                "onWillRender MyComponent",
                "onWillUpdateProps MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);
        });

        QUnit.test("lifecycle mount/unmount/update", async function (assert) {
            assert.expect(24);

            class MyChildComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyChildComponent.template = xml`<div>child <t t-esc="props.text" /></div>`;
            class MyComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyComponent.template = xml`<div><MyChildComponent t-props="props" /></div>`;
            MyComponent.components = { MyChildComponent };

            const target = testUtils.prepareTarget();
            const widget = new ComponentWrapper(null, MyComponent, {
                text: "takeNoMess"
            });
            await widget.mount(target);

            assert.strictEqual(target.innerHTML, "<div><div>child takeNoMess</div></div>");
            assert.verifySteps([
                "onWillStart MyComponent",
                "onWillRender MyComponent",
                "onWillStart MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);

            widget.unmount();
            assert.strictEqual(target.innerHTML, "");
            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillUnmount MyChildComponent",
            ]);

            await widget.update({
                text: "leveeBreaks"
            });

            assert.verifySteps([
                "onWillUpdateProps MyComponent",
                "onWillRender MyComponent",
                "onWillUpdateProps MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);
            assert.strictEqual(target.innerHTML, "<div><div>child leveeBreaks</div></div>");
        });

        QUnit.test("lifecycle mount/unmount/update/render", async function (assert) {
            assert.expect(36);

            class MyChildComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyChildComponent.template = xml`<div>child <t t-esc="props.text" /></div>`;
            class MyComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle(assert.step.bind(assert));
                }
            }
            MyComponent.template = xml`<div><MyChildComponent t-props="props" /></div>`;
            MyComponent.components = { MyChildComponent };

            const target = testUtils.prepareTarget();
            const widget = new ComponentWrapper(null, MyComponent, {
                text: "takeNoMess"
            });
            await widget.mount(target);

            assert.strictEqual(target.innerHTML, "<div><div>child takeNoMess</div></div>");
            assert.verifySteps([
                "onWillStart MyComponent",
                "onWillRender MyComponent",
                "onWillStart MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);

            widget.unmount();
            assert.strictEqual(target.innerHTML, "");
            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillUnmount MyChildComponent",
            ]);

            await widget.update({
                text: "leveeBreaks"
            });

            assert.verifySteps([
                "onWillUpdateProps MyComponent",
                "onWillRender MyComponent",
                "onWillUpdateProps MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onMounted MyChildComponent",
                "onMounted MyComponent"
            ]);
            assert.strictEqual(target.innerHTML, "<div><div>child leveeBreaks</div></div>");

            await widget.render();
            assert.verifySteps([
                "onWillUpdateProps MyComponent",
                "onWillRender MyComponent",
                "onWillUpdateProps MyChildComponent",
                "onRendered MyComponent",
                "onWillRender MyChildComponent",
                "onRendered MyChildComponent",
                "onWillPatch MyComponent",
                "onWillPatch MyChildComponent",
                "onPatched MyChildComponent",
                "onPatched MyComponent"
            ]);
            assert.strictEqual(target.innerHTML, "<div><div>child leveeBreaks</div></div>");
        });

        QUnit.test("sub component can be updated (in DOM)", async function (assert) {
            assert.expect(2);

            class MyComponent extends LegacyComponent {}
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
            assert.expect(18);

            class MyComponent extends LegacyComponent {
                setup() {
                    useLogLifeCycle((log) => assert.step(log));
                }
            }
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
            assert.verifySteps([
                "onWillStart MyComponent",
                "onWillRender MyComponent",
                "onRendered MyComponent",
                "onMounted MyComponent"
            ]);

            assert.strictEqual(target.innerHTML, '<div><div>Component 1</div></div>');

            widget.$el.detach();
            widget.on_detach_callback();

            assert.verifySteps([
                "onWillUnmount MyComponent"
            ]);

            await widget.update();
            assert.verifySteps([
                "onWillUpdateProps MyComponent",
                "onWillRender MyComponent",
                "onRendered MyComponent"
            ]);

            widget.$el.appendTo(target);
            widget.on_attach_callback();
            assert.verifySteps([
                "onMounted MyComponent"
            ]);

            assert.strictEqual(target.innerHTML, '<div><div>Component 2</div></div>');

            widget.destroy();

            assert.verifySteps([
                "onWillUnmount MyComponent",
                "onWillDestroy MyComponent"
            ]);
        });

        QUnit.test("update a destroyed sub component", async function (assert) {
            assert.expect(1);

            class MyComponent extends LegacyComponent {}
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

            class WidgetComponent extends LegacyComponent {}
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
            class WidgetComponent extends LegacyComponent {}
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
            class MyComponent extends LegacyComponent {}
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
            class Parent extends LegacyComponent {
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
            const parent = await mount(Parent, target);

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
            class MyComponent extends LegacyComponent {
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

        QUnit.module("WidgetWrapper");

        QUnit.test("correctly update widget component during mounting", async function (assert) {
            // It comes with a fix for a bug that occurred because in some circonstances,
            // a widget component can be updated twice.
            // Specifically, this occurs when there is 'pad' widget in the form view, because this
            // widget does a 'setValue' in its 'renderEdit', which thus resets the widget component.
            assert.expect(4);

            const PadLikeWidget = fieldRegistry.get('char').extend({
                _renderEdit() {
                    assert.step("setValue");
                    this._setValue("some value");
                }
            });
            fieldRegistry.add('pad_like', PadLikeWidget);

            class WidgetComponent extends LegacyComponent {}
            WidgetComponent.template = xml`<div>Widget</div>`;
            widgetRegistry.add("widget_comp", WidgetComponent);

            const form = await testUtils.createView({
                View: FormView,
                model: 'partner',
                res_id: 1,
                data: {
                    partner: {
                        fields: {
                            id: {string: "id", type:"integer"},
                            foo: {string: "Foo", type: "char"},
                        },
                        records: [{
                            id: 1,
                            foo: "value",
                        }],
                    },
                },
                arch: `
                    <form><sheet><group>
                        <field name="foo" widget="pad_like" />
                        <widget name="widget_comp" />
                    </group></sheet></form>
                `,
            });

            assert.containsOnce(form, ".o_legacy_form_view.o_form_readonly");

            await testUtils.dom.click(form.$(".o_form_label")[0]);
            await testUtils.nextTick(); // wait for quick edit

            assert.containsOnce(form, ".o_legacy_form_view.o_form_editable");
            assert.verifySteps(["setValue"]);

            form.destroy();

            delete fieldRegistry.map.pad_like;
            delete widgetRegistry.map.widget_comp;
        });

        QUnit.module("useWowlService");

        QUnit.test("simple use case of useWowlService", async function (assert) {
            assert.expect(1);

            registry.category("services").add("test", {
                start() {
                    return "I'm a wowl service";
                },
            });
            const wowlEnv = await makeTestEnv();
            const legacyEnv = makeTestEnvironment();
            mapLegacyEnvToWowlEnv(legacyEnv, wowlEnv);

            class MyComponent extends Component {
                setup() {
                    assert.strictEqual(useWowlService("test"), "I'm a wowl service");
                }
            }
            MyComponent.template = xml`<div/>`;

            await mount(MyComponent, getFixture(), { env: legacyEnv });
        });

        QUnit.module("EventBus");

        QUnit.test("unregister multiple listener from the same target", async function (assert) {
            const target = Symbol("test");
            const bus = new EventBus();
            let i = 0;

            bus.on("a", target, () => assert.step(`a:${i++}`));
            bus.on("b", target, () => assert.step(`b:${i++}`));

            bus.trigger("a");
            bus.trigger("b");

            bus.off("a", target);
            bus.off("b", target);

            bus.trigger("a");
            bus.trigger("b");

            assert.verifySteps([
                "a:0",
                "b:1",
            ], "callback should not be called after unregistering them");
        });

    });
});
