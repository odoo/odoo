import {
    advanceTime,
    after,
    animationFrame,
    click,
    expect,
    hover,
    queryAll,
    queryFirst,
    queryOne,
    queryText,
    test,
} from "@odoo/hoot";
import { Component, onWillStart, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { useService } from "@web/core/utils/hooks";

import { currencies } from "@web/core/currency";
import { registry } from "@web/core/registry";
import { parseXML } from "@web/core/utils/xml";
import { Card } from "@web/views/card/card";
import { CardCompiler } from "@web/views/card/card_compiler";
import { ViewButton } from "@web/views/view_button/view_button";

const fieldRegistry = registry.category("fields");
const viewWidgetRegistry = registry.category("view_widgets");

async function mountCard({
    resModel,
    resId,
    arch,
    context,
    openRecord,
    deleteRecord,
    archiveRecord,
    readonly,
    Compiler,
} = {}) {
    class Parent extends Component {
        static template = xml`
            <div style="width: 300px" class="m-2 p-2 border bg-white">
                <Card t-props="this.cardProps"/>
            </div>`;
        static components = { Card };

        setup() {
            const orm = useService("orm");
            onWillStart(async () => {
                this.fields = await orm.call(resModel, "fields_get", []);
            });
        }

        get cardProps() {
            const props = {
                card: parseXML(arch),
                resModel,
                resId,
                fields: this.fields,
                // optional props
                readonly: readonly || false,
                openRecord: openRecord,
                deleteRecord: deleteRecord,
                archiveRecord: archiveRecord,
                context: context,
                Compiler: Compiler,
            };
            return props;
        }
    }

    return mountWithCleanup(Parent);
}

class Partner extends models.Model {
    _name = "partner";
    _rec_name = "foo";

    foo = fields.Char();
    bar = fields.Boolean();
    sequence = fields.Integer();
    int_field = fields.Integer({ aggregator: "sum", sortable: true });
    float_field = fields.Float({ aggregator: "sum" });
    product_id = fields.Many2one({ relation: "product" });
    category_ids = fields.Many2many({ relation: "category" });
    date = fields.Date();
    datetime = fields.Datetime();
    state = fields.Selection({
        type: "selection",
        selection: [
            ["abc", "ABC"],
            ["def", "DEF"],
            ["ghi", "GHI"],
        ],
    });

    _records = [
        {
            id: 1,
            foo: "yop",
            bar: true,
            int_field: 10,
            float_field: 0.4,
            product_id: 3,
            category_ids: [],
            state: "abc",
        },
        {
            id: 2,
            foo: "blip",
            bar: true,
            int_field: 9,
            category_ids: [],
        },
        {
            id: 3,
            foo: "blip",
            bar: false,
            int_field: -4,
            category_ids: [],
        },
    ];
}

class Product extends models.Model {
    _name = "product";

    name = fields.Char();

    _records = [
        { id: 3, name: "hello" },
        { id: 5, name: "xmo" },
    ];
}

class Category extends models.Model {
    _name = "category";

    name = fields.Char();
    color = fields.Integer();

    _records = [
        { id: 6, name: "gold", color: 2 },
        { id: 7, name: "silver", color: 5 },
    ];
}

defineModels([Partner, Product, Category]);

test("generic tags are case insensitive", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <Div class="test">Hello</Div>
                    </t>
                </templates>
            </card>`,
    });

    expect("div.test").toHaveCount(1);
});

test("float fields are formatted properly without using a widget", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="float_field" digits="[0,5]"/>
                        <field name="float_field" digits="[0,3]"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveText("0.40000\n0.400");
});

test("field with widget and attributes in card", async () => {
    const myField = {
        component: class MyField extends Component {
            static template = xml`<span/>`;
            static props = ["*"];
            setup() {
                expect(this.props.attrs).toEqual({
                    name: "int_field",
                    widget: "my_field",
                    str: "some string",
                    bool: "true",
                    num: "4.5",
                    field_id: "int_field_0",
                });
            }
        },
        extractProps: ({ attrs }) => ({ attrs }),
    };
    fieldRegistry.add("my_field", myField);
    after(() => fieldRegistry.remove("my_field"));

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <field name="int_field" widget="my_field"
                            str="some string"
                            bool="true"
                            num="4.5"
                        />
                    </t>
                </templates>
            </card>`,
    });
});

test("card with integer field with human_readable option", async () => {
    Partner._records[0].int_field = 5 * 1000 * 1000;
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="int_field" options="{'human_readable': true}"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveText("5M");
    expect(".o_field_widget").toHaveCount(0);
});

test("context can be used in card template", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field t-if="context.some_key" name="foo"/>
                    </t>
                </templates>
            </card>`,
        context: { some_key: 1 },
    });

    expect(".o_card_record").toHaveCount(1);
    expect(".o_card_record span:contains(yop)").toHaveCount(1);
});

test("card with sub-template", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <t t-call="another-template"/>
                    </t>
                    <t t-name="another-template">
                        <field name="foo"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveText("yop");
});

test("card with t-set outside card", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="int_field"/>
                <templates>
                    <t t-name="card">
                        <t t-set="x" t-value="record.int_field.value"/>
                        <div>
                            <t t-out="x"/>
                        </div>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveText("10");
});

test("card with t-if/t-else on field", async () => {
    const arch = `
        <card>
            <templates>
                <t t-name="card">
                    <field t-if="record.int_field.value > -1" name="int_field"/>
                    <t t-else="">Negative value</t>
                </t>
            </templates>
        </card>`;

    await mountCard({ resModel: "partner", resId: 1, arch });
    expect(queryAll(".o_card_record")[0]).toHaveText("10");

    await mountCard({ resModel: "partner", resId: 3, arch });
    expect(queryAll(".o_card_record")[1]).toHaveText("Negative value");
});

test("card with t-if/t-else on field with widget", async () => {
    const arch = `
        <card>
            <templates>
                <t t-name="card">
                    <field t-if="record.int_field.value > -1" name="int_field" widget="integer"/>
                    <t t-else="">Negative value</t>
                </t>
            </templates>
        </card>`;

    await mountCard({ resModel: "partner", resId: 1, arch });
    expect(queryAll(".o_card_record")[0]).toHaveText("10");

    await mountCard({ resModel: "partner", resId: 3, arch });
    expect(queryAll(".o_card_record")[1]).toHaveText("Negative value");
});

test("field with widget and dynamic attributes in card", async () => {
    const myField = {
        component: class MyField extends Component {
            static template = xml`<span/>`;
            static props = ["*"];
        },
        extractProps: ({ attrs }) => {
            expect.step(
                `${attrs["dyn-bool"]}/${attrs["interp-str"]}/${attrs["interp-str2"]}/${attrs["interp-str3"]}`
            );
        },
    };
    fieldRegistry.add("my_field", myField);
    after(() => fieldRegistry.remove("my_field"));

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <field name="int_field" widget="my_field"
                            t-att-dyn-bool="record.foo.value.length > 3"
                            t-attf-interp-str="hello {{record.foo.value}}"
                            t-attf-interp-str2="hello #{record.foo.value} !"
                            t-attf-interp-str3="hello {{record.foo.value}} }}"
                        />
                    </t>
                </templates>
            </card>`,
    });
    expect.verifySteps(["false/hello yop/hello yop !/hello yop }}"]);
});

test("view button and string interpolated attribute in card", async () => {
    patchWithCleanup(ViewButton.prototype, {
        setup() {
            super.setup();
            expect.step(`[${this.props.clickParams["name"]}] className: '${this.props.className}'`);
        },
    });

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <a name="one" type="object" class="hola"/>
                        <a name="two" type="object" class="hola" t-attf-class="hello"/>
                        <a name="sri" type="object" class="hola" t-attf-class="{{record.foo.value}}"/>
                        <a name="foa" type="object" class="hola" t-attf-class="{{record.foo.value}} olleh"/>
                        <a name="fye" type="object" class="hola" t-attf-class="hello {{record.foo.value}}"/>
                    </t>
                </templates>
            </card>`,
    });
    expect.verifySteps([
        "[one] className: 'hola oe_kanban_action'",
        "[two] className: 'hola oe_kanban_action hello'",
        "[sri] className: 'hola oe_kanban_action yop'",
        "[foa] className: 'hola oe_kanban_action yop olleh'",
        "[fye] className: 'hola oe_kanban_action hello yop'",
    ]);
});

test("buttons with modifiers", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="foo"/>
                <field name="bar"/>
                <field name="state"/>
                <templates>
                    <div t-name="card">
                        <button class="o_btn_test_1" type="object" name="a1" invisible="foo != 'yop'"/>
                        <button class="o_btn_test_2" type="object" name="a2" invisible="bar and state not in ['abc', 'def']"/>
                    </div>
                </templates>
            </card>`,
    });

    expect(".o_btn_test_1").toHaveCount(1, { message: "card should have one button of type 1" });
    expect(".o_btn_test_2").toHaveCount(1, { message: "card should have one button of type 2" });
});

test("support styling of anchor tags with action type", async () => {
    expect.assertions(3);

    mockService("action", {
        doActionButton(action) {
            expect(action.name).toBe("42");
        },
    });

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <a type="action" name="42" class="btn-primary" style="margin-left: 10px"><i class="oi oi-arrow-right"/> Click me !</a>
                    </div>
                </templates>
            </card>`,
    });

    await click("a[type='action']");
    expect("a[type='action']:first").toHaveClass("btn-primary");
    expect(queryFirst("a[type='action']").style.marginLeft).toBe("10px");
});

test("button executes action and reloads", async () => {
    onRpc("web_read", () => expect.step("web_read"));

    let count = 0;
    mockService("action", {
        async doActionButton({ onClose }) {
            count++;
            await animationFrame();
            onClose();
        },
    });

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <div t-name="card">
                        <field name="foo"/>
                        <button type="object" name="a1" class="a1">
                            A1
                        </button>
                    </div>
                </templates>
            </card>`,
    });

    // Clear the initial web_read from setup
    expect.verifySteps(["web_read"]);

    expect("button.a1").toHaveCount(1);
    expect("button.a1").not.toHaveAttribute("disabled");

    await click("button.a1");

    expect("button.a1").toHaveAttribute("disabled");

    await animationFrame();

    expect("button.a1").not.toHaveAttribute("disabled");
    expect(count).toBe(1, { message: "should have triggered an execute action only once" });
    // the record should be reloaded after executing a button action
    expect.verifySteps(["web_read"]);
});

test("field tag with modifiers but no widget", async () => {
    const arch = `
        <card>
            <templates>
                <t t-name="card">
                    <field name="foo" invisible="id == 1"/>
                </t>
            </templates>
        </card>`;

    await mountCard({ resModel: "partner", resId: 1, arch });
    expect(queryAll(".o_card_record")[0]).toHaveText("");

    await mountCard({ resModel: "partner", resId: 2, arch });
    expect(queryAll(".o_card_record")[1]).toHaveText("blip");
});

test("field tag with widget and class attributes", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="char" class="hi"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_field_widget.hi").toHaveCount(1);
});

test("rendering date and datetime (value)", async () => {
    Partner._records[0].date = "2017-01-25";
    Partner._records[1].datetime = "2016-12-12 10:55:05";

    const arch = `
        <card>
            <templates>
                <t t-name="card">
                    <field class="date" name="date"/>
                    <field class="datetime" name="datetime"/>
                </t>
            </templates>
        </card>`;

    await mountCard({ resModel: "partner", resId: 1, arch });
    expect(queryAll(".o_card_record")[0].querySelector(".date")).toHaveText("Jan 25, 2017");

    await mountCard({ resModel: "partner", resId: 2, arch });
    expect(queryAll(".o_card_record")[1].querySelector(".datetime")).toHaveText(
        "Dec 12, 2016, 11:55 AM"
    );
});

test("rendering date and datetime (raw value)", async () => {
    Partner._records[0].date = "2017-01-25";
    Partner._records[1].datetime = "2016-12-12 10:55:05";

    const arch = `
        <card>
            <field name="date"/>
            <field name="datetime"/>
            <templates>
                <t t-name="card">
                    <span class="date" t-out="record.date.raw_value"/>
                    <span class="datetime" t-out="record.datetime.raw_value"/>
                </t>
            </templates>
        </card>`;

    await mountCard({ resModel: "partner", resId: 1, arch });
    expect(queryAll(".o_card_record")[0].querySelector(".date")).toHaveText(
        "2017-01-25T00:00:00.000+01:00"
    );

    await mountCard({ resModel: "partner", resId: 2, arch });
    expect(queryAll(".o_card_record")[1].querySelector(".datetime")).toHaveText(
        "2016-12-12T11:55:05.000+01:00"
    );
});

test("rendering many2one (value)", async () => {
    Partner._records[1].product_id = false;

    const arch = `
        <card>
            <templates>
                <t t-name="card">
                    <field name="product_id" class="product_id"/>
                </t>
            </templates>
        </card>`;

    await mountCard({ resModel: "partner", resId: 1, arch });
    expect(queryAll(".o_card_record")[0]).toHaveText("hello");

    await mountCard({ resModel: "partner", resId: 2, arch });
    expect(queryAll(".o_card_record")[1]).toHaveText("");
});

test("rendering many2one (raw value)", async () => {
    Partner._records[1].product_id = false;

    const arch = `
        <card>
            <field name="product_id"/>
            <templates>
                <t t-name="card">
                    <span class="product_id" t-out="record.product_id.raw_value"/>
                </t>
            </templates>
        </card>`;

    await mountCard({ resModel: "partner", resId: 1, arch });
    expect(queryAll(".o_card_record")[0]).toHaveText("3");

    await mountCard({ resModel: "partner", resId: 2, arch });
    expect(queryAll(".o_card_record")[1]).toHaveText("false");
});

test("evaluate conditions on relational fields", async () => {
    Partner._records[0].product_id = false;

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="product_id"/>
                <field name="category_ids"/>
                <templates>
                    <t t-name="card">
                        <button t-if="!record.product_id.raw_value" class="btn_a">A</button>
                        <button t-if="!record.category_ids.raw_value.length" class="btn_b">B</button>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveCount(1);
    expect(".btn_a").toHaveCount(1, { message: "should show the 'Action' button" });
    expect(".btn_b").toHaveCount(1, { message: "should show the 'B' button" });
});

test("properly evaluate more complex domains", async () => {
    await mountCard({
        resModel: "partner",
        resId: 3,
        arch: `
            <card>
                <field name="bar"/>
                <field name="category_ids"/>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <button type="object" invisible="bar or category_ids" class="btn btn-primary float-end" name="arbitrary">Join</button>
                    </t>
                </templates>
            </card>`,
    });

    expect("button.float-end.oe_kanban_action").toHaveCount(1, {
        message: "button should be visible",
    });
});

test("many2many_tags in card views", async () => {
    Partner._records[0].category_ids = [6, 7];
    Category._records.push({
        id: 8,
        name: "hello",
        color: 0,
    });

    onRpc("web_save", () => expect.step("web_save"));

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="category_ids" widget="many2many_tags" options="{'color_field': 'color', 'on_tag_click': 'edit_color'}"/>
                        <field name="foo"/>
                        <field name="state" widget="priority"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_field_many2many_tags .o_tag").toHaveCount(2, {
        message: "record should contain 2 tags",
    });
    expect(".o_tag.o_tag_color_2").toHaveCount(1, {
        message: "first tag should have color 2",
    });

    // Write on the record using the priority widget to trigger a re-render in readonly
    await contains(".o_priority_star:first-child").click();

    expect.verifySteps(["web_save"]);
    expect(".o_field_many2many_tags .o_tag").toHaveCount(2, {
        message: "record should still contain 2 tags",
    });
    const tags = queryAll(".o_tag");
    expect(tags[0]).toHaveText("gold");
    expect(tags[1]).toHaveText("silver");
});

test("priority field should not be editable when missing access rights", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <field name="state" widget="priority"/>
                    </t>
                </templates>
            </card>`,
        readonly: true,
    });
    expect(".o_card_record .o_priority .fa-star-o").toHaveCount(2);
    await contains(".o_card_record .o_priority_star:first-child").click();
    expect(".o_card_record .o_priority .fa-star-o").toHaveCount(2);
});

test("can use JSON in card template", async () => {
    Partner._records = [{ id: 1, foo: '["g", "e", "d"]' }];

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="foo"/>
                <templates>
                    <t t-name="card">
                        <div>
                            <span t-foreach="JSON.parse(record.foo.raw_value)" t-as="v" t-key="v_index" t-out="v"/>
                        </div>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveCount(1);
    expect(".o_card_record span").toHaveCount(3);
    expect(".o_card_record").toHaveText("ged");
});

test("Missing t-key is automatically filled with a warning", async () => {
    patchWithCleanup(console, { warn: () => expect.step("warning") });

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <div>
                            <span t-foreach="[1, 2, 3]" t-as="i" t-out="i" />
                        </div>
                    </t>
                </templates>
            </card>`,
    });

    expect.verifySteps(["warning"]);
    expect(queryOne(".o_card_record")).toHaveText("123");
});

test("Allow use of 'editable'/'deletable' in card", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <div t-name="card">
                        <button t-if="widget.editable">EDIT</button>
                        <button t-if="widget.deletable">DELETE</button>
                    </div>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveText("EDITDELETE");
});

test("basic support for widgets (being Owl Components)", async () => {
    class MyComponent extends Component {
        static template = xml`<div t-att-class="this.props.class" t-out="this.value"/>`;
        static props = ["*"];
        get value() {
            return JSON.stringify(this.props.record.data);
        }
    }
    const myComponent = {
        component: MyComponent,
    };
    viewWidgetRegistry.add("test", myComponent);
    after(() => viewWidgetRegistry.remove("test"));

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                        <widget name="test"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(queryOne(".o_card_record").querySelector(".o_widget")).toHaveText('{"foo":"yop"}');
});

test("card record: record value should be updated", async () => {
    class MyComponent extends Component {
        static template = xml`<div><button t-on-click="this.onClick">CLick</button></div>`;
        static props = ["*"];
        onClick() {
            this.props.record.update({ foo: "yolo" });
        }
    }
    const myComponent = {
        component: MyComponent,
    };
    viewWidgetRegistry.add("test", myComponent);
    after(() => viewWidgetRegistry.remove("test"));

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="foo" class="foo"/>
                        <widget name="test"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(queryText(".foo", { root: queryOne(".o_card_record") })).toBe("yop");

    await click(queryOne("button", { root: queryOne(".o_card_record") }));
    await animationFrame();
    await animationFrame();

    expect(queryText(".foo", { root: queryOne(".o_card_record") })).toBe("yolo");
});

test("card view with boolean field", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="bar"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record input:disabled").toHaveCount(1);
    expect(".o_card_record input:checked").toHaveCount(1);
});

test("card view with boolean widget", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="bar" widget="boolean"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(
        queryAll("div.o_field_boolean .o-checkbox", { root: queryOne(".o_card_record") })
    ).toHaveCount(1);
});

test("card view with boolean toggle widget", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="bar" widget="boolean_toggle"/>
                    </t>
                </templates>
            </card>`,
    });
    expect(queryOne(".o_card_record").querySelector("[name='bar'] input")).toBeChecked();

    await click("[name='bar'] input");
    await animationFrame();

    expect(queryOne(".o_card_record").querySelector("[name='bar'] input")).not.toBeChecked();
});

test("card view with monetary and currency fields without widget", async () => {
    class Currency extends models.Model {
        _name = "res.currency";

        name = fields.Char();
        symbol = fields.Char();
        position = fields.Selection({
            selection: [["before", "B"]],
        });

        _records = [{ id: 1, name: "USD", symbol: "$", position: "before" }];
    }
    defineModels([Currency]);
    Partner._fields.salary = fields.Monetary({ aggregator: "sum", currency_field: "currency_id" });
    Partner._fields.currency_id = fields.Many2one({ relation: "res.currency" });
    Partner._records[0].salary = 1750;
    Partner._records[0].currency_id = 1;

    const mockedCurrencies = {};
    for (const record of Currency._records) {
        mockedCurrencies[record.id] = record;
    }
    patchWithCleanup(currencies, mockedCurrencies);

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <field name="currency_id"/>
                <templates>
                    <t t-name="card">
                        <field name="salary"/>
                    </t>
                </templates>
            </card>`,
    });

    expect(".o_card_record").toHaveText("$ 1,750.00");
});

test("card widget can extract props from attrs", async () => {
    class TestWidget extends Component {
        static template = xml`<div class="o-test-widget-option" t-out="this.props.title"/>`;
        static props = ["*"];
    }
    const testWidget = {
        component: TestWidget,
        extractProps: ({ attrs }) => ({
            title: attrs.title,
        }),
    };
    viewWidgetRegistry.add("widget_test_option", testWidget);
    after(() => viewWidgetRegistry.remove("widget_test_option"));

    await mountCard({
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <widget name="widget_test_option" title="Widget with Option"/>
                    </t>
                </templates>
            </card>`,
        resModel: "partner",
    });

    expect(".o-test-widget-option").toHaveCount(1);
    expect(".o-test-widget-option:first").toHaveText("Widget with Option");
});

test("fieldDependencies support for fields", async () => {
    const customField = {
        component: class CustomField extends Component {
            static template = xml`<span t-out="this.props.record.data.int_field"/>`;
            static props = ["*"];
        },
        fieldDependencies: [{ name: "int_field", type: "integer" }],
    };
    fieldRegistry.add("custom_field", customField);
    after(() => fieldRegistry.remove("custom_field"));

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="custom_field"/>
                    </t>
                </templates>
            </card>`,
    });

    expect("[name=foo] span:first").toHaveText("10");
});

test("fieldDependencies support for fields: dependence on a relational field", async () => {
    const customField = {
        component: class CustomField extends Component {
            static template = xml`<span t-out="this.props.record.data.product_id.display_name"/>`;
            static props = ["*"];
        },
        fieldDependencies: [{ name: "product_id", type: "many2one", relation: "product" }],
    };
    fieldRegistry.add("custom_field", customField);
    after(() => fieldRegistry.remove("custom_field"));

    onRpc("web_read", () => expect.step("web_read"));

    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="custom_field"/>
                    </t>
                </templates>
            </card>`,
    });

    expect("[name=foo] span:first").toHaveText("hello");
    expect.verifySteps(["web_read"]);
});

test("Can't use CardRenderer implementation details in arch", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <div>
                            <t t-out="__owl__"/>
                            <t t-out="props"/>
                            <t t-out="env"/>
                            <t t-out="render"/>
                        </div>
                    </t>
                </templates>
            </card>`,
    });
    expect(queryOne(".o_card_record")).toHaveInnerHTML("<div></div>");
});

test("card with basic and custom compiler, same arch", async () => {
    // In this test, the exact same arch will be rendered by 2 different card renderers:
    // once with the basic one, and once with a custom renderer having a custom compiler. The
    // purpose of the test is to ensure that the template is compiled twice, once by each
    // compiler, even though the arch is the same.
    class MyCardCompiler extends CardCompiler {
        setup() {
            super.setup();
            this.compilers.push({ selector: "div", fn: this.compileDiv });
        }

        compileDiv(node, params) {
            const compiledNode = this.compileGenericNode(node, params);
            compiledNode.setAttribute("class", "my_card_compiler");
            return compiledNode;
        }
    }

    const arch = `
        <card>
            <templates>
                <t t-name="card">
                    <div><field name="foo"/></div>
                </t>
            </templates>
        </card>`;

    // Mount with custom compiler
    await mountCard({ resModel: "partner", arch, Compiler: MyCardCompiler });
    expect(".my_card_compiler").toHaveCount(1);

    // Mount with default compiler — no new my_card_compiler elements are added
    const before = queryAll(".my_card_compiler").length;
    await mountCard({ resModel: "partner", arch });
    expect(queryAll(".my_card_compiler").length).toBe(before, {
        message: "default compiler should not produce my_card_compiler elements",
    });
});

test.tags("desktop");
test("card: fields with data-tooltip attribute", async () => {
    await mountCard({
        resModel: "partner",
        resId: 1,
        arch: `
            <card>
                <templates>
                    <t t-name="card">
                        <field name="foo" data-tooltip="pipu" />
                    </t>
                </templates>
            </card>`,
    });

    expect(".o-tooltip").toHaveCount(0);
    await hover("article span");
    await advanceTime(500);
    expect(".o-tooltip").toHaveCount(1);
});
