odoo.define('web.basic_view_tests', function (require) {
    "use strict";

    const BasicView = require('web.BasicView');
    const BasicRenderer = require("web.BasicRenderer");
    const testUtils = require('web.test_utils');
    const widgetRegistryOwl = require('web.widgetRegistry');
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { xml } = owl;

    const createView = testUtils.createView;

    QUnit.module('LegacyViews', {
        beforeEach: function () {
            this.data = {
                fake_model: {
                    fields: {},
                    record: [],
                },
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                    },
                    records: [
                        { id: 1, bar: true, foo: "yop" },
                        { id: 2, bar: true, foo: "blip" },
                    ]
                },
            };
        },
    }, function () {

        QUnit.module('BasicView');

        QUnit.test('fields given in fieldDependencies of custom widget are loaded', async function (assert) {
            assert.expect(1);

            const basicView = BasicView.extend({
                viewType: "test",
                config: Object.assign({}, BasicView.prototype.config, {
                    Renderer: BasicRenderer,
                })
            });

            class MyWidget extends LegacyComponent {}
            MyWidget.fieldDependencies = {
                foo: { type: 'char' },
                bar: { type: 'boolean' },
            };
            MyWidget.template = xml/* xml */`
            <div class="custom-widget">Hello World!</div>
            `;
            widgetRegistryOwl.add('testWidget', MyWidget);

            const view = await createView({
                View: basicView,
                data: this.data,
                model: "foo",
                arch:
                `<test>
                    <widget name="testWidget"/>
                </test>`,
                mockRPC: function (route, args) {
                    if (route === "/web/dataset/search_read") {
                        assert.deepEqual(args.fields, ["foo", "bar"],
                            "search_read should be called with dependent fields");
                        return Promise.resolve();
                    }
                    return this._super.apply(this, arguments);
                }
            });

            view.destroy();
            delete widgetRegistryOwl.map.testWidget;
        });

    });
});
