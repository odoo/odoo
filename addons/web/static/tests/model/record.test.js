import { expect, test } from "@odoo/hoot";
import { queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import { Component, onError, useState, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    findComponent,
    makeServerError,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { useService } from "@web/core/utils/hooks";

import { Record } from "@web/model/record";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { CharField } from "@web/views/fields/char/char_field";
import { Field } from "@web/views/fields/field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

class Foo extends models.Model {
    foo = fields.Char();

    _records = [
        { id: 1, foo: "yop" },
        { id: 2, foo: "blip" },
        { id: 3, foo: "gnap" },
        { id: 4, foo: "abc" },
        { id: 5, foo: "blop" },
    ];
}

defineModels([Foo]);

test(`display a simple field`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <div class="root">
                <Record resModel="'foo'" resId="1" fieldNames="['foo']" t-slot-scope="data">
                    <span>hello</span>
                    <Field name="'foo'" record="data.record"/>
                </Record>
            </div>
        `;
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect(queryFirst`.root`).toHaveOuterHTML(`
        <div class="root">
            <span>hello</span>
            <div name="foo" class="o_field_widget o_field_char">
                <span>yop</span>
            </div>
        </div>
    `);
    expect.verifySteps([
        "/web/dataset/call_kw/foo/fields_get",
        "/web/dataset/call_kw/foo/web_read",
    ]);
});

test(`can be updated with different resId`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'foo'" resId="state.resId" fieldNames="['foo']" t-slot-scope="data">
                <Field name="'foo'" record="data.record"/>
                <button class="my-btn" t-on-click="() => this.state.resId++">Next</button>
            </Record>
        `;

        setup() {
            this.state = useState({
                resId: 1,
            });
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect.verifySteps([
        "/web/dataset/call_kw/foo/fields_get",
        "/web/dataset/call_kw/foo/web_read",
    ]);
    expect(`.o_field_char:contains(yop)`).toHaveCount(1);

    await contains(`button.my-btn`).click();
    expect(`.o_field_char:contains(blip)`).toHaveCount(1);
    expect.verifySteps(["/web/dataset/call_kw/foo/web_read"]);
});

test(`can be receive a context as props`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <div class="root">
                <Record resModel="'foo'" fieldNames="['foo']" context="{ test: 4 }" t-slot-scope="data">
                    <Field name="'foo'" record="data.record"/>
                </Record>
            </div>
        `;
    }

    onRpc("onchange", ({ kwargs }) => {
        expect.step(`onchange`);
        expect(kwargs.context).toEqual({
            allowed_company_ids: [1],
            lang: "en",
            test: 4,
            tz: "taht",
            uid: 7,
        });
    });
    await mountWithCleanup(Parent);
    expect.verifySteps(["onchange"]);
});

test(`predefined fields and values`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "char",
                },
                bar: {
                    name: "bar",
                    type: "boolean",
                },
            };
            this.values = {
                foo: "abc",
                bar: true,
            };
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect.verifySteps([]);
    expect(`.o_field_widget input`).toHaveValue("abc");
});

test(`Record with onRootLoaded props`, async () => {
    let record;
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" t-slot-scope="data" hooks="hooks">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "char",
                },
            };
            this.hooks = {
                onRootLoaded: this.onRootLoaded.bind(this),
            };
        }

        onRootLoaded(root) {
            expect.step("onRootLoaded");
            record = root;
        }
    }

    await mountWithCleanup(Parent);
    expect.verifySteps(["onRootLoaded"]);
    expect(record.data.foo).toBe("");
    await contains(`[name='foo'] input`).edit("coucou");
    expect(record.data.foo).toBe("coucou");
});

test(`Record with onRecordChanged props`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data" hooks="hooks">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "char",
                },
                bar: {
                    name: "bar",
                    type: "boolean",
                },
            };
            this.values = {
                foo: "abc",
                bar: true,
            };
            this.hooks = {
                onRecordChanged: this.onRecordChanged.bind(this),
            };
        }

        onRecordChanged(record, changes) {
            expect.step("record changed");
            expect(record.model.constructor.name).toBe("StandaloneRelationalModel");
            expect(changes).toEqual({ foo: "753" });
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect(`[name='foo'] input`).toHaveValue("abc");

    await contains(`[name='foo'] input`).edit("753");
    expect.verifySteps(["record changed"]);
    expect(`[name='foo'] input`).toHaveValue("753");
});

test(`Record with onWillSaveRecord and onRecordSavedProps`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'foo'" resId="1" fieldNames="['foo']" mode="'edit'" t-slot-scope="data" hooks="hooks">
                <button class="save" t-on-click="() => data.record.save()">Save</button>
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.hooks = {
                onRecordSaved: this.onRecordSaved.bind(this),
                onWillSaveRecord: this.onWillSaveRecord.bind(this),
            };
        }

        onRecordSaved(record) {
            expect.step("onRecordSaved");
        }

        onWillSaveRecord(record) {
            expect.step("onWillSaveRecord");
        }
    }

    onRpc(({ method }) => expect.step(method));
    await mountWithCleanup(Parent);

    await contains(`[name='foo'] input`).edit("abc");
    await contains(`button.save`).click();
    expect.verifySteps(["fields_get", "web_read", "onWillSaveRecord", "web_save", "onRecordSaved"]);
});

test(`can access record changes`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" t-slot-scope="data">
                <button class="do_something" t-on-click="() => doSomething(data.record)">
                    Do something
                </button>
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        async doSomething(record) {
            expect.step(`do something with ${JSON.stringify(await record.getChanges())}`);
        }
    }

    await mountWithCleanup(Parent);

    await contains(".do_something").click();
    expect.verifySteps([`do something with {"foo":false}`]);

    await contains(".o_field_widget[name=foo] input").edit("some value");
    await contains(".do_something").click();
    expect.verifySteps([`do something with {"foo":"some value"}`]);
});

test.tags("desktop");
test(`handles many2one fields: value is an object`, async () => {
    class Bar extends models.Model {
        name = fields.Char();

        _records = [
            { id: 1, name: "bar1" },
            { id: 3, name: "abc" },
        ];
    }
    defineModels([Bar]);

    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Many2OneField };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data" hooks="hooks">
                <Many2OneField name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "many2one",
                    relation: "bar",
                },
            };
            this.values = {
                foo: { id: 1, display_name: "bar1" },
            };
            this.hooks = {
                onRecordChanged: this.onRecordChanged.bind(this),
            };
        }

        onRecordChanged(record, changes) {
            expect.step("record changed");
            expect(changes).toEqual({ foo: 3 });
            expect(record.data).toEqual({ foo: { id: 3, display_name: "abc" } });
            expect(record.data.foo.id).toBe(3);
            expect(record.data.foo.display_name).toBe("abc");
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect.verifySteps([]);
    expect(`.o_field_many2one_selection input`).toHaveValue("bar1");

    await contains(`.o_field_many2one_selection input`).edit("abc", { confirm: false });
    await runAllTimers();
    expect.verifySteps(["/web/dataset/call_kw/bar/web_name_search"]);

    await contains(`.o-autocomplete--dropdown-item a:eq(0)`).click();
    expect.verifySteps(["record changed"]);
    expect(`.o_field_many2one_selection input`).toHaveValue("abc");
});

test.tags("desktop");
test(`handles many2one fields: value is a pair id, display_name`, async () => {
    class Bar extends models.Model {
        name = fields.Char();

        _records = [
            { id: 1, name: "bar1" },
            { id: 3, name: "abc" },
        ];
    }
    defineModels([Bar]);

    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Many2OneField };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data" hooks="hooks">
                <Many2OneField name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "many2one",
                    relation: "bar",
                },
            };
            this.values = {
                foo: { id: 1, display_name: "bar1" },
            };
            this.hooks = {
                onRecordChanged: this.onRecordChanged.bind(this),
            };
        }

        onRecordChanged(record, changes) {
            expect.step("record changed");
            expect(changes).toEqual({ foo: 3 });
            expect(record.data).toEqual({ foo: { id: 3, display_name: "abc" } });
            expect(record.data.foo.id).toBe(3);
            expect(record.data.foo.display_name).toBe("abc");
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect.verifySteps([]);
    expect(`.o_field_many2one_selection input`).toHaveValue("bar1");

    await contains(`.o_field_many2one_selection input`).edit("abc", { confirm: false });
    await runAllTimers();
    expect.verifySteps(["/web/dataset/call_kw/bar/web_name_search"]);

    await contains(`.o-autocomplete--dropdown-item a:eq(0)`).click();
    expect.verifySteps(["record changed"]);
    expect(`.o_field_many2one_selection input`).toHaveValue("abc");
});

test(`handles many2one fields: value is an id`, async () => {
    class Bar extends models.Model {
        name = fields.Char();

        _records = [
            { id: 1, name: "bar1" },
            { id: 3, name: "abc" },
        ];
    }
    defineModels([Bar]);

    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Many2OneField };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data">
                <Many2OneField name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "many2one",
                    relation: "bar",
                },
            };
            this.values = {
                foo: 1,
            };
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect.verifySteps(["/web/dataset/call_kw/bar/web_read"]);
    expect(`.o_field_many2one_selection input`).toHaveValue("bar1");
});

test(`handles many2one fields: value is an object with id only`, async () => {
    class Bar extends models.Model {
        name = fields.Char();

        _records = [
            { id: 1, name: "bar1" },
            { id: 3, name: "abc" },
        ];
    }
    defineModels([Bar]);

    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Many2OneField };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data">
                <Many2OneField name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "many2one",
                    relation: "bar",
                },
            };
            this.values = {
                foo: { id: 1 },
            };
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect.verifySteps(["/web/dataset/call_kw/bar/web_read"]);
    expect(`.o_field_many2one_selection input`).toHaveValue("bar1");
});

test(`handles x2many fields`, async () => {
    class Tag extends models.Model {
        name = fields.Char();

        _records = [
            { id: 1, name: "bug" },
            { id: 3, name: "ref" },
        ];
    }
    defineModels([Tag]);

    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Many2ManyTagsField };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['tags']" activeFields="activeFields" fields="fields" values="values" t-slot-scope="data">
                <Many2ManyTagsField name="'tags'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.activeFields = {
                tags: {
                    related: {
                        activeFields: {
                            display_name: {},
                        },
                        fields: {
                            display_name: { name: "display_name", type: "string" },
                        },
                    },
                },
            };
            this.fields = {
                tags: {
                    name: "Tags",
                    type: "many2many",
                    relation: "tag",
                },
            };
            this.values = {
                tags: [1, 3],
            };
        }
    }

    onRpc(({ route }) => expect.step(route));
    await mountWithCleanup(Parent);
    expect.verifySteps(["/web/dataset/call_kw/tag/web_read"]);
    expect(queryAllTexts`.o_tag`).toEqual(["bug", "ref"]);
});

test(`supports passing dynamic values -- full control to the user of Record`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <Record resModel="'foo'" fieldNames="['foo']" fields="fields" values="{ foo: values.foo }" t-slot-scope="data" hooks="hooks">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "char",
                },
                bar: {
                    name: "bar",
                    type: "boolean",
                },
            };
            this.values = useState({
                foo: "abc",
                bar: true,
            });
            this.hooks = {
                onRecordChanged: this.onRecordChanged.bind(this),
            };
        }

        onRecordChanged(record, changes) {
            expect.step("record changed");
            expect(record.model.constructor.name).toBe("StandaloneRelationalModel");
            expect(changes).toEqual({ foo: "753" });
            this.values.foo = 357;
        }
    }

    onRpc(() => {
        throw new makeServerError({ message: "should not do any rpc" });
    });
    await mountWithCleanup(Parent);
    expect(`[name='foo'] input`).toHaveValue("abc");

    await contains(`[name='foo'] input`).edit("753");
    expect.verifySteps(["record changed"]);
    expect(`[name='foo'] input`).toHaveValue("357");
});

test(`can switch records`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <a id="increment" t-on-click="() => state.num++" t-esc="state.num"/>
            <a id="next" t-on-click="next">NEXT</a>
            <Record resId="state.currentId" resModel="'foo'" fieldNames="['foo']" fields="fields" t-slot-scope="data">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.state = useState({ currentId: 1, num: 0 });
        }

        next() {
            this.state.currentId = 5;
            this.state.num++;
        }
    }

    onRpc("web_read", ({ method, args, kwargs }) => {
        expect.step(
            `${method} : ${JSON.stringify(args[0])} - ${JSON.stringify(kwargs.specification)}`
        );
    });
    await mountWithCleanup(Parent);
    expect.verifySteps([`web_read : [1] - {"foo":{}}`]);
    expect(`#increment`).toHaveText("0");
    expect(`div[name='foo']`).toHaveText("yop");

    await contains(`#increment`).click();
    // No reload when a render from upstream comes
    expect.verifySteps([]);
    expect(`#increment`).toHaveText("1");
    expect(`div[name='foo']`).toHaveText("yop");

    await contains(`#next`).click();
    expect.verifySteps([`web_read : [5] - {"foo":{}}`]);
    expect(`#increment`).toHaveText("2");
    expect(`div[name='foo']`).toHaveText("blop");
});

test(`can switch records with values`, async () => {
    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <a id="next" t-on-click="next">NEXT</a>
            <Record resId="state.currentId" resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data">
                <Field name="'foo'" record="data.record"/>
            </Record>
        `;

        setup() {
            this.fields = {
                foo: {
                    name: "foo",
                    type: "char",
                },
                bar: {
                    name: "bar",
                    type: "boolean",
                },
            };
            this.values = {
                foo: "abc",
                bar: true,
            };
            this.state = useState({ currentId: 99 });
        }

        next() {
            this.state.currentId = 100;
            this.values = {
                foo: "def",
                bar: false,
            };
        }
    }

    onRpc(({ route }) => expect.step(route));
    const parent = await mountWithCleanup(Parent);
    const _record = findComponent(
        parent,
        (component) => component instanceof Record.components._Record
    );

    // No load since the values are provided to the record
    expect.verifySteps([]);
    // First values are loaded
    expect(`div[name='foo']`).toHaveText("abc");
    // Verify that the underlying _Record Model root has the specified resId
    expect(_record.model.root.resId).toBe(99);

    await contains(`#next`).click();
    // Still no load.
    expect.verifySteps([]);
    // Second values are loaded
    expect(`div[name='foo']`).toHaveText("def");
    // Verify that the underlying _Record Model root has the updated resId
    expect(_record.model.root.resId).toBe(100);
});

test(`faulty useRecordObserver in widget`, async () => {
    patchWithCleanup(CharField.prototype, {
        setup() {
            super.setup();
            useRecordObserver((record, props) => {
                throw new Error("faulty record observer");
            });
        },
    });

    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <t t-if="!state.error">
                <Record resId="1" resModel="'foo'" fieldNames="['foo']" fields="fields" values="values" t-slot-scope="data">
                    <Field name="'foo'" record="data.record"/>
                </Record>
            </t>
            <t t-else="">
                <div class="error" t-esc="state.error.message"/>
            </t>
        `;

        setup() {
            this.state = useState({ error: false });
            onError((error) => {
                this.state.error = error;
            });
        }
    }

    await mountWithCleanup(Parent);
    expect(`.error`).toHaveText(
        `The following error occurred in onWillStart: "faulty record observer"`
    );
});

test(`don't duplicate a useRecordObserver effect when switching back and forth between the same records`, async () => {
    patchWithCleanup(CharField.prototype, {
        setup() {
            super.setup();
            useRecordObserver((record) => {
                expect.step(`foo: ${record.data.foo}`);
            });
        },
    });

    class StandaloneRelationalModel extends RelationalModel {
        constructor(env, params, services) {
            params = {
                config: {
                    resModel: "foo",
                    fieldNames: ["foo"],
                    fields: { foo: { name: "foo", type: "char" } },
                    activeFields: { foo: {} },
                    isMonoRecord: true,
                },
                hooks: {
                    onRecordSaved: () => {},
                    onWillSaveRecord: () => {},
                    onRecordChanged: () => {},
                },
            };
            super(env, params, services);
        }
        load(params = {}) {
            const data = params.values;
            const config = this._getNextConfig(this.config, params);
            this.root = this._createRoot(config, data);
            this.config = config;
            return;
        }
    }

    class Parent extends Component {
        static props = ["*"];
        static components = { Record, Field };
        static template = xml`
            <a id="setRecord" t-on-click="setRecord">SET</a>
            <a id="toggleRecord" t-on-click="toggleRecord">TOGGLE</a>
            <Field name="'foo'" record="records[state.recordIndex]"/>
        `;

        setup() {
            this.orm = useService("orm");
            const services = { orm: this.orm };
            const model = new StandaloneRelationalModel(this.env, {}, services);
            model.load({ resId: 1, values: { foo: "abc" } });
            const record1 = model.root;
            model.load({ resId: 2, values: { foo: "def" } });
            const record2 = model.root;
            this.records = [record1, record2];
            this.state = useState({ recordIndex: 0 });
        }

        setRecord() {
            this.records[this.state.recordIndex].update({ foo: "ghi" });
        }

        toggleRecord() {
            this.state.recordIndex = (this.state.recordIndex + 1) % 2;
        }
    }

    await mountWithCleanup(Parent);
    expect.verifySteps(["foo: abc"]);
    await contains("#toggleRecord").click();
    expect.verifySteps(["foo: def"]);
    await contains("#toggleRecord").click();
    expect.verifySteps(["foo: abc"]);
    await contains("#setRecord").click();
    expect.verifySteps(["foo: ghi"]);
});
