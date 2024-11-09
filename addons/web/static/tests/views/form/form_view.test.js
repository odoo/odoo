import { after, before, expect, test } from "@odoo/hoot";
import {
    clear,
    click,
    hover,
    press,
    queryAllAttributes,
    queryAllTexts,
    queryFirst,
} from "@odoo/hoot-dom";
import { Deferred, animationFrame, mockTimeZone, mockTouch, runAllTimers } from "@odoo/hoot-mock";
import {
    Component,
    EventBus,
    onMounted,
    onPatched,
    onWillStart,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    defineModels,
    fields,
    findComponent,
    getPagerLimit,
    getPagerValue,
    getService,
    installLanguages,
    makeServerError,
    mockService,
    models,
    mountView,
    mountViewInDialog,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    toggleActionMenu,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { useBus, useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { CharField } from "@web/views/fields/char/char_field";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { Field } from "@web/views/fields/field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { FormController } from "@web/views/form/form_controller";
import { WebClient } from "@web/webclient/webclient";

const fieldsRegistry = registry.category("fields");
const widgetsRegistry = registry.category("view_widgets");

class Partner extends models.Model {
    name = fields.Char({ translate: true });
    foo = fields.Char({ default: "My little Foo Value" });
    bar = fields.Boolean();
    int_field = fields.Integer();
    float_field = fields.Float({ aggregator: "sum" });
    child_ids = fields.One2many({ string: "one2many field", relation: "partner" });
    parent_id = fields.Many2one({ relation: "partner" });
    type_ids = fields.Many2many({ relation: "partner.type" });
    product_id = fields.Many2one({ relation: "product" });
    product_ids = fields.One2many({ relation: "product" });
    state = fields.Selection({
        selection: [
            ["ab", "AB"],
            ["cd", "CD"],
            ["ef", "EF"],
        ],
    });
    date = fields.Date();
    datetime = fields.Datetime();
    reference = fields.Reference({
        selection: [
            ["product", "Product"],
            ["partner_type", "Partner Type"],
            ["partner", "Partner"],
        ],
    });
    user_id = fields.Many2one({ relation: "res.users" });

    _records = [
        {
            id: 1,
            name: "first record",
            product_id: 37,
            bar: true,
            foo: "yop",
            int_field: 10,
            float_field: 0.44,
            child_ids: [],
            type_ids: [],
            parent_id: 4,
            state: "ab",
            date: "2017-01-25",
            datetime: "2016-12-12 10:55:05",
        },
        {
            id: 2,
            name: "second record",
            bar: true,
            foo: "blip",
            int_field: 9,
            float_field: 13,
            child_ids: [],
            type_ids: [],
            parent_id: 1,
            state: "cd",
        },
        {
            id: 4,
            name: "aaa",
            state: "ef",
        },
        {
            id: 5,
            name: "aaa",
            foo: "",
            bar: false,
            state: "ef",
        },
    ];
}

class PartnerType extends models.Model {
    _name = "partner.type";

    name = fields.Char();
    color = fields.Integer();
    foo = fields.Char();

    _records = [
        { id: 12, name: "gold", color: 2 },
        { id: 14, name: "silver", color: 5 },
    ];
}

class Product extends models.Model {
    name = fields.Char();
    partner_type_id = fields.Many2one({ relation: "partner.type" });

    _records = [
        { id: 37, name: "xphone" },
        { id: 41, name: "xpad" },
    ];
}

class ResUsers extends models.Model {
    _name = "res.users";

    name = fields.Char();
    partner_ids = fields.One2many({ relation: "partner", relation_field: "user_id" });

    _records = [
        { id: 17, name: "Aline", partner_ids: [1] },
        { id: 19, name: "Christine" },
    ];
}

class ResCompany extends models.Model {
    _name = "res.company";
    name = fields.Char();
}

defineModels([Partner, PartnerType, Product, ResUsers, ResCompany]);

onRpc("has_group", () => true);

before(() => {
    patchWithCleanup(EventBus.prototype, {
        addEventListener(...args) {
            super.addEventListener(...args);
            after(() => {
                this.removeEventListener(...args);
            });
        },
    });
});

test(`simple form rendering`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div class="test" style="opacity: 0.5;">some html<span>aa</span></div>
                <sheet>
                    <group>
                        <group style="background-color: red">
                            <field name="foo" style="color: blue;"/>
                            <field name="bar"/>
                            <field name="int_field" string="f3_description"/>
                            <field name="float_field"/>
                        </group>
                        <group>
                            <div class="hello"></div>
                        </group>
                    </group>
                    <notebook>
                        <page string="Partner Yo">
                            <field name="child_ids">
                                <list>
                                    <field name="foo"/>
                                    <field name="bar"/>
                                </list>
                            </field>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`div.test`).toHaveCount(1);
    expect(`div.test`).toHaveStyle({ opacity: "0.5" });
    expect(`label:contains(Foo)`).toHaveCount(1);
    expect(`.o_field_char input`).toHaveCount(1);
    expect(`.o_field_char input`).toHaveValue("blip");
    expect(`.o_group .o_inner_group:eq(0)`).toHaveStyle({ backgroundColor: "rgb(255, 0, 0)" });
    expect(`.o_field_widget[name=foo]`).toHaveStyle({ color: "rgb(0, 0, 255)" });
    expect(`label:contains(something_id)`).toHaveCount(0);
    expect(`label:contains(f3_description)`).toHaveCount(1);
    expect(`div.o_field_one2many table`).toHaveCount(1);
    expect(`div.o_cell:not(.o_list_record_selector) .o-checkbox input:checked`).toHaveCount(1);
    expect(`label.o_form_label_empty:contains(type_ids)`).toHaveCount(0);
});

test(`form rendering with class and style attributes`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: /* xml */ `<form class="myCustomClass" style="border: 1px solid red;"/>`,
        resId: 2,
    });
    expect(
        `.o_view_controller[style*='border: 1px solid red;'], .o_view_controller [style*='border: 1px solid red;']`
    ).toHaveCount(0);
    expect(`.o_view_controller.o_form_view.myCustomClass`).toHaveCount(1);
    expect(`.myCustomClass`).toHaveCount(1);
});

test(`generic tags are case insensitive`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><Div class="test">Hello</Div></form>`,
    });
    expect(`div.test`).toHaveCount(1);
});

test(`form view with a group that contains an invisible group`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <group invisible="1">
                            <field name="foo"/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_form_view .o_group`).toHaveCount(1);
});

test.tags("mobile")(`button box rendering on small screen`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><sheet><div name="button_box"><button id="btn1">MyButton</button><button id="btn2">MyButton2</button><button id="btn3">MyButton3</button><button id="btn4">MyButton4</button></div></sheet></form>`,
        resId: 2,
    });
    expect(`.o-form-buttonbox > button`).toHaveCount(0);
    expect(`.oe_stat_button .o_button_more`).toHaveCount(1);

    await contains(`div.oe_stat_button .o_button_more`).click();
    expect(`.o-form-buttonbox-small button.oe_stat_button`).toHaveCount(4);
    expect(`.o-dropdown--menu #btn4`).toHaveCount(1);
});

test.tags("desktop")(`button box rendering on big screen`, async () => {
    const bus = new EventBus();
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            value: false,
        });
        return {
            bus,
            get size() {
                return SIZES.XXL;
            },
            get isSmall() {
                return false;
            },
        };
    });
    let btnString = "";
    for (let i = 0; i < 9; i++) {
        btnString += `<button class="oe_stat_button" id="btn${i}">My Button ${i}</button>`;
    }

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><sheet><div name="button_box">${btnString}</div></sheet></form>`,
        resId: 2,
    });
    expect(`.o-form-buttonbox > button`).toHaveCount(7);
    expect(`.o-form-buttonbox > .oe_stat_button .o-dropdown`).toHaveCount(1);

    const buttonBox = queryFirst(`.o-form-buttonbox`);
    const buttonBoxRect = buttonBox.getBoundingClientRect();
    // we asserted that we have 7 buttons + 1 dropdown
    for (const btn of buttonBox.children) {
        expect(btn).toHaveRect({ top: buttonBoxRect.top });
    }
});

test(`form view gets size class on small and big screens`, async () => {
    let uiSize = SIZES.MD;
    const bus = new EventBus();
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            value: false,
        });
        return {
            bus,
            get size() {
                return uiSize;
            },
            get isSmall() {
                return uiSize <= SIZES.SM;
            },
        };
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><sheet><div></div></sheet></form>`,
        resId: 2,
    });
    expect(`.o_xxl_form_view, .o_xxs_form_view`).toHaveCount(0);

    uiSize = SIZES.XXL;
    bus.trigger("resize");
    await animationFrame();
    expect(`.o_xxs_form_view`).toHaveCount(0);
    expect(`.o_xxl_form_view`).toHaveCount(1);

    uiSize = SIZES.XS;
    bus.trigger("resize");
    await animationFrame();
    expect(`.o_xxl_form_view`).toHaveCount(0);
    expect(`.o_xxs_form_view`).toHaveCount(1);
});

test(`duplicate fields rendered properly`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <group>
                        <field name="foo" class="foo_1" invisible="not bar"/>
                        <field name="foo" class="foo_2" invisible="bar"/>
                        <field name="foo" class="foo_3"/>
                        <field name="int_field" class="int_field_1" readonly="bar"/>
                        <field name="int_field" class="int_field_2" readonly="not bar"/>
                        <field name="bar"/>
                    </group>
                </group>
            </form>
        `,
    });
    expect(`.o_field_widget[name=foo].foo_1`).toHaveCount(0);
    expect(`.o_field_widget[name=foo].foo_2`).toHaveCount(1);
    expect(`.o_field_widget[name=foo].foo_3`).toHaveCount(1);

    await contains(`.o_field_widget[name=foo].foo_3 input`).edit("hello");
    expect(`.o_field_widget[name=foo].foo_2 input`).toHaveValue("hello");
    expect(`.o_field_widget[name=int_field].int_field_1`).not.toHaveClass("o_readonly_modifier");
    expect(`.o_field_widget[name=int_field].int_field_2`).toHaveClass("o_readonly_modifier");
    expect(`.int_field_1 input`).toHaveCount(1);
    expect(`.int_field_2 span`).toHaveCount(1);

    await contains(`.o_field_widget[name=bar] input`).check();
    expect(`.o_field_widget[name=int_field].int_field_1`).toHaveClass("o_readonly_modifier");
    expect(`.o_field_widget[name=int_field].int_field_2`).not.toHaveClass("o_readonly_modifier");
    expect(`.int_field_1 span`).toHaveCount(1);
    expect(`.int_field_2 input`).toHaveCount(1);
});

test(`duplicate fields rendered properly (one2many)`, async () => {
    Partner._records.push({ id: 6, child_ids: [1] });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="bottom">
                        <field name="foo"/>
                    </list>
                    <form/>
                </field>
                <field name="child_ids" readonly="True">
                    <list editable="bottom">
                        <field name="foo"/>
                    </list>
                    <form/>
                </field>
            </form>
        `,
        resId: 6,
    });
    expect(`.o_field_one2many`).toHaveCount(2);
    expect(`.o_field_one2many:eq(0)`).not.toHaveClass("o_readonly_modifier");
    expect(`.o_field_one2many:eq(1)`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_one2many:eq(0) .o_data_cell`).click();
    expect(`.o_field_one2many`).toHaveCount(2);
    expect(`.o_field_one2many:eq(0) .o_selected_row .o_field_widget[name=foo] input`).toHaveValue(
        "yop"
    );
    expect(`.o_field_one2many:eq(1) .o_data_row:eq(0) .o_data_cell[name=foo]`).toHaveText("yop");

    await contains(`.o_field_one2many:eq(0) .o_selected_row .o_field_widget[name=foo] input`).edit(
        "hello",
        { confirm: false }
    );
    await click(`.o_content`); // confirm change by focusing out the input.
    await animationFrame();
    await animationFrame();
    await animationFrame();
    await animationFrame();
    await animationFrame();
    await animationFrame();
    expect(`.o_field_one2many:eq(1) .o_data_row:eq(0) .o_data_cell[name=foo]`).toHaveText("hello");

    await contains(`.o_field_one2many:eq(0) .o_field_x2many_list_row_add a`).click();
    expect(`.o_field_one2many:eq(0) .o_selected_row .o_field_widget[name="foo"] input`).toHaveValue(
        "My little Foo Value"
    );
    expect(`.o_field_one2many:eq(1) .o_data_row:eq(1) .o_data_cell[name=foo]`).toHaveText(
        "My little Foo Value"
    );
});

test(`attributes are transferred on async widgets`, async () => {
    const def = new Deferred();
    class AsyncField extends CharField {
        willStart() {
            return def;
        }
    }
    fieldsRegistry.add("asyncwidget", { component: AsyncField });

    const viewProm = mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" style="color: blue;" widget="asyncwidget"/></form>`,
        resId: 2,
    });
    await animationFrame();

    def.resolve();
    await viewProm;
    expect(`.o_field_widget[name=foo]`).toHaveStyle({ color: "rgb(0, 0, 255)" });
});

test(`placeholder attribute on input`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><input placeholder="chimay"/></form>`,
        resId: 2,
    });
    expect(`input[placeholder="chimay"]`).toHaveCount(1);
});

test(`decoration works on widgets`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="display_name" decoration-danger="int_field &lt; 5"/>
                <field name="foo" decoration-danger="int_field &gt; 5"/>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_widget[name="display_name"]`).not.toHaveClass("text-danger");
    expect(`.o_field_widget[name="foo"]`).toHaveClass("text-danger");
});

test(`form with o2m having a many2many fields using the many2many_tags widget along the color_field option`, async () => {
    // In this scenario, the x2many form view isn't inline, so when we click on the record,
    // it does an independant getView, which doesn't return all fields of the model. In the
    // x2many list view, there's a field with a many2many_tags widget with the color option,
    // and the color field (color) in our case, isn't in the form view.
    // This test ensures that we can open the form view in this situation.
    Partner._records[0].type_ids = [12, 14];
    Partner._views = {
        form: `
            <form>
                <field name="display_name"/>
                <field name="type_ids" widget="one2many">
                    <list string="Values">
                        <field name="display_name"/>
                        <!--
                            Required to add at least one different field than the fields read
                            to display <field name="type_ids" widget="many2many_tags"/> below.
                            To force to re-read the record with more fields.
                        -->
                        <field name="foo"/>
                    </list>
                </field>
            </form>
        `,
    };

    await mountView({
        resModel: "res.users",
        type: "form",
        arch: `
                <form edit="0">
                    <field name="partner_ids">
                        <list>
                            <field name="name"/>
                            <field name="type_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                        </list>
                    </field>
                </form>
            `,
        resId: 17,
    });
    expect(`.o_field_widget[name=type_ids] .o_field_tags`).toHaveCount(1);

    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.modal .o_form_view .o_field_widget[name=type_ids]`).toHaveCount(1);
});

test(`form with o2m having a field with fieldDependencies`, async () => {
    // In this scenario, the x2many form view isn't inline, so when we click on the record,
    // it does an independant getView, which doesn't return all fields of the model. In the
    // x2many list view, there's a field with fieldDependencies, and the dependency field
    // (int_field) in our case, isn't in the form view. This test ensures that we can open
    // the form view in this situation.
    class MyField extends CharField {}
    fieldsRegistry.add("my_widget", {
        component: MyField,
        fieldDependencies: [{ name: "int_field", type: "integer" }],
    });

    Partner._records[1].child_ids = [1];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list>
                        <field name="foo" widget="my_widget"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_widget[name="child_ids"] .o_data_row`).toHaveCount(1);

    await contains(`.o_field_widget[name="child_ids"] .o_data_row .o_data_cell`).click();
    expect(`.modal .o_form_view .o_field_widget[name="child_ids"]`).toHaveCount(1);
});

test(`form with o2m having a selection field with fieldDependencies`, async () => {
    class MyField extends CharField {}
    fieldsRegistry.add("my_widget", {
        component: MyField,
        fieldDependencies: [{ name: "selection", type: "selection" }],
    });

    Partner._fields.o2m = fields.One2many({ relation: "partner.type" });
    Partner._records[1].o2m = [1];

    PartnerType._fields.selection = fields.Selection({
        selection: [
            ["a", "A"],
            ["b", "B"],
        ],
    });
    PartnerType._records = [
        {
            id: 1,
            name: "first partner_type",
            selection: false,
        },
    ];
    PartnerType._views = {
        form: `<form><field name="display_name" /></form>`,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="o2m">
                    <list>
                        <field name="display_name" widget="my_widget"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_widget[name=o2m] .o_data_row`).toHaveCount(1);

    await contains(`.o_field_widget[name=o2m] .o_field_x2many_list_row_add a`).click();
    expect(`.modal .o_form_view .o_field_widget[name=display_name]`).toHaveCount(1);
});

test(`fieldDependencies are readonly by default`, async () => {
    class MyField extends CharField {}
    fieldsRegistry.add("my_widget", {
        component: MyField,
        fieldDependencies: [
            { name: "int_field", type: "integer" },
            { name: "bar", type: "boolean" },
            { name: "float_field", type: "float", readonly: false },
        ],
    });

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual(
            {
                name: "plop",
                foo: "My little Foo Value",
                float_field: 0,
            },
            { message: "'int_field' and 'bar' shouldn't be present" }
        );
        expect.step("web_save");
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="name"/>
                <field name="foo" widget="my_widget"/>
                <field name="int_field" readonly="1"/>
            </form>
        `,
    });
    await contains(`[name='name'] input`).edit("plop");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`decoration-bf works on fields`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="display_name" decoration-bf="int_field &lt; 5"/>
                <field name="foo" decoration-bf="int_field &gt; 5"/>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_widget[name="display_name"]`).not.toHaveClass("fw-bold");
    expect(`.o_field_widget[name="foo"]`).toHaveClass("fw-bold");
});

test(`decoration-it works on fields`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="display_name" decoration-it="int_field &lt; 5"/>
                <field name="foo" decoration-it="int_field &gt; 5"/>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_widget[name="display_name"]`).not.toHaveClass("fst-italic");
    expect(`.o_field_widget[name="foo"]`).toHaveClass("fst-italic");
});

test(`decoration on widgets are reevaluated if necessary`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="display_name" decoration-danger="int_field &lt; 5"/>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_widget[name="display_name"]`).not.toHaveClass("text-danger");
    await contains(`.o_field_widget[name=int_field] input`).edit("3");
    expect(`.o_field_widget[name="display_name"]`).toHaveClass("text-danger");
});

test(`decoration on widgets works on same widget`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field" decoration-danger="int_field &lt; 5"/></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name="int_field"]`).not.toHaveClass("text-danger");
    await contains(`.o_field_widget[name=int_field] input`).edit("3");
    expect(`.o_field_widget[name="int_field"]`).toHaveClass("text-danger");
});

test(`only necessary fields are fetched with correct context`, async () => {
    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.specification).toEqual(
            { foo: {}, display_name: {} },
            { message: "should only fetch requested fields" }
        );
        expect(kwargs.context.bin_size).toBe(true, {
            message: "bin_size should always be in the context",
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect.verifySteps(["web_read"]);
});

test(`group rendering`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`div.o_inner_group`).toHaveCount(1);
});

test(`group with formLabel`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <!-- OuterGroup -->
                        <field name="foo"/>
                        <label for="foo" class="plop plop2"/>
                        <group>
                            <!-- InnerGroup -->
                            <field name="display_name"/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_widget[name=foo]`).toHaveClass(["o_field_char", "col-lg-6"]);
    expect(`.o_form_label[for=foo_0]`).toHaveClass(["plop", "plop2", "col-lg-6"]);
});

test(`group containing both a field and a group`, async () => {
    // The purpose of this test is to check that classnames defined in a
    // field widget and those added by the form renderer are correctly
    // combined. For instance, the renderer adds className 'o_group_col_x'
    // on outer group's children (an outer group being a group that contains
    // at least a group).
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo"/>
                    <group>
                        <field name="int_field"/>
                    </group>
                </group>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_group .o_field_widget[name=foo]`).toHaveCount(1);
    expect(`.o_group .o_inner_group .o_field_widget[name=int_field]`).toHaveCount(1);
    expect(`.o_field_widget[name=foo]`).toHaveClass(["o_field_char", "col-lg-6"]);
});

test(`field ids are unique (same field name in 2 form views)`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo"/>
                    </group>
                    <field name="child_ids">
                        <form>
                            <sheet>
                                <group>
                                    <field name="bar"/>
                                    <field name="foo"/>
                                </group>
                            </sheet>
                        </form>
                        <list>
                            <field name="foo"/>
                        </list>
                    </field>
                </sheet>
            </form>`,
        resId: 1,
    });

    expect(".o_field_widget input#foo_0").toHaveCount(1);

    await contains(".o_field_x2many_list_row_add a").click();
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".o_field_widget input#foo_0").toHaveCount(1);
    expect(".modal .o_field_widget input#foo_0").toHaveCount(1);
    expect(".modal .o_field_widget input#bar_0").toHaveCount(1);
});

test(`Form and subview with _view_ref contexts`, async () => {
    Product._fields.type_ids = fields.One2many({ relation: "partner.type" });
    Product._records = [{ id: 1, name: "Tromblon", type_ids: [12, 14] }];
    Partner._records[0].product_id = 1;

    // This is an old test, written before "get_views" (formerly "load_views") automatically
    // inlines x2many subviews. As the purpose of this test is to assert that the js fetches
    // the correct sub view when it is not inline (which can still happen in nested form views),
    // we bypass the inline mecanism of "get_views" by setting widget="one2many" on the field.
    Partner._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="product_id" context="{'list_view_ref': 'some_tree_view'}"/>
            </form>
        `,
        search: `<search/>`,
    };
    PartnerType._views = {
        list: `<list><field name="color"/></list>`,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="color"/>
                    </t>
                </templates>
            </kanban>
        `,
    };
    Product._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="type_ids" widget="one2many" context="{'list_view_ref': 'some_other_tree_view'}"/>
            </form>
        `,
        search: `<search/>`,
    };

    onRpc("product", "get_views", ({ kwargs }) => {
        const { context } = kwargs;
        expect.step("product get_views");
        expect(context.list_view_ref).toBe("some_tree_view");
        // "The correct _view_ref should have been sent to the server, first time"
    });
    onRpc("partner.type", "get_views", ({ kwargs }) => {
        const { context } = kwargs;
        expect.step("partner.type get_views");
        expect(context.list_view_ref).toBe("some_other_tree_view");
        // "The correct _view_ref should have been sent to the server for the subview"
    });
    onRpc("get_formview_action", ({ model, kwargs }) => {
        expect.step("get_formview_action");
        return {
            res_id: 1,
            type: "ir.actions.act_window",
            target: "current",
            res_model: model,
            context: kwargs.context,
            view_mode: "form",
            views: [[false, "form"]],
        };
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_id: 1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "partner",
        view_mode: "form",
        views: [[false, "form"]],
    });
    await contains(`.o_field_widget[name="product_id"] .o_external_button`, {
        visible: false,
    }).click();
    expect.verifySteps(["get_formview_action", "product get_views", "partner.type get_views"]);
});

test(`Form and subsubview with only _view_ref contexts`, async () => {
    PartnerType._fields.company_ids = fields.One2many({ relation: "res.company" });
    ResCompany._views = {
        search: `<search/>`,
        list: `<list><field name="name"/></list>`,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        "form,2": `<form><field name="name"/></form>`,
    };
    PartnerType._views = {
        search: `<search/>`,
        list: `<list><field name="name"/></list>`,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        "form,foo_partner_type_form_view": `
            <form>
                <field name="color"/>
                <field name="company_ids" context="{
                    'default_color': 2,
                    'form_view_ref': 'bar_rescompany_form_view',
                }"/>
            </form>
        `,
    };

    const userContext = {
        lang: "en",
        tz: "taht",
        uid: 7,
        allowed_company_ids: [1],
    };
    const expectedContexts = new Map();
    expectedContexts.set("view:partner", { ...userContext });
    expectedContexts.set("onchange:partner", { ...userContext });
    expectedContexts.set("view:partner.type", {
        ...userContext,
        form_view_ref: "foo_partner_type_form_view",
    });
    expectedContexts.set("onchange:partner.type", {
        ...userContext,
        form_view_ref: "foo_partner_type_form_view",
    });

    onRpc("get_views", ({ model, kwargs }) => {
        const { context } = kwargs;
        expect.step(`get_views (${model})`);
        expect(context).toEqual(expectedContexts.get(`view:${model}`));
    });
    onRpc("onchange", ({ model, kwargs }) => {
        const { context } = kwargs;
        expect.step(`onchange (${model})`);
        expect(context).toEqual(expectedContexts.get(`onchange:${model}`));
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field string="Partner Types" name="type_ids" widget="one2many" context="{
                    'default_partner_id': id,
                    'form_view_ref': 'foo_partner_type_form_view'
                }"/>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps(["get_views (partner)", "get_views (partner.type)"]);

    // Add a line in the x2many type_ids field
    expectedContexts.clear();
    expectedContexts.set("view:partner.type", {
        ...userContext,
        form_view_ref: "foo_partner_type_form_view",
    });
    expectedContexts.set("onchange:partner.type", {
        ...userContext,
        default_partner_id: 2,
        form_view_ref: "foo_partner_type_form_view",
    });

    await contains(
        `[name=type_ids] .o_field_x2many_list_row_add a, [name=type_ids] .o-kanban-button-new`
    ).click();
    expect.verifySteps(["get_views (partner.type)"]);

    // Create a new type_ids
    await contains(`.modal .o_create_button`).click();
    expect.verifySteps(["get_views (partner.type)", "onchange (partner.type)"]);

    // Create a new company
    expectedContexts.clear();
    expectedContexts.set("view:res.company", {
        ...userContext,
        form_view_ref: "bar_rescompany_form_view",
    });
    expectedContexts.set("onchange:res.company", {
        ...userContext,
        default_color: 2,
        form_view_ref: "bar_rescompany_form_view",
    });

    await contains(`.modal [name=company_ids] .o_field_x2many_list_row_add a`).click();
    expect.verifySteps(["get_views (res.company)", "onchange (res.company)"]);
});

test(`x2many form_view_ref with defined list`, async () => {
    Partner._records = [{ id: 1, type_ids: [1] }];

    PartnerType._records = [{ id: 1, name: "Timmy 1" }];
    PartnerType._views = {
        "form,foo_partner_type_form_view": `
            <form>
                <div class="form_view_ref_partner_type">
                    <field name="display_name" />
                </div>
            </form>
        `,
    };

    const expectedContexts = new Map();
    const userContext = {
        lang: "en",
        tz: "taht",
        uid: 7,
        allowed_company_ids: [1],
    };

    expectedContexts.set("partner", { ...userContext });
    expectedContexts.set("partner.type", {
        ...userContext,
        form_view_ref: "foo_partner_type_form_view",
    });

    onRpc("get_views", ({ model, kwargs }) => {
        expect.step(`get_views (${model})`);
        expect(kwargs.context).toEqual(expectedContexts.get(model));
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="type_ids" invisible="1" />
                <field string="Partner Types" name="type_ids" context="{
                    'default_partner_id': id,
                    'form_view_ref': 'foo_partner_type_form_view'
                }">
                    <list>
                        <field name="display_name" />
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["get_views (partner)"]);

    await contains(`.o_field_widget[name='type_ids'] .o_field_cell`).click();
    expect.verifySteps(["get_views (partner.type)"]);
});

test(`invisible fields are properly hidden`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        // the arch contains an x2many field without inline view: as it is always invisible,
        // the view should not be fetched. we don't specify any view in this test, so if it
        // ever tries to fetch it, it will crash, indicating that this is wrong.
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" invisible="1"/>
                        <field name="bar"/>
                    </group>
                    <field name="float_field" invisible="1"/>
                    <field name="child_ids" invisible="True"/>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`label:contains(Foo)`).toHaveCount(0);
    expect(`.o_field_widget[name=foo]`).toHaveCount(0);
    expect(`.o_field_widget[name=float_field]`).toHaveCount(0);
    expect(`.o_field_widget[name="child_ids"]`).toHaveCount(0);
});

test(`correctly copy attributes to compiled labels`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <label string="Apply after" for="bar" class="a"/>
                <field name="bar" class="b"/>
                <label string="hours" for="bar" class="c"/>
            </form>
        `,
    });
    expect(`.o_form_label:eq(0)`).toHaveClass("a");
    expect(`.o_field_widget.o_field_boolean`).toHaveClass("b");
    expect(`.o_form_label:eq(1)`).toHaveClass("c");
});

test(`invisible fields are not used for the label generation`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="float_field" invisible="1"/>
                    <label for="float_field"/>
                    <field name="float_field"/>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`label:contains(Float field)`).toHaveCount(1);
});

test(`invisible elements are properly hidden`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header invisible="1">
                    <button name="myaction" string="coucou"/>
                </header>
                <sheet>
                <group>
                    <group string="invgroup" invisible="1">
                        <field name="foo"/>
                    </group>
                    <group string="visgroup">
                        <field name="bar"/>
                    </group>
                </group>
                <notebook>
                    <page string="visible"/>
                    <page string="invisible" invisible="1"/>
                </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_form_statusbar button:contains(coucou)`).toHaveCount(0);
    expect(`.o_notebook li a:contains(visible)`).toHaveCount(1);
    expect(`.o_notebook li a:contains(invisible)`).toHaveCount(0);
    expect(`div.o_inner_group:contains(visgroup)`).toHaveCount(1);
    expect(`div.o_inner_group:contains(invgroup)`).toHaveCount(0);
});

test(`invisible attrs on fields are re-evaluated on field change`, async () => {
    // we set the value bar to simulate a falsy boolean value.
    Partner._records[0].bar = false;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="int_field"/>
                        <field name="type_ids" invisible="1"/>
                        <field name="foo" invisible="int_field == 10"/>
                        <field name="bar" invisible="not bar and not type_ids"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_widget[name=int_field]`).toHaveCount(1);
    expect(`.o_field_widget[name=type_ids]`).toHaveCount(0);
    expect(`.o_field_widget[name=foo]`).toHaveCount(0);
    expect(`.o_field_widget[name=bar]`).toHaveCount(0);

    await contains(`.o_field_widget[name=int_field] input`).edit("44");
    expect(`.o_field_widget[name=int_field]`).toHaveCount(1);
    expect(`.o_field_widget[name=type_ids]`).toHaveCount(0);
    expect(`.o_field_widget[name=foo]`).toHaveCount(1);
    expect(`.o_field_widget[name=bar]`).toHaveCount(0);
});

test(`invisible attrs char fields`, async () => {
    // For a char/text field, the server can return false or "" (empty string),
    // depending if the field isn't set in db (NULL) or set to the empty string.
    // This makes no difference in the UI, but it matters when evaluating modifiers.
    Partner._records[0].name = false;
    Partner._records[0].foo = "";

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div class="a" invisible="foo == False">b</div>
                <div class="b" invisible="foo == ''">b</div>
                <div class="c" invisible="not name">c</div>
                <div class="d" invisible="name == ''">d</div>
                <div class="e" invisible="not foo">e</div>
                <div class="f" invisible="name == False">f</div>
                <field name="name" invisible="1"/>
                <field name="foo" invisible="1"/>
            </form>
        `,
        resId: 1,
    });
    expect(`div.a`).toHaveCount(1);
    expect(`div.b`).toHaveCount(0);
    expect(`div.c`).toHaveCount(0);
    expect(`div.d`).toHaveCount(1);
    expect(`div.e`).toHaveCount(0);
    expect(`div.f`).toHaveCount(0);
});

test(`properly handle modifiers and attributes on notebook tags`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="int_field"/>
                    <notebook name="test_name" class="new_class" invisible="int_field == 10">
                        <page string="Foo">
                            <field name="foo"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook`).toHaveCount(0);

    await contains(`.o_field_widget[name=int_field] input`).edit("44");
    expect(`.o_notebook`).toHaveCount(1);
    expect(`.o_notebook`).toHaveClass("new_class");
});

test(`empty notebook`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook/>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`:scope .o_notebook .nav`).toHaveCount(0);
});

test(`notebook page name and class transferred to DOM`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page name="choucroute" string="Choucroute" class="sauerKraut">
                            <field name="foo"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook .nav .nav-link[name='choucroute']`).toHaveClass(["active", "sauerKraut"]);
});

test(`no visible page`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Foo" invisible="1">
                            <field name="foo"/>
                        </page>
                        <page string="Bar" invisible="1">
                            <field name="bar"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook_headers .nav-item`).toHaveCount(0);
    expect(`.tab-content .tab-pane`).toHaveCount(0);
});

test(`notebook: pages with invisible modifiers`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <notebook>
                        <page string="A" invisible='not bar'>
                            <field name="foo"/>
                        </page>
                        <page string="B" invisible='bar'>
                            <field name="int_field"/>
                        </page>
                        <page string="C">
                            <field name="float_field"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook .nav-link`).toHaveCount(2);
    expect(`.o_notebook .nav .nav-link.active`).toHaveCount(1);
    expect(`.o_notebook .nav .nav-link:eq(0)`).toHaveClass("active");
    expect(`.o_notebook .nav-link.active`).toHaveText("A");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_notebook .nav-link`).toHaveCount(2);
    expect(`.o_notebook .nav .nav-link.active`).toHaveCount(1);
    expect(`.o_notebook .nav .nav-link:eq(0)`).toHaveClass("active");
    expect(`.o_notebook .nav-link.active`).toHaveText("B");
});

test(`invisible attrs on first notebook page`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="int_field"/>
                    <notebook>
                        <page string="Foo" invisible='int_field == 44'>
                            <field name="foo"/>
                        </page>
                        <page string="Bar">
                            <field name="bar"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook .nav .nav-link`).toHaveCount(2);
    expect(`.o_notebook .nav .nav-link:eq(0)`).toHaveClass("active");
    expect(`.o_notebook .tab-content .tab-pane:eq(0)`).toHaveClass("active");

    await contains(`.o_field_widget[name=int_field] input`).edit("44");
    expect(`.o_notebook .nav .nav-link`).toHaveCount(1);
    expect(`.o_notebook .tab-content .tab-pane`).toHaveCount(1);
    expect(`.o_notebook .nav .nav-link`).toHaveClass("active");
    expect(`.o_notebook .tab-content .tab-pane`).toHaveClass("active");
});

test(`invisible attrs on notebook page which has only one page`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <notebook>
                        <page string="Foo" invisible='bar'>
                            <field name="foo"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook`).toHaveCount(0);

    // enable checkbox
    await contains(`.o_field_boolean input`).click();
    expect(`.o_notebook .nav .nav-link`).toHaveCount(1);
    expect(`.o_notebook .tab-content .tab-pane`).toHaveCount(1);
    expect(`.o_notebook .nav .nav-link`).toHaveClass("active");
    expect(`.o_notebook .tab-content .tab-pane`).toHaveClass("active");
});

test(`first notebook page invisible`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="product_id"/>
                    <notebook>
                        <page string="Foo" invisible="1">
                            <field name="foo"/>
                        </page>
                        <page string="Bar">
                            <field name="bar"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook .nav .nav-link`).toHaveCount(1);
    expect(`.o_notebook .nav .nav-link`).toHaveClass("active");
});

test(`hide notebook element if all pages hidden`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <notebook class="new_class">
                        <page string="Foo" invisible="bar">
                            <field name="foo"/>
                        </page>
                        <page string="float_field" invisible="1">
                            <field name="float_field"/>
                        </page>
                        <page string="IntField" invisible="bar">
                            <field name="int_field"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
    });
    expect(`.o_notebook .nav .nav-link`).toHaveCount(2);

    await contains(`.o_field_boolean input`).click();
    expect(`.o_notebook`).toHaveCount(0);
});

test(`autofocus on second notebook page`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="product_id"/>
                    <notebook>
                        <page string="Choucroute">
                            <field name="foo"/>
                        </page>
                        <page string="Cassoulet" autofocus="autofocus">
                            <field name="bar"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_notebook .nav .nav-item:eq(0) .nav-link`).not.toHaveClass("active");
    expect(`.o_notebook .nav .nav-item:eq(1) .nav-link`).toHaveClass("active");
});

test(`notebook page is changing when an anchor is clicked from another page`, async () => {
    await mountWithCleanup(`
        <div class="scrollable-view" style="overflow: auto; max-height: 400px;"/>
    `);

    await mountView(
        {
            resModel: "partner",
            type: "form",
            arch: `
            <form>
                <a class="outerLink2" href="#anchor2">TO ANCHOR 2 FROM OUTSIDE THE NOTEPAD</a>
                <sheet>
                    <notebook>
                        <page string="Non scrollable page">
                            <div id="anchor1">No scrollbar!</div>
                            <a href="#anchor2" class="link2">TO ANCHOR 2</a>
                        </page>
                        <page string="Other scrollable page">
                            <p style="font-size: large">
                                Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                                ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                                at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                                placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                                augue.
                            </p>
                            <p style="font-size: large">
                                Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                                ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                                at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                                placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                                augue.
                            </p>
                            <h2 id="anchor2">There is a scroll bar</h2>
                            <a href="#anchor1" class="link1">TO ANCHOR 1</a>
                            <p style="font-size: large">
                                Aliquam convallis sollicitudin purus. Praesent aliquam, enim at fermentum mollis,
                                ligula massa adipiscing nisl, ac euismod nibh nisl eu lectus. Fusce vulputate sem
                                at sapien. Vivamus leo. Aliquam euismod libero eu enim. Nulla nec felis sed leo
                                placerat imperdiet. Aenean suscipit nulla in justo. Suspendisse cursus rutrum
                                augue.
                            </p>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
            resId: 1,
        },
        queryFirst`.scrollable-view`
    );
    expect(`.tab-pane.active #anchor1`).toHaveCount(1);
    expect(`#anchor2`).toHaveCount(0);

    await contains(`.link2`).click();
    expect(`.tab-pane.active #anchor2`).toHaveCount(1);
    expect(`#anchor2`).toBeVisible();

    await contains(`.link1`).click();
    expect(`.tab-pane.active #anchor1`).toHaveCount(1);
    expect(`#anchor1`).toBeVisible();

    await contains(`.outerLink2`).click();
    expect(`.tab-pane.active #anchor2`).toHaveCount(1);
    expect(`#anchor2`).toBeVisible();
});

test(`invisible attrs on group are re-evaluated on field change`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="bar"/>
                    <group invisible='not bar'>
                        <group>
                            <field name="foo"/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`div.o_group`).toHaveCount(1);

    await contains(`.o_field_boolean input`).click();
    expect(`div.o_group`).toHaveCount(0);
});

test(`invisible attrs with zero value in expression and unset value in data`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="foo"/>
                    <group invisible='float_field == 0.0'>
                        <div class="hello">this should be invisible</div>
                        <field name="float_field"/>
                    </group>
                </sheet>
            </form>
        `,
    });
    expect(`div.hello`).toHaveCount(0);
});

test(`reset local state when switching to another view`, async () => {
    Partner._views = {
        form: `
            <form>
                <sheet>
                    <field name="product_id"/>
                    <notebook>
                        <page string="Foo">
                            <field name="foo"/>
                        </page>
                        <page string="Bar">
                            <field name="bar"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        list: `<list><field name="foo"/></list>`,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(`.o_control_panel_main_buttons button.o_list_button_add`).click();
    expect(`.o_form_view`).toHaveCount(1);
    // sanity check: notebook active page is first page
    expect(`.o_notebook .nav-link:eq(0)`).toHaveClass("active");

    // click on second page tab
    await contains(`.o_notebook .nav-link:eq(1)`).click();
    expect(`.o_notebook .nav-link:eq(1)`).toHaveClass("active");

    await contains(`.o_control_panel .o_form_button_cancel`).click();
    expect(`.o_form_view`).toHaveCount(0);

    await contains(`.o_control_panel_main_buttons button.o_list_button_add`).click();
    expect(`.o_form_view`).toHaveCount(1);
    // check notebook active page is first page again
    expect(`.o_notebook .nav-link:eq(0)`).toHaveClass("active");
});

test.tags("desktop");
test(`trying to leave an invalid form view should not change the navbar`, async () => {
    defineMenus([
        {
            id: "root",
            children: [
                { id: 1, children: [], name: "App0", appID: 1, xmlid: "menu_1", actionID: 1 },
                { id: 2, children: [], name: "App1", appID: 2, xmlid: "menu_2", actionID: 2 },
            ],
            name: "root",
            appID: "root",
        },
    ]);

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
        {
            id: 2,
            name: "Product",
            res_model: "product",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    ]);

    Partner._views = {
        form: `
            <form>
                <sheet>
                    <field name="name" required="1"/>
                    <field name="foo"/>
                </sheet>
            </form>
        `,
        search: `<search/>`,
    };
    Product._views = {
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
    };

    await mountWithCleanup(WebClient);
    await animationFrame();
    await getService("action").doAction(1);
    expect(`.o_main_navbar .o_menu_brand`).toHaveText("App0");

    await contains(`[name='foo'] input`).edit("blop");
    await contains(`.o_navbar_apps_menu button`).click();
    await contains(`.o-dropdown--menu .dropdown-item[data-section='2']`).click();
    await animationFrame();
    expect(`.o_main_navbar .o_menu_brand`).toHaveText("App0");

    await contains(`[name='name'] input`).edit("blop");
    await contains(`.o_navbar_apps_menu button`).click();
    await contains(`.o-dropdown--menu .dropdown-item[data-section='2']`).click();
    await animationFrame();
    expect(`.o_main_navbar .o_menu_brand`).toHaveText("App1");
});

test.tags("desktop")(`rendering stat buttons with action on desktop`, async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step("doActionButton");
            expect(params.name).toBe("someaction");
            expect(params.type).toBe("action");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button class="oe_stat_button" type="action" name="someaction">
                            <field name="int_field"/>
                        </button>
                        <button class="oe_stat_button" name="some_action" type="action" invisible='bar'>
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button.oe_stat_button`).toHaveCount(1);

    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("mobile")(`rendering stat buttons with action on mobile`, async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step("doActionButton");
            expect(params.name).toBe("someaction");
            expect(params.type).toBe("action");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button class="oe_stat_button" type="action" name="someaction">
                            <field name="int_field"/>
                        </button>
                        <button class="oe_stat_button" name="some_action" type="action" invisible='bar'>
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    expect(`button.oe_stat_button`).toHaveCount(1);

    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("desktop")(`rendering stat buttons without class on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button>
                            <field name="int_field"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button.oe_stat_button`).toHaveCount(1);
});

test.tags("mobile")(`rendering stat buttons without class on mobile`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button>
                            <field name="int_field"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    expect(`button.oe_stat_button`).toHaveCount(1);
});

test.tags("desktop")(`rendering stat buttons without action on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button class="oe_stat_button">
                            <field name="int_field"/>
                        </button>
                        <button class="oe_stat_button" name="some_action" type="action" invisible='bar'>
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button.oe_stat_button[disabled]`).toHaveCount(1);
});

test.tags("mobile")(`rendering stat buttons without action on mobile`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button class="oe_stat_button">
                            <field name="int_field"/>
                        </button>
                        <button class="oe_stat_button" name="some_action" type="action" invisible='bar'>
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    expect(`button.oe_stat_button[disabled]`).toHaveCount(1);
});

test.tags("desktop")(`readonly stat buttons stays disabled on desktop`, async () => {
    mockService("action", {
        async doActionButton(params) {
            if (params.name == "action_to_perform") {
                expect.step("action_to_perform");
                expect(`button.oe_stat_button[disabled]`).toHaveCount(2, {
                    message: "While performing the action, both buttons should be disabled.",
                });
            }
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button class="oe_stat_button">
                            <field name="int_field"/>
                        </button>
                        <button class="oe_stat_button" type="action" name="some_action">
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <button type="action" name="action_to_perform">Run an action</button>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button.oe_stat_button`).toHaveCount(2);
    expect(`button.oe_stat_button[disabled]`).toHaveCount(1);

    await contains(`button[name=action_to_perform]`).click();
    expect(`button.oe_stat_button[disabled]`).toHaveCount(1, {
        message: "After performing the action, only one button should be disabled.",
    });
    expect.verifySteps(["action_to_perform"]);
});

test.tags("mobile")(`readonly stat buttons stays disabled on mobile`, async () => {
    mockService("action", {
        async doActionButton(params) {
            if (params.name == "action_to_perform") {
                expect.step("action_to_perform");
            }
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button class="oe_stat_button">
                            <field name="int_field"/>
                        </button>
                        <button class="oe_stat_button" type="action" name="some_action">
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <button type="action" name="action_to_perform">Run an action</button>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    expect(`button.oe_stat_button`).toHaveCount(2);
    expect(`button.oe_stat_button[disabled]`).toHaveCount(1);

    await contains(`button[name=action_to_perform]`).click();
    await contains(".o-form-buttonbox .o_button_more").click();
    expect(`button.oe_stat_button[disabled]`).toHaveCount(1, {
        message: "After performing the action, only one button should be disabled.",
    });
    expect.verifySteps(["action_to_perform"]);
});

test(`label with no string attribute gets the default label for the corresponding field`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <label for="bar"/>
                        <div>
                            <field name="bar"/>
                        </div>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`label.o_form_label`).toHaveCount(1);
    expect(`label.o_form_label`).toHaveText("Bar");
});

test(`label uses the string attribute when present`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <label for="bar" string="customstring"/>
                        <div>
                            <field name="bar"/>
                        </div>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`label.o_form_label`).toHaveCount(1);
    expect(`label.o_form_label`).toHaveText("customstring");
});

test(`label ignores the content of the label when present`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <label for="bar">customstring</label>
                        <div>
                            <field name="bar"/>
                        </div>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`label.o_form_label`).toHaveCount(1);
    expect(`label.o_form_label`).toHaveText("Bar");
});

test(`label with empty string attribute renders to an empty label`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <label for="bar" string=""/>
                        <div>
                            <field name="bar"/>
                        </div>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`label.o_form_label`).toHaveCount(1);
    expect(`label.o_form_label`).toHaveText("");
});

test(`two mutually exclusive labels with a dynamic invisible attribute`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <label for="bar" string="label1" invisible='bar'/>
                        <label for="bar" string="label2" invisible='not bar'/>
                        <field name="bar" nolabel="1"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`label.o_form_label`).toHaveCount(1);
    expect(`label.o_form_label`).toHaveText("label2");
    expect(`.o_inner_group > div`).toHaveCount(1);
});

test(`label is not rendered when invisible and not at top-level in a group`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <div>
                            <label for="bar" invisible='bar'/>
                            <field name="bar" />
                        </div>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`label.o_form_label`).toHaveCount(0);
});

test(`input ids for multiple occurrences of fields in form view`, async () => {
    // A same field can occur several times in the view, but its id must be
    // unique by occurrence, otherwise there is a warning in the console (in
    // edit mode) as we get several inputs with the same "id" attribute, and
    // several labels the same "for" attribute.
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo"/>
                    <label for="float_field"/>
                    <div><field name="float_field"/></div>
                </group>
                <group>
                    <field name="foo"/>
                    <label for="float_field2"/>
                    <div><field name="float_field" id="float_field2"/></div>
                </group>
            </form>
        `,
    });
    const fieldIdAttrs = queryAllAttributes(`.o_field_widget input`, "id");
    const labelForAttrs = queryAllAttributes(`.o_form_label`, "for");
    expect(new Set(fieldIdAttrs)).toHaveLength(4);
    expect(fieldIdAttrs).toEqual(labelForAttrs);
});

test(`input ids for multiple occurrences of fields in sub form view (inline)`, async () => {
    // A same field can occur several times in the view, but its id must be
    // unique by occurrence, otherwise there is a warning in the console (in
    // edit mode) as we get several inputs with the same "id" attribute, and
    // several labels the same "for" attribute.
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list><field name="foo"/></list>
                    <form>
                        <group>
                            <field name="foo"/>
                            <label for="float_field"/>
                            <div><field name="float_field"/></div>
                        </group>
                        <group>
                            <field name="foo"/>
                            <label for="float_field2"/>
                            <div><field name="float_field" id="float_field2"/></div>
                        </group>
                    </form>
                </field>
            </form>
        `,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();
    const fieldIdAttrs = queryAllAttributes(`.modal .o_form_view .o_field_widget input`, "id");
    const labelForAttrs = queryAllAttributes(`.modal .o_form_view .o_form_label`, "for");
    expect(new Set(fieldIdAttrs)).toHaveLength(4);
    expect(fieldIdAttrs).toEqual(labelForAttrs);
});

test.tags("desktop");
test(`input ids for multiple occurrences of fields in sub form view (not inline)`, async () => {
    // A same field can occur several times in the view, but its id must be
    // unique by occurrence, otherwise there is a warning in the console (in
    // edit mode) as we get several inputs with the same "id" attribute, and
    // several labels the same "for" attribute.
    Partner._views = {
        list: `<list><field name="foo"/></list>`,
        form: `
                <form>
                    <group>
                        <field name="foo"/>
                        <label for="float_field"/>
                        <div><field name="float_field"/></div>
                    </group>
                    <group>
                        <field name="foo"/>
                        <label for="float_field2"/>
                        <div><field name="float_field" id="float_field2"/></div>
                    </group>
                </form>
            `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="child_ids" widget="one2many"/></form>`,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();
    const fieldIdAttrs = queryAllAttributes(`.modal .o_form_view .o_field_widget input`, "id");
    const labelForAttrs = queryAllAttributes(`.modal .o_form_view .o_form_label`, "for");
    expect(new Set(fieldIdAttrs)).toHaveLength(4);
    expect(fieldIdAttrs).toEqual(labelForAttrs);
});

test(`two occurrences of invalid field in form view`, async () => {
    Partner._fields.parent_id = fields.Many2one({ relation: "partner", required: true });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="parent_id"/>
                    <field name="parent_id"/>
                </group>
            </form>
        `,
    });
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_label.o_field_invalid`).toHaveCount(2);
    expect(`.o_field_many2one.o_field_invalid`).toHaveCount(2);
});

test(`two occurrences of invalid integer fields in form view`, async () => {
    Partner._fields.parent_id = fields.Many2one({ relation: "partner", required: true });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="int_field" class="a"/>
                    <field name="int_field" class="b"/>
                </group>
            </form>
        `,
    });
    await contains(`.a input`).edit("abc");
    expect(`.o_form_label.o_field_invalid`).toHaveCount(2);
    expect(`.o_field_integer.o_field_invalid`).toHaveCount(2);

    await contains(`.b input`).edit("10");
    expect(`.o_form_label.o_field_invalid`).toHaveCount(0);
    expect(`.o_field_integer.o_field_invalid`).toHaveCount(0);
});

test(`mutually exclusive required fields in form view`, async () => {
    delete Partner._fields.foo.default;

    onRpc("web_save", () => expect.step("saved"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo" required="not name"/>
                    <field name="name" required="not foo"/>
                </group>
            </form>
        `,
        resId: 1,
    });

    await contains(".o_field_widget[name=foo] input").edit("");
    await contains(".o_field_widget[name=name] input").edit("");

    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget.o_field_invalid`).toHaveCount(2);
    expect(`.o_form_button_save`).toHaveAttribute("disabled");

    await contains(`.o_field_widget[name=foo] input`).edit("some value");
    expect(`.o_field_widget.o_field_invalid`).toHaveCount(0);
    expect(`.o_form_button_save`).not.toHaveAttribute("disabled");

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["saved"]);
});

test(`twice same field with different required attributes`, async () => {
    Partner._fields.foo = fields.Char();

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="bar"/>
                    <field name="int_field"/>
                    <field name="foo" required="not bar"/>
                    <field name="foo" required="int_field == 44"/>
                </group>
            </form>
        `,
    });
    expect(`.o_field_widget[name=foo]:eq(0)`).toHaveClass("o_required_modifier");
    expect(`.o_field_widget[name=foo]:eq(1)`).not.toHaveClass("o_required_modifier");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_field_widget[name=foo]:eq(0)`).not.toHaveClass("o_required_modifier");
    expect(`.o_field_widget[name=foo]:eq(1)`).not.toHaveClass("o_required_modifier");

    await contains(`.o_field_widget[name=int_field] input`).edit("44");
    expect(`.o_field_widget[name=foo]:eq(0)`).not.toHaveClass("o_required_modifier");
    expect(`.o_field_widget[name=foo]:eq(1)`).toHaveClass("o_required_modifier");

    await contains(`.o_form_button_save`).click();
    expect(`.o_form_label.o_field_invalid`).toHaveCount(2);
    expect(`.o_field_widget.o_field_invalid`).toHaveCount(2);
    expect.verifySteps(["get_views", "onchange"]);
});

test(`twice same field with different readonly attributes`, async () => {
    Partner._fields.foo = fields.Char();

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({
            bar: true,
            int_field: 0,
            foo: "some value",
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="bar"/>
                    <field name="int_field"/>
                    <field name="foo" readonly="not bar"/>
                    <field name="foo" readonly="int_field == 0"/>
                </group>
            </form>
        `,
    });
    expect(`.o_field_widget[name=foo]:eq(0)`).toHaveClass("o_readonly_modifier");
    expect(`.o_field_widget[name=foo]:eq(1)`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_field_widget[name=foo]:eq(0)`).not.toHaveClass("o_readonly_modifier");
    expect(`.o_field_widget[name=foo]:eq(1)`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_widget[name=foo] input`).edit("some value");
    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("some value");
    expect.verifySteps(["web_save"]);
});

test(`twice same field with different invisible attributes`, async () => {
    Partner._fields.foo = fields.Char();

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="bar"/>
                    <field name="int_field"/>
                    <field name="foo" required="1" invisible="not bar"/>
                    <field name="foo" invisible="int_field == 0"/>
                </group>
            </form>
        `,
    });
    expect(`.o_field_widget[name=foo]`).toHaveCount(0);

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_field_widget[name=foo]`).toHaveCount(1);

    // foo is required, and as it isn't invisible (at least for one occurrence), it shouldn't
    // allow to save as it is not set
    await contains(`.o_form_button_save`).click();
    expect(".o_field_widget[name=foo]").toHaveClass("o_field_invalid");
    expect.verifySteps(["get_views", "onchange"]);
});

test(`required field computed by another field in a form view`, async () => {
    Partner._fields.foo = fields.Char({
        onChange(record) {
            if (record.foo) {
                record.name = "plop";
            }
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="name" required="1"/>
                <field name="foo"/>
            </form>
        `,
    });
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_invalid`).toHaveCount(1);

    await contains(`[name='foo'] input`).edit("hello");
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_invalid`).toHaveCount(0);
});

test(`required field computed by another field in a x2m`, async () => {
    Partner._fields.foo = fields.Char({
        default: false,
        onChange(record) {
            if (record.foo) {
                record.name = "plop";
            }
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="bottom">
                        <field name="foo"/>
                        <field name="int_field"/>
                        <field name="name" required="1"/>
                    </list>
                </field>
            </form>
        `,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_data_row [name='int_field'] input`).edit("1");
    await contains(".o_form_view").click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_selected_row`).toHaveCount(1);
    expect(`.o_field_invalid`).toHaveCount(1);

    await contains(`.o_data_row [name='foo'] input`).edit("hello");
    await contains(".o_form_view").click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_selected_row`).toHaveCount(0);
    expect(`.o_field_invalid`).toHaveCount(0);
});

test.tags("desktop")(`tooltips on multiple occurrences of fields and labels`, async () => {
    Partner._fields.foo = fields.Char({ help: "foo tooltip" });
    Partner._fields.bar = fields.Boolean({ help: "bar tooltip" });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo"/>
                    <label for="bar"/>
                    <div><field name="bar"/></div>
                </group>
                <group>
                    <field name="foo"/>
                    <label for="bar2"/>
                    <div><field name="bar" id="bar2"/></div>
                </group>
            </form>
        `,
    });
    await hover(".o_form_label[for=foo_0] sup");
    await runAllTimers();
    await animationFrame();
    expect(".o-tooltip .o-tooltip--help").toHaveText("foo tooltip");

    await hover(".o_form_label[for=bar_0] sup");
    await runAllTimers();
    await animationFrame();
    expect(".o-tooltip .o-tooltip--help").toHaveText("bar tooltip");

    await hover(".o_form_label[for=foo_1] sup");
    await runAllTimers();
    await animationFrame();
    expect(".o-tooltip .o-tooltip--help").toHaveText("foo tooltip");

    await hover(".o_form_label[for=bar_1] sup");
    await runAllTimers();
    await animationFrame();
    expect(".o-tooltip .o-tooltip--help").toHaveText("bar tooltip");
});

test(`readonly attrs on fields are re-evaluated on field change`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" readonly="bar"/>
                        <field name="bar"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_widget[name="foo"]`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_boolean input`).click();
    expect(`.o_field_widget[name="foo"]`).not.toHaveClass("o_readonly_modifier");

    await contains(`.o_field_boolean input`).click();
    expect(`.o_field_widget[name="foo"]`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_boolean input`).click();
    expect(`.o_field_widget[name="foo"]`).not.toHaveClass("o_readonly_modifier");
});

test(`field with readonly modifier depending on id`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field" readonly="id"/></form>`,
    });
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget[name=int_field] input`).toHaveCount(1);
    expect(`.o_field_widget[name=int_field]`).not.toHaveClass("o_readonly_modifier");

    await contains(`.o_field_widget[name=int_field] input`).edit("34");
    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name=int_field]`).toHaveText("34");

    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget[name=int_field] input`).toHaveCount(0);
    expect(`.o_field_widget[name=int_field]`).toHaveClass("o_readonly_modifier");
});

test.tags("desktop")(`readonly attrs on lines are re-evaluated on field change 2`, async () => {
    Partner._records[0].product_ids = [37];
    Partner._records[0].parent_id = false;

    let onchangeApplied = false;
    Partner._fields.parent_id = fields.Many2one({
        relation: "partner",
        onChange(record) {
            // when parent_id changes, push another record in product_ids.
            // only push a second record once.
            if (!onchangeApplied) {
                record.product_ids = [[37, 41]];
                onchangeApplied = true;
            }
        },
    });

    Product._records[0].name = "test";
    // This one is necessary to have a valid, rendered widget
    Product._fields.int_field = fields.Integer();

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="parent_id"/>
                <field name="product_ids" readonly="not parent_id">
                    <list editable="top"><field name="int_field" widget="handle"/><field name="name"/></list>
                </field>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_field_many2one[name="parent_id"] input`).click();
    await contains(`.dropdown .dropdown-item:contains(first record)`).click();
    expect(`.o_field_one2many[name="product_ids"]`).not.toHaveClass("o_readonly_modifier");

    await clear();
    await click(`.o_content`); // blur input to trigger change
    await animationFrame();
    expect(`.o_field_one2many[name="product_ids"]`).toHaveClass("o_readonly_modifier");

    await contains(`.o_field_many2one[name="parent_id"] input`).click();
    await contains(`.dropdown .dropdown-item:contains(second record)`).click();
    expect(`.o_field_one2many[name="product_ids"]`).not.toHaveClass("o_readonly_modifier");

    await clear();
    await click(`.o_content`); // blur input to trigger change
    await animationFrame();
    expect(`.o_field_one2many[name="product_ids"]`).toHaveClass("o_readonly_modifier");
});

test(`empty fields have o_form_empty class in readonly mode`, async () => {
    Partner._records[1].foo = false; // 1 is record with id=2
    Partner._records[1].parent_id = false; // 1 is record with id=2
    Partner._fields.foo = fields.Char({
        onChange(record) {
            if (record.foo === "hello") {
                record.int_field = false;
            }
        },
    });
    Partner._fields.int_field = fields.Integer({ readonly: true });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo"/>
                        <field name="parent_id" readonly="not foo"/>
                        <field name="int_field"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_empty`).toHaveCount(1);
    expect(`.o_form_label_empty`).toHaveCount(1);

    await contains(`.o_field_widget[name=foo] input`).edit("test");
    expect(`.o_field_empty`).toHaveCount(0);
    expect(`.o_form_label_empty`).toHaveCount(0);

    await contains(`.o_field_widget[name=foo] input`).edit("hello");
    expect(`.o_field_empty`).toHaveCount(1);
    expect(`.o_form_label_empty`).toHaveCount(1);
});

test(`empty fields' labels still get the empty class after widget rerender`, async () => {
    Partner._fields.foo = fields.Char();
    Partner._records[1].foo = false; // 1 is record with id=2
    Partner._records[1].name = false; // 1 is record with id=2

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo"/>
                    <field name="name" readonly="foo == 'readonly'"/>
                </group>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_empty`).toHaveCount(0);
    expect(`.o_form_label_empty`).toHaveCount(0);

    await contains(`.o_field_widget[name=foo] input`).edit("readonly");
    await contains(`.o_field_widget[name=foo] input`).edit("edit");
    await contains(`.o_field_widget[name=name] input`).edit("some name");
    await contains(`.o_field_widget[name=foo] input`).edit("readonly");
    expect(`.o_field_empty`).toHaveCount(0);
    expect(`.o_form_label_empty`).toHaveCount(0);
});

test(`empty inner readonly fields don't have o_form_empty class in "create" mode`, async () => {
    Partner._fields.product_id = fields.Many2one({ relation: "product", readonly: true });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <group>
                            <field name="product_id"/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
    });
    expect(`.o_form_label_empty`).toHaveCount(0);
    expect(`.o_field_empty`).toHaveCount(0);
});

test(`label tag added for fields have o_form_empty class in readonly mode if field is empty`, async () => {
    Partner._fields.foo = fields.Char({
        onChange(record) {
            if (record.foo === "hello") {
                record.int_field = false;
            }
        },
    });
    Partner._fields.int_field = fields.Integer({ readonly: true });
    Partner._records[1].foo = false; // 1 is record with id=2
    Partner._records[1].parent_id = false; // 1 is record with id=2

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <label for="foo" string="Foo"/>
                    <field name="foo"/>
                    <label for="parent_id" string="parent_id" readonly="not foo"/>
                    <field name="parent_id" readonly="not foo"/>
                    <label for="int_field" string="IntField" readonly="not int_field"/>
                    <field name="int_field"/>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(".o_field_empty").toHaveCount(1);
    expect(".o_form_label_empty").toHaveCount(1);

    await contains(`div[name=foo] input`).edit("test");
    expect(`.o_field_empty`).toHaveCount(0);
    expect(`.o_form_label_empty`).toHaveCount(0);

    await contains(`div[name=foo] input`).edit("hello");
    expect(`.o_field_empty`).toHaveCount(1);
    expect(`.o_form_label_empty`).toHaveCount(1);
});

test(`required attrs on fields are re-evaluated on field change`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" required="bar"/>
                        <field name="bar"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_widget[name="foo"]`).toHaveClass("o_required_modifier");

    await contains(`.o_field_boolean input`).uncheck();
    expect(`.o_field_widget[name="foo"]`).not.toHaveClass("o_required_modifier");

    await contains(`.o_field_boolean input`).check();
    expect(`.o_field_widget[name="foo"]`).toHaveClass("o_required_modifier");
});

test(`required fields should have o_required_modifier`, async () => {
    Partner._fields.foo = fields.Char({ required: true });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_widget`).toHaveClass("o_required_modifier");
});

test(`required float fields works as expected`, async () => {
    Partner._fields.float_field = fields.Float({ required: true });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="float_field"/>
                    </group>
                </sheet>
            </form>
        `,
    });
    expect(`.o_field_widget[name="float_field"]`).toHaveClass("o_required_modifier");
    expect(`.o_field_widget[name="float_field"] input`).toHaveValue("0.00");

    await contains(`.o_form_button_save`).click();
    await contains(`.o_field_widget[name="float_field"] input`).edit("1");
    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name="float_field"] input`).toHaveValue("1.00");
    expect.verifySteps(["get_views", "onchange", "web_save", "web_save"]);
});

test(`separators`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                <group>
                    <separator string="Geolocation"/>
                    <field name="foo"/>
                </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`div.o_horizontal_separator`).toHaveCount(1);
});

test(`invisible attrs on separators`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <separator string="Geolocation" invisible="bar"/>
                        <field name="bar"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`div.o_horizontal_separator`).toHaveCount(0);
});

test(`form views in dialogs do not have a control panel`, async () => {
    Partner._views = {
        form: `<form><field name="foo"/></form>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_dialog .o_form_view`).toHaveCount(1);
    expect(`.o_dialog .o_form_view .o_control_panel`).toHaveCount(0);
});

test(`form views in dialogs do not add display_name field`, async () => {
    Partner._views = {
        form: `<form><field name="foo"/></form>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        },
    ]);

    onRpc("onchange", ({ args }) => {
        expect.step("onchange");
        expect(args[3]).toEqual({ foo: {} });
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_dialog .o_form_view`).toHaveCount(1);
    expect(`.o_dialog .o_form_view .o_control_panel`).toHaveCount(0);
    expect.verifySteps(["onchange"]);
});

test(`form views in dialogs closes on save`, async () => {
    Partner._fields.foo = fields.Char();
    Partner._records[0].foo = undefined;
    Partner._views = {
        form: `<form><field name="foo" required="1"/></form>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_dialog .o_form_view`).toHaveCount(1);

    await contains(`.o_dialog .o_form_button_save`).click();
    expect(`.o_dialog .o_form_view`).toHaveCount(1);

    await contains(`[name="foo"] input`).edit("Gizmo");
    await contains(`.o_dialog .o_form_button_save`).click();
    expect(`.o_dialog .o_form_view`).toHaveCount(0);
});

test(`form views in dialogs closes on discard on existing record`, async () => {
    Partner._fields.foo = fields.Char();
    Partner._records[0].foo = undefined;
    Partner._views = {
        form: `<form><field name="foo" required="1"/></form>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
            res_id: 1,
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_dialog .o_form_view`).toHaveCount(1);

    await contains(`.o_dialog .o_form_button_cancel`).click();
    expect(`.o_dialog .o_form_view`).toHaveCount(0);
});

test(`form views in dialogs do not have class o_xxl_form_view`, async () => {
    const bus = new EventBus();
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            value: false,
        });
        return {
            activateElement() {},
            deactivateElement() {},
            bus,
            size: SIZES.XXL,
            isSmall: false,
        };
    });

    Partner._views = {
        form: `<form><field name="foo"/></form>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_dialog .o_form_view`).toHaveCount(1);
    expect(`.o_dialog .o_form_view`).not.toHaveClass("o_xxl_form_view");
});

test.tags("desktop")(`buttons in form view`, async () => {
    expect.errors(1);

    mockService("action", {
        doActionButton(params) {
            expect.step(params.name);
            if (params.name === "post") {
                expect(params.resId).toBe(2);
                params.onClose();
            } else {
                throw makeServerError({ message: "doActionButton error" });
            }
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="state" invisible="1"/>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                    <button name="some_method" class="s" string="Do it" type="object"/>
                    <button name="some_other_method" invisible="state not in ['ab', 'ef']" string="Do not" type="object"/>
                </header>
                <sheet>
                    <group>
                        <button string="Geolocate" name="geo_localize" icon="fa-check" type="object"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button.btn i.fa.fa-check`).toHaveCount(1);
    expect(`.o_form_statusbar button`).toHaveCount(2);
    expect(`button.child_ids[name="post"]:contains(Confirm)`).toHaveCount(1);

    // click on p (will succeed and reload)
    await contains(`.o_form_statusbar button.child_ids`).click();
    expect.verifyErrors([]);

    // click on s (will fail)
    await contains(`.o_form_statusbar button.s`).click();
    expect.verifySteps([
        "get_views",
        "web_read", // initial read
        "post",
        "web_read", // reload (successfully clicked on p)
        "some_method",
    ]);
    expect.verifyErrors(["doActionButton error"]);
});

test.tags("desktop")(`buttons classes in form view`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="0"/>
                    <button name="1" class="btn-primary"/>
                    <button name="2" class="oe_highlight"/>
                    <button name="3" class="btn-secondary"/>
                    <button name="4" class="btn-link"/>
                    <button name="5" class="oe_link"/>
                    <button name="6" class="btn-success"/>
                    <button name="7" class="o_this_is_a_button"/>
                </header>
                <sheet>
                    <button name="8"/>
                    <button name="9" class="btn-primary"/>
                    <button name="10" class="oe_highlight"/>
                    <button name="11" class="btn-secondary"/>
                    <button name="12" class="btn-link"/>
                    <button name="13" class="oe_link"/>
                    <button name="14" class="btn-success"/>
                    <button name="15" class="o_this_is_a_button"/>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button[name="0"]`).toHaveClass("btn btn-secondary");
    expect(`button[name="1"]`).toHaveClass("btn btn-primary");
    expect(`button[name="2"]`).toHaveClass("btn btn-primary");
    expect(`button[name="3"]`).toHaveClass("btn btn-secondary");
    expect(`button[name="4"]`).toHaveClass("btn btn-link");
    expect(`button[name="5"]`).toHaveClass("btn btn-link");
    expect(`button[name="6"]`).toHaveClass("btn btn-success");
    expect(`button[name="7"]`).toHaveClass("btn o_this_is_a_button btn-secondary");
    expect(`button[name="8"]`).toHaveClass("btn btn-secondary");
    expect(`button[name="9"]`).toHaveClass("btn btn-primary");
    expect(`button[name="10"]`).toHaveClass("btn btn-primary");
    expect(`button[name="11"]`).toHaveClass("btn btn-secondary");
    expect(`button[name="12"]`).toHaveClass("btn btn-link");
    expect(`button[name="13"]`).toHaveClass("btn btn-link");
    expect(`button[name="14"]`).toHaveClass("btn btn-success");
    expect(`button[name="15"]`).toHaveClass("btn o_this_is_a_button");
});

test.tags("desktop");
test(`buttons should be in .o_statusbar_buttons in form view header on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="0"/>
                    <field name="foo" widget="url" class="btn btn-secondary" text="My Button" readonly="1"/>
                </header>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_statusbar_buttons > button:eq(0)`).toHaveAttribute("name", "0");
    expect(`.o_statusbar_buttons > div:eq(0)`).toHaveAttribute("name", "foo");
});

test.tags("mobile")(`buttons should be in CogMenu in form view header on mobile`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="0"/>
                    <field name="foo" widget="url" class="btn btn-secondary" text="My Button" readonly="1"/>
                </header>
            </form>
        `,
        resId: 2,
    });

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    expect(`.o-dropdown-item-unstyled-button > button`).toHaveAttribute("name", "0");
    expect(`.o-dropdown-item-unstyled-button > div`).toHaveAttribute("name", "foo");
});

test(`button in form view and long willStart`, async () => {
    let rpcCount = 0;
    class AsyncField extends CharField {
        setup() {
            onWillStart(async () => {
                expect.step("willStart");
            });
        }
    }
    fieldsRegistry.add("asyncwidget", { component: AsyncField });

    onRpc("web_read", () => {
        rpcCount++;
        expect.step(`web_read${rpcCount}`);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="state" invisible="1"/>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                </header>
                <sheet>
                    <group>
                        <field name="foo" widget="asyncwidget"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps(["web_read1", "willStart"]);
});

test.tags("desktop")(`button in form view and long willStart on desktop`, async () => {
    mockService("action", {
        doActionButton(params) {
            params.onClose();
        },
    });

    let rpcCount = 0;
    class AsyncField extends CharField {
        setup() {
            onWillUpdateProps(async () => {
                expect.step("willUpdateProps");
                if (rpcCount === 1) {
                    return new Promise(() => {});
                }
            });
        }
    }
    fieldsRegistry.add("asyncwidget", { component: AsyncField });

    onRpc("web_read", () => {
        rpcCount++;
        expect.step(`web_read${rpcCount}`);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="state" invisible="1"/>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                </header>
                <sheet>
                    <group>
                        <field name="foo" widget="asyncwidget"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps(["web_read1"]);

    await contains(`.o_form_statusbar button.child_ids`).click();
    expect.verifySteps(["web_read2", "willUpdateProps"]);

    await contains(`.o_form_statusbar button.child_ids`).click();
    expect.verifySteps(["web_read3", "willUpdateProps"]);
});

test.tags("mobile")(`button in form view and long willStart on mobile`, async () => {
    mockService("action", {
        doActionButton(params) {
            params.onClose();
        },
    });

    let rpcCount = 0;
    class AsyncField extends CharField {
        setup() {
            onWillUpdateProps(async () => {
                expect.step("willUpdateProps");
                if (rpcCount === 1) {
                    return new Promise(() => {});
                }
            });
        }
    }
    fieldsRegistry.add("asyncwidget", { component: AsyncField });

    onRpc("web_read", () => {
        rpcCount++;
        expect.step(`web_read${rpcCount}`);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="state" invisible="1"/>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                </header>
                <sheet>
                    <group>
                        <field name="foo" widget="asyncwidget"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps(["web_read1"]);

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(`.o-dropdown-item-unstyled-button button.child_ids`).click();
    expect.verifySteps(["web_read2", "willUpdateProps"]);

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(`.o-dropdown-item-unstyled-button button.child_ids`).click();
    expect.verifySteps(["web_read3", "willUpdateProps"]);
});

test.tags("desktop")(`buttons in form view, new record`, async () => {
    // this test simulates a situation similar to the settings forms.

    let resId = null;
    mockService("action", {
        doActionButton(params) {
            expect.step("execute_action");
            expect(params.resId).toBe(resId);
            params.onClose();
        },
    });

    onRpc("web_save", ({ parent }) => {
        const result = parent();
        resId = result[0].id;
        return result;
    });
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                    <button name="some_method" class="s" string="Do it" type="object"/>
                </header>
                <sheet>
                    <group>
                        <button string="Geolocate" name="geo_localize" icon="fa-check" type="object"/>
                    </group>
                </sheet>
            </form>
        `,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_form_statusbar button.child_ids`).click();
    expect.verifySteps(["web_save", "execute_action", "web_read"]);
});

test.tags("desktop");
test(`buttons in form view, new record, with field id in view on desktop`, async () => {
    // buttons in form view are one of the rare example of situation when we
    // save a record without reloading it immediately, because we only care
    // about its id for the next step.  But at some point, if the field id
    // is in the view, it was registered in the changes, and caused invalid
    // values in the record (data.id was set to null)

    let resId = null;
    mockService("action", {
        doActionButton(params) {
            expect.step("execute_action");
            expect(params.resId).toBe(resId);
            params.onClose();
        },
    });

    onRpc("web_save", ({ parent }) => {
        const result = parent();
        resId = result[0].id;
        return result;
    });
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                </header>
                <sheet>
                    <group>
                        <field name="id" invisible="1"/>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
    });
    await contains(`.o_form_statusbar button.child_ids`).click();
    expect.verifySteps(["get_views", "onchange", "web_save", "execute_action", "web_read"]);
});

test.tags("mobile");
test(`buttons in form view, new record, with field id in view on mobile`, async () => {
    // buttons in form view are one of the rare example of situation when we
    // save a record without reloading it immediately, because we only care
    // about its id for the next step.  But at some point, if the field id
    // is in the view, it was registered in the changes, and caused invalid
    // values in the record (data.id was set to null)

    let resId = null;
    mockService("action", {
        doActionButton(params) {
            expect.step("execute_action");
            expect(params.resId).toBe(resId);
            params.onClose();
        },
    });

    onRpc("web_save", ({ parent }) => {
        const result = parent();
        resId = result[0].id;
        return result;
    });
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                </header>
                <sheet>
                    <group>
                        <field name="id" invisible="1"/>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
    });

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(`.o-dropdown-item-unstyled-button button.child_ids`).click();
    expect.verifySteps(["get_views", "onchange", "web_save", "execute_action", "web_read"]);
});

test(`buttons with data-hotkey attribute`, async () => {
    mockService("action", {
        doActionButton(params) {
            expect.step(params.name);
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <button name="validate" string="Validate" type="object" data-hotkey="v"/>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_form_view button[data-hotkey=v]`).toHaveCount(1);

    await press(["alt", "v"]);
    await animationFrame();
    expect.verifySteps(["validate"]);
});

test(`change and save char`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].foo).toBe("tralala");
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><group><field name="foo"/></group></form>`,
        resId: 2,
    });
    expect(`.o_form_editable`).toHaveCount(1);

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`properly reload data from server`, async () => {
    onRpc("web_save", ({ args }) => {
        args[1].foo = "apple";
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><group><field name="foo"/></group></form>`,
        resId: 2,
    });
    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("apple");
});

test(`disable buttons until reload data from server`, async () => {
    let def = null;
    onRpc("web_save", async ({ args }) => {
        args[1].foo = "apple";
        await def;
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><group><field name="foo"/></group></form>`,
        resId: 2,
    });

    def = new Deferred();
    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(`.o_form_button_save`).click();

    expect(`.o_form_button_save`).not.toBeEnabled();
    expect(`.o_form_button_cancel`).not.toBeEnabled();

    def.resolve();
    await animationFrame();
    expect(`.o_form_button_save`).toBeEnabled();
    expect(`.o_form_button_cancel`).toBeEnabled();
});

test(`properly apply onchange in simple case`, async () => {
    Partner._onChanges = {
        foo(record) {
            record.int_field = record.foo.length + 1000;
        },
    };
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="int_field"/></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("9");

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("1,007");
});

test(`properly apply onchange when changed field is active field`, async () => {
    Partner._onChanges = {
        int_field(record) {
            record.int_field = 14;
        },
    };
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field"/></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("9");

    await contains(`.o_field_widget[name=int_field] input`).edit("666");
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("14");

    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("14");
});

test(`onchange send only the present fields to the server`, async () => {
    Partner._records[0].product_id = false;
    Partner._onChanges = {
        foo(record) {
            record.foo = record.foo + " alligator";
        },
    };
    PartnerType._views = {
        list: `<list><field name="name"/></list>`,
    };

    onRpc("onchange", ({ args }) => {
        expect.step("onchange");
        expect(args[3]).toEqual({
            display_name: {},
            foo: {},
            child_ids: {
                fields: {
                    bar: {},
                    product_id: {
                        fields: {
                            display_name: {},
                        },
                    },
                },
                limit: 40,
                order: "",
            },
            type_ids: {
                fields: {
                    name: {},
                },
                limit: 40,
                order: "",
            },
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="child_ids" widget="one2many">
                    <list>
                        <field name="bar"/>
                        <field name="product_id"/>
                    </list>
                </field>
                <field name="type_ids"/>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    expect.verifySteps(["onchange"]);
});

test(`onchange only send present fields value`, async () => {
    Partner._onChanges = {
        foo: () => {},
    };

    let checkOnchange = false;
    onRpc("onchange", ({ args }) => {
        if (!checkOnchange) {
            return;
        }
        expect.step("onchange");
        expect(args[1]).toEqual({
            foo: "tralala",
            child_ids: [[0, args[1].child_ids[0][1], { name: "valid line", float_field: 12.4 }]],
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="name"/>
                <field name="foo"/>
                <field name="child_ids">
                    <list editable="top">
                        <field name="name"/>
                        <field name="float_field"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });

    // add a o2m row
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_field_one2many .o_field_widget[name=name] input`).edit("valid line", {
        confirm: false,
    });
    await contains(`.o_field_one2many .o_field_widget[name=float_field] input`).edit("12.4", {
        confirm: false,
    });
    expect.verifySteps([]);

    // trigger an onchange by modifying foo
    checkOnchange = true;
    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    expect.verifySteps(["onchange"]);
});

test(`onchange send relation parent field values (including readonly)`, async () => {
    ResUsers._fields.login = fields.Char();
    ResUsers._onChanges = {
        name: (obj) => {
            // like computed field that depends on "name" field
            obj.login = obj.name.toLowerCase() + "@example.org";
        },
    };
    Partner._onChanges = {
        float_field: () => {},
    };

    let checkOnchange = false;
    onRpc("onchange", ({ args, kwargs }) => {
        if (!checkOnchange) {
            return;
        }
        expect(args[1]).toEqual({
            float_field: 12.4,
            user_id: {
                id: 17,
                name: "Test",
                login: "test@example.org",
                partner_ids: [[0, args[1].user_id.partner_ids[0][1], { float_field: 0 }]],
            },
        });
        expect.step("onchange");
    });

    await mountView({
        resModel: "res.users",
        type: "form",
        arch: `
            <form>
                <field name="name"/>
                <field name="login" readonly="True"/>
                <field name="partner_ids">
                    <list editable="top">
                        <field name="float_field"/>
                    </list>
                </field>
            </form>
        `,
        resId: 17,
    });

    // trigger an onchange that update a readonly field by modifying user name
    await contains(`.o_field_widget[name=name] input`).edit("Test");

    // add a o2m row
    await contains(`.o_field_x2many_list_row_add a`).click();
    expect.verifySteps([]);

    // trigger an onchange by modifying float_field
    checkOnchange = true;
    await contains(`.o_field_one2many .o_field_widget[name=float_field] input`).edit("12.4", {
        confirm: "tab",
    });
    expect.verifySteps(["onchange"]);
});

test(`evaluate in python field options`, async () => {
    class MyField extends Component {
        static props = ["*"];
        static template = xml`<div>ok</div>`;
        setup() {
            expect.step("setup");
            expect(this.props.horizontal).toBe(true);
        }
    }
    fieldsRegistry.add("my_field", {
        component: MyField,
        extractProps({ options }) {
            expect.step("extractProps");
            expect(options).toEqual({ horizontal: true });
            return { horizontal: options.horizontal };
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo" widget="my_field" options="{'horizontal': True}"/>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_field_widget`).toHaveText("ok");
    expect.verifySteps(["extractProps", "setup"]);
});

test(`can create a record with default values`, async () => {
    onRpc("web_save", ({ kwargs }) => {
        expect.step("web_save");
        expect(kwargs.context.active_field).toBe(2);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="bar"/>
            </form>
        `,
        resId: 1,
        context: { active_field: 2 },
    });

    const n = Partner._records.length;

    await contains(`.o_form_button_create`).click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_char input`).toHaveValue("My little Foo Value");

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
    expect(`.o_form_editable`).toHaveCount(1);
    expect(Partner._records).toHaveLength(n + 1);
});

test(`default record with a one2many and an onchange on sub field`, async () => {
    Partner._onChanges = {
        foo: () => {},
    };

    onRpc("onchange", ({ args }) => {
        expect.step("onchange");
        expect(args[3]).toEqual({
            display_name: {},
            child_ids: {
                fields: {
                    foo: {},
                },
                limit: 40,
                order: "",
            },
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids" widget="one2many">
                    <list><field name="foo"/></list>
                </field>
            </form>
        `,
    });
    expect.verifySteps(["onchange"]);
});

test(`remove default value in subviews`, async () => {
    Product._onchanges = {
        name: () => {},
    };

    const defaultContext = {
        lang: "en",
        tz: "taht",
        uid: 7,
        allowed_company_ids: [1],
    };

    onRpc("partner", "onchange", ({ kwargs }) => {
        expect.step(`onchange:partner`);
        expect(kwargs.context).toEqual({ ...defaultContext, default_state: "ab" });
    });
    onRpc("product", "onchange", ({ kwargs }) => {
        expect.step(`onchange:product`);
        expect(kwargs.context).toEqual({ ...defaultContext, default_product_uom_qty: 68 });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="product_ids" context="{'default_product_uom_qty': 68}">
                    <list editable="top">
                        <field name="name"/>
                    </list>
                </field>
            </form>
        `,
        context: { default_state: "ab" },
    });
    expect.verifySteps(["onchange:partner"]);

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect.verifySteps(["onchange:product"]);
});

test(`form with one2many with dynamic context`, async () => {
    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.specification).toEqual({
            display_name: {},
            int_field: {},
            child_ids: {
                fields: {
                    foo: {},
                },
                context: { static: 4 },
                limit: 40,
                order: "",
            },
        });
    });
    onRpc("onchange", ({ kwargs }) => {
        expect.step("onchange");
        expect(kwargs.context).toEqual({
            dynamic: 20,
            lang: "en",
            static: 4,
            tz: "taht",
            uid: 7,
            allowed_company_ids: [1],
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="int_field"/>
                <field name="child_ids" editable="bottom" context="{'static': 4, 'dynamic': int_field * 2}">
                    <list>
                        <field name="foo"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["web_read"]);

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect.verifySteps(["onchange"]);
});

test(`reference field in one2many list`, async () => {
    Partner._records[0].reference = "partner,2";
    Partner._views = {
        form: `<form><field name="name"/></form>`,
    };

    onRpc("get_formview_id", () => false);
    await mountViewInDialog({
        resModel: "res.users",
        type: "form",
        arch: `
            <form>
                <field name="name"/>
                <field name="partner_ids">
                    <list editable="bottom">
                        <field name="name"/>
                        <field name="reference"/>
                    </list>
                </field>
            </form>
        `,
        resId: 17,
    });
    await contains(`table td[data-tooltip="first record"]`).click();
    await contains(`table td button.o_external_button`, { visible: false }).click();
    await contains(`.o_dialog:not(.o_inactive_modal) .o_field_widget[name="name"] input`).edit(
        "New name"
    );
    await contains(`.o_dialog:not(.o_inactive_modal) footer .o_form_button_save`).click();
    expect(`.o_field_cell[data-tooltip="New name"]`).toHaveCount(1);
});

test(`there is an Actions menu when creating a new record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        actionMenus: {},
        resId: 1,
    });
    expect(`.o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_form_button_create`).click();
    expect(`.o_cp_action_menus`).toHaveCount(1);

    await contains(`.o_form_button_save`).click();
    expect(`.o_cp_action_menus`).toHaveCount(1);
});

test(`basic default record`, async () => {
    Partner._fields.foo = fields.Char({ default: "default foo value" });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
    });
    expect(`input`).toHaveValue("default foo value");
    expect.verifySteps(["get_views", "onchange"]);
});

test(`make default record with non empty one2many`, async () => {
    Partner._fields.child_ids = fields.One2many({
        relation: "partner",
        default: [
            [6, 0, []], // replace with zero ids
            [0, 0, { foo: "new foo1", product_id: 41, child_ids: [] }], // create a new value
            [0, 0, { foo: "new foo2", product_id: 37, child_ids: [] }], // create a new value
        ],
    });

    onRpc("read", ({ args }) => {
        if (args[1].length === 1 && args[1][0] === "display_name") {
            expect.step("read display_name");
        }
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list>
                        <field name="foo"/>
                        <field name="product_id"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect(`td:contains(new foo1)`).toHaveCount(1);
    expect(`td:contains(new foo2)`).toHaveCount(1);
    expect(`td:contains(xphone)`).toHaveCount(1);
    expect.verifySteps([]);
});

test(`make default record with non empty many2one`, async () => {
    Partner._fields.parent_id = fields.Many2one({ relation: "partner", default: 4 });

    onRpc("read", ({ args }) => {
        if (args[1].length === 1 && args[1][0] === "display_name") {
            throw new Error("Should not call display_name read");
        }
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="parent_id"/></form>`,
    });
    expect(`.o_field_widget[name="parent_id"] input`).toHaveValue("aaa");
    expect.verifySteps([]);
});

test(`form view properly change its title`, async () => {
    Partner._views = {
        form: `<form><field name="foo"/></form>`,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            res_id: 1,
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_breadcrumb`).toHaveText("first record");

    await contains(`.o_form_button_create`).click();
    expect(`.o_breadcrumb`).toHaveText("New");
});

test(`archive/unarchive a record`, async () => {
    // add active field on partner model to have archive option
    Partner._fields.active = fields.Boolean({ default: true });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="active"/><field name="foo"/></form>`,
        resId: 1,
        actionMenus: {},
    });
    expect(`.o_cp_action_menus`).toHaveCount(1);

    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(1);

    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal-footer .btn-primary`).click();
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Unarchive)`).toHaveCount(1);

    await toggleMenuItem("UnArchive");
    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(1);
    expect.verifySteps([
        "get_views",
        "web_read",
        "action_archive",
        "web_read",
        "action_unarchive",
        "web_read",
    ]);
});

test(`apply custom standard action menu (archive)`, async () => {
    // add active field on partner model to have archive option
    Partner._fields.active = fields.Boolean({ default: true });

    const formView = registry.category("views").get("form");
    class CustomFormController extends formView.Controller {
        getStaticActionMenuItems() {
            const menuItems = super.getStaticActionMenuItems();
            menuItems.archive.callback = () => {
                expect.step("customArchive");
            };
            return menuItems;
        }
    }
    registry.category("views").add("custom_form", {
        ...formView,
        Controller: CustomFormController,
    });
    after(() => {
        registry.category("views").remove("custom_form");
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form js_class="custom_form">
                <field name="active"/>
                <field name="foo"/>
            </form>
        `,
        resId: 1,
        actionMenus: {},
    });
    expect(`.o_cp_action_menus`).toHaveCount(1);

    await toggleActionMenu();
    expect(`.o-dropdown--menu span:contains(Archive)`).toHaveCount(1);

    await toggleMenuItem("Archive");
    expect.verifySteps(["customArchive"]);
});

test(`add custom static action menu`, async () => {
    const formView = registry.category("views").get("form");
    class CustomFormController extends formView.Controller {
        getStaticActionMenuItems() {
            const menuItems = super.getStaticActionMenuItems();
            menuItems.customAvailable = {
                isAvailable: () => true,
                description: "Custom Available",
                sequence: 35,
                callback: () => {
                    expect.step("Custom Available");
                },
            };
            menuItems.customNotAvailable = {
                isAvailable: () => false,
                description: "Custom Not Available",
                callback: () => {
                    expect.step("Custom Not Available");
                },
            };
            menuItems.customDefaultAvailable = {
                description: "Custom Default Available",
                callback: () => {
                    expect.step("Custom Default Available");
                },
            };
            return menuItems;
        }
    }
    registry.category("views").add("custom_form", {
        ...formView,
        Controller: CustomFormController,
    });
    after(() => {
        registry.category("views").remove("custom_form");
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form js_class="custom_form">
                <field name="foo"/>
            </form>
        `,
        resId: 1,
        actionMenus: {},
    });
    expect(`.o_cp_action_menus`).toHaveCount(1);

    await toggleActionMenu();
    expect(queryAllTexts`.o-dropdown--menu .dropdown-item`).toEqual([
        "Custom Default Available",
        "Duplicate",
        "Custom Available",
        "Delete",
    ]);

    await toggleMenuItem("Custom Available");
    expect.verifySteps(["Custom Available"]);

    await toggleActionMenu();
    await toggleMenuItem("Custom Default Available");
    expect.verifySteps(["Custom Default Available"]);
});

test(`archive a record with intermediary action`, async () => {
    // add active field on partner model to have archive option
    Partner._fields.active = fields.Char({ default: "true" });
    Partner._views = {
        form: `<form><field name="active"/><field name="foo"/></form>`,
        search: `<search/>`,
    };
    Product._views = {
        form: `
            <form>
                <field name="display_name" />
                <footer>
                    <button type="object" name="do_archive" class="myButton" />
                </footer>
            </form>
        `,
        search: `<search/>`,
    };

    let readPartner = 0;
    onRpc("do_archive", () => false);
    onRpc("action_archive", () => ({
        type: "ir.actions.act_window",
        res_model: "product",
        target: "new",
        views: [[false, "form"]],
    }));
    onRpc("partner", "web_read", () => {
        if (readPartner === 1) {
            return [{ id: 1, active: "archived" }];
        }
        readPartner++;
    });
    onRpc(({ model, method, route }) =>
        expect.step(`${method || route}${method ? ": " + model : ""}`)
    );
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.act_window",
        res_model: "partner",
        res_id: 1,
        views: [[false, "form"]],
    });
    expect(`[name='active'] input`).toHaveValue("true");
    expect.verifySteps(["get_views: partner", "web_read: partner"]);

    await toggleActionMenu();
    expect(`.o-dropdown--menu .o-dropdown-item:contains(Archive)`).toHaveCount(1);

    await toggleMenuItem("Archive");
    expect(`.modal`).toHaveCount(1);
    expect.verifySteps([]);

    await contains(`.modal-footer .btn-primary`).click();
    expect.verifySteps(["action_archive: partner", "get_views: product", "onchange: product"]);

    await contains(`.modal footer .myButton`).click();
    expect.verifySteps(["web_save: product", "do_archive: product", "web_read: partner"]);
    expect(`.modal`).toHaveCount(0);
    expect(`[name='active'] input`).toHaveValue("archived");
});

test(`archive action with active field not in view`, async () => {
    // add active field on partner model, but do not put it in the view
    Partner._fields.active = fields.Boolean({ default: true });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
        actionMenus: {},
    });
    expect(`.o_cp_action_menus`).toHaveCount(1);

    await toggleActionMenu();
    expect(`.o_cp_action_menus span:contains(Archive)`).toHaveCount(0);
    expect(`.o_cp_action_menus span:contains(Unarchive)`).toHaveCount(0);
});

test(`archive action not shown with readonly active field`, async () => {
    // add active field on partner model in readonly mode to do not have Archive option
    Partner._fields.active = fields.Boolean({ default: true, readonly: true });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="active"/><field name="foo"/></form>`,
        resId: 1,
        actionMenus: {},
    });
    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    expect(queryAllTexts`.o_menu_item`).toEqual(["Duplicate", "Delete"]);
});

test(`can duplicate a record`, async () => {
    onRpc("copy", ({ args, model }) => {
        if (model === "partner") {
            expect(args).toEqual([[1]]);
            expect.step("copy");
        }
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
        actionMenus: {},
    });
    expect(`.o_breadcrumb`).toHaveText("first record");

    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect.verifySteps(["copy"]);
    expect(`.o_breadcrumb`).toHaveText("first record (copy)");
    expect(`.o_form_editable`).toHaveCount(1);
});

test(`duplicating a record preserves the context`, async () => {
    onRpc("web_read", ({ kwargs }) => expect.step(kwargs.context.hey));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
        actionMenus: {},
        context: { hey: "hoy" },
    });
    expect.verifySteps(["hoy"]);

    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect.verifySteps(["hoy"]);
});

test(`cannot duplicate a record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form duplicate="false"><field name="foo"/></form>`,
        resId: 1,
        actionMenus: {},
    });
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_cp_action_menus`).toHaveCount(1);

    await toggleActionMenu();
    expect(`.o_cp_action_menus span:contains(Duplicate)`).toHaveCount(0);
});

test(`don't duplicate if save fail`, async () => {
    onRpc("web_save", () => {
        expect.step("web_save");
        throw new Error("Cannot save");
    });
    onRpc("copy", () => expect.step("copy"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        actionMenus: {},
    });
    await contains(`[name=foo] input`).edit("new value");
    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect(`.modal .o_error_dialog`).toHaveCount(1);

    // Discard changes don't trigger Duplicate action
    await contains(`.modal .btn-secondary`).click();
    expect.verifySteps(["web_save"]);
});

test(`editing a translatable field in a duplicate record overrides translations`, async () => {
    onRpc("web_save", () => expect.step("web_save"));
    onRpc("web_override_translations", ({ args }) => {
        expect.step("web_override_translations");
        expect(args[1]).toEqual({ name: "first record (test)" });
        return true;
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="name"/></form>`,
        resId: 1,
        actionMenus: {},
    });
    expect(`.o_breadcrumb`).toHaveText("first record");

    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect(`.o_breadcrumb`).toHaveText("first record (copy)");
    expect(`.o_form_editable`).toHaveCount(1);

    await contains(`.o_field_char input`).edit("first record (test)");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save", "web_override_translations"]);
});

test.tags("desktop")(`clicking on stat buttons in edit mode on desktop`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("doActionButton");
        },
    });

    onRpc("web_save", ({ args }) => expect(args[1].foo).toBe("tralala"));
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box">
                        <button class="oe_stat_button" name="some_action" type="action">
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(`.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
    expect(`.o_form_editable`).toHaveCount(1);

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(`.oe_stat_button`).click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect.verifySteps(["web_save", "doActionButton"]);
});

test.tags("mobile")(`clicking on stat buttons in edit mode on mobile`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("doActionButton");
        },
    });

    onRpc("web_save", ({ args }) => expect(args[1].foo).toBe("tralala"));
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box">
                        <button class="oe_stat_button" name="some_action" type="action">
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(".o-form-buttonbox .o_button_more").click();
    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
    expect(`.o_form_editable`).toHaveCount(1);

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(".o-form-buttonbox .o_button_more").click();
    await contains(`button.oe_stat_button`).click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect.verifySteps(["web_save", "doActionButton"]);
});

test.tags("desktop");
test(`clicking on stat buttons save and reload in edit mode on desktop`, async () => {
    mockService("action", {
        doActionButton() {},
    });

    onRpc("web_save", ({ args }) => {
        // simulate an override of the model...
        args[1].name = "GOLDORAK";
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box">
                        <button class="oe_stat_button" type="action">
                            <field name="int_field" widget="statinfo" string="Some number"/>
                        </button>
                    </div>
                <group>
                    <field name="name"/>
                </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_control_panel .o_breadcrumb`).toHaveText("second record");

    await contains(`.o_field_widget[name=name] input`).edit("some other name");
    await contains(`button.oe_stat_button`).click();
    expect(`.o_control_panel .o_breadcrumb`).toHaveText("GOLDORAK");
});

test.tags("mobile")(`clicking on stat buttons save and reload in edit mode on mobile`, async () => {
    mockService("action", {
        doActionButton() {},
    });

    onRpc("web_save", ({ args }) => {
        // simulate an override of the model...
        args[1].name = "GOLDORAK";
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div name="button_box">
                        <button class="oe_stat_button" type="action">
                            <field name="int_field" widget="statinfo" string="Some number"/>
                        </button>
                    </div>
                <group>
                    <field name="name"/>
                </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_breadcrumb`).toHaveText("second record");

    await contains(`.o_field_widget[name=name] input`).edit("some other name");
    await contains(".o-form-buttonbox .o_button_more").click();
    await contains(`button.oe_stat_button`).click();
    expect(`.o_breadcrumb`).toHaveText("GOLDORAK");
});

test(`buttons with attr "special" do not trigger a save`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("doActionButton");
        },
    });

    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <button string="Do something" class="btn-primary" name="abc" type="object"/>
                <button string="Or discard" class="btn-secondary" special="cancel"/>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(`.o_content button.btn-primary`).click();
    expect.verifySteps(["web_save", "doActionButton"]);

    await contains(`.o_field_widget[name=foo] input`).edit("abcdef");
    await contains(`.o_content button.btn-secondary`).click();
    expect.verifySteps(["doActionButton"]);
});

test(`buttons with attr "special=save" save`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("execute_action");
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <button string="Save" class="btn-primary" special="save"/>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(`.o_content button.btn-primary`).click();
    expect.verifySteps(["web_save", "execute_action"]);
});

test.tags("desktop")(`buttons with attr "special" in dialog close the dialog`, async () => {
    Product._views = {
        form: `
            <form>
                <sheet>
                    <field name="name" />
                </sheet>
                <footer>
                    <button class="btn btn-primary" special="save" data-hotkey="s">Special button save</button>
                    <button class="btn btn-secondary" special="cancel" data-hotkey="j">Special button cancel</button>
                </footer>
            </form>
        `,
    };

    onRpc("get_formview_id", () => false);
    onRpc("web_save", ({ model }) => expect.step(`${model}.web_save`));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="product_id"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    await contains(`[name="product_id"] input`).edit("ABC", { confirm: false });
    await runAllTimers(); // skip debounce
    await contains(`.o_m2o_dropdown_option_create_edit`).click();
    expect(`.o_dialog`).toHaveCount(1);

    await contains(`.o_field_widget[name=name] input`).edit("ABCDE");
    await contains(`button[special=save]`).click();
    expect(`.o_dialog`).toHaveCount(0);
    expect.verifySteps(["product.web_save"]);
    expect(`[name="product_id"] input`).toHaveValue("ABCDE");
    expect(`.o_form_status_indicator_buttons:not(.invisible)`).toHaveCount(1);

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["partner.web_save"]);

    await contains(`[name="product_id"] input`).edit("XYZ", { confirm: false });
    await runAllTimers(); // skip debounce
    await contains(`.o_m2o_dropdown_option_create_edit`).click();
    await contains(`button[special=cancel]`).click();
    expect(`.o_dialog`).toHaveCount(0);
    expect.verifySteps([]);
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);
});

test.tags("desktop")(`Add custom buttons to default buttons (replace="0")`, async () => {
    Product._views = {
        form: `
            <form>
                <sheet>
                    <field name="name" />
                </sheet>
                <footer replace="0">
                    <button class="btn btn-primary">Custom 1</button>
                    <button class="btn btn-secondary">Custom 2</button>
                </footer>
            </form>
        `,
    };
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="product_id"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    await contains(`[name="product_id"] input`).edit("ABC", { confirm: false });
    await runAllTimers(); // skip debounce
    await contains(`.o_m2o_dropdown_option_create_edit`).click();

    expect(".o_dialog .o_form_button_save").toHaveCount(1);
    expect(".o_dialog .o_form_button_cancel").toHaveCount(1);
    expect(".o_dialog button:contains(Custom 1)").toHaveCount(1);
    expect(".o_dialog button:contains(Custom 2)").toHaveCount(1);
});

test(`missing widgets do not crash`, async () => {
    Partner._fields.foo = fields.Generic({ type: "new field type without widget" });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect(`.o_field_widget`).toHaveCount(1);
});

test(`nolabel`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <group class="firstgroup">
                            <field name="foo" nolabel="1"/>
                        </group>
                        <group class="secondgroup">
                            <field name="product_id"/>
                            <field name="int_field" nolabel="1"/><field name="float_field" nolabel="1"/>
                        </group>
                        <group>
                            <field name="bar"/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`label.o_form_label`).toHaveCount(2);
    expect(`label.o_form_label:eq(0)`).toHaveText("Product");
    expect(`label.o_form_label:eq(1)`).toHaveText("Bar");
    expect(`.firstgroup div`).toHaveStyle("");
    expect(`.secondgroup div.o_wrap_field`).toHaveCount(2);
    expect(`.secondgroup div.o_wrap_field:first div.o_cell`).toHaveCount(2);
});

test(`many2one in a one2many`, async () => {
    Partner._records[0].child_ids = [2];
    Partner._records[1].product_id = 37;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list>
                        <field name="product_id"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect(`td:contains(xphone)`).toHaveCount(1);
});

test(`circular many2many's`, async () => {
    Partner._records[0].type_ids = [12];
    PartnerType._fields.partner_ids = fields.Many2many({ relation: "partner" });
    PartnerType._records[0].partner_ids = [1];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="type_ids">
                    <list><field name="display_name"/></list>
                    <form>
                        <field name="partner_ids">
                            <list><field name="display_name"/></list>
                            <form><field name="display_name"/></form>
                        </field>
                    </form>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect(`td:contains(gold)`).toHaveCount(1);

    await contains(`.o_data_cell`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal td:contains(first record)`).toHaveCount(1);

    await contains(`.modal .o_data_cell`).click();
    expect(`.modal`).toHaveCount(2);
});

test(`discard changes on a non dirty form view`, async () => {
    onRpc("write", () => expect.step("write"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resId: 1,
    });
    expect(`.o_field_widget[name=foo] input`).toHaveValue("yop");

    await contains(`.o_form_button_cancel`, { visible: false }).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("yop");
    expect.verifySteps([]);
});

test(`discard changes on a dirty form view`, async () => {
    onRpc("write", () => expect.step("write"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resId: 1,
    });
    expect(`.o_field_widget[name=foo] input`).toHaveValue("yop");

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("new value");

    await contains(`.o_form_button_cancel`).click();
    expect(`.o_field_widget input`).toHaveValue("yop");
    expect.verifySteps([]);
});

test(`discard changes on a dirty form view (for date field)`, async () => {
    // this test checks that the relational model properly handles date object
    // when they are discarded and saved.  This may be an issue because
    // dates are saved as luxon instances, and were at one point stringified,
    // then parsed into string, which is wrong.
    Partner._fields.date = fields.Date({ default: "2017-01-25" });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="date"></field></form>`,
    });

    // also focus the buttons before clicking on them to precisely reproduce what
    // really happens (mostly because the datepicker lib need that focus
    // event to properly focusout the input, otherwise it crashes later on
    // when the 'blur' event is triggered by the re-rendering)
    await contains(`.o_form_button_cancel`).click();

    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget input`).toHaveValue("01/25/2017");
});

test.tags("desktop")(`discard changes on relational data on new record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="top">
                        <field name="product_id"/>
                    </list>
                </field>
            </form>
        `,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_input_dropdown input`).click();
    await contains(`.dropdown-item:contains(xphone)`).click();
    expect(`.o_field_widget[name="product_id"] input`).toHaveValue("xphone");

    await contains(`.o_form_button_cancel`).click();
    expect(`.o_data_row`).toHaveCount(0);
});

test("discard changes on relational data on existing record", async () => {
    Partner._records[0].product_ids = [37];
    Partner._records[0].bar = false;
    Partner._onChanges = {
        bar(record) {
            // when bar changes, push another record in product_ids.
            record.product_ids = [[4, 41]];
        },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="bar"/>
                <field name="product_ids" widget="one2many">
                    <list>
                        <field name="display_name"/>
                    </list>
                </field>
            </form>`,
    });

    expect(queryAllTexts`.o_data_cell`).toEqual(["xphone"]);
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(0);

    // Click on bar
    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(1);
    expect(queryAllTexts`.o_data_cell`).toEqual(["xphone", "xpad"]);

    // click on discard
    await contains(`.o_form_button_cancel`).click();
    expect(queryAllTexts`.o_data_cell`).toEqual(["xphone"]);
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(0);
});

test("discard changes on relational data on new record (1)", async () => {
    // When bar is changed, it pushes a record in product_ids
    // After discarding, product_ids should be empty
    Partner._onChanges = {
        bar(record) {
            if (record.bar) {
                // when bar changes, push another record in product_ids.
                record.product_ids = [[4, 41]];
            }
        },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="product_ids" widget="one2many">
                    <list>
                        <field name="display_name"/>
                    </list>
                </field>
            </form>`,
    });

    expect(queryAllTexts`.o_data_cell`).toEqual([]);
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(0);

    // Click on bar
    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(1);
    expect(queryAllTexts`.o_data_cell`).toEqual(["xpad"]);

    // click on discard
    await contains(`.o_form_button_cancel`).click();
    expect(queryAllTexts`.o_data_cell`).toEqual([]);
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(0);
});

test("discard changes on relational data on new record (2)", async () => {
    // An initial onChange push a record in product_ids
    // When bar is changed, it pushes a second record in product_ids
    // After discarding, product_ids should contain the inital record pushed by the inital onChange
    Partner._onChanges = {
        product_ids(record) {
            record.product_ids = [[4, 41]];
        },
        bar(record) {
            if (record.bar) {
                // when bar changes, push another record in product_ids.
                record.product_ids = [[4, 37]];
            }
        },
    };
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="bar"/>
                <field name="product_ids" widget="one2many">
                    <list>
                        <field name="display_name"/>
                    </list>
                </field>
            </form>`,
    });

    expect(queryAllTexts`.o_data_cell`).toEqual(["xpad"]);
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(0);

    // Click on bar
    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(1);
    expect(queryAllTexts`.o_data_cell`).toEqual(["xpad", "xphone"]);

    // click on discard
    await contains(`.o_form_button_cancel`).click();
    expect(queryAllTexts`.o_data_cell`).toEqual(["xpad"]);
    expect(`.o_field_widget[name=bar] input:checked`).toHaveCount(0);
});

test(`discard changes on a new (non dirty, except for defaults) form view`, async () => {
    Partner._fields.foo = fields.Char({ default: "ABC" });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        config: {
            historyBack() {
                expect.step("history-back");
            },
        },
    });
    expect(`.o_field_widget[name=foo] input`).toHaveValue("ABC");

    await contains(`.o_form_button_cancel`).click();
    expect.verifySteps(["history-back"]);
});

test(`discard changes on a new (dirty) form view`, async () => {
    Partner._fields.foo = fields.Char({ default: "ABC" });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        config: {
            historyBack() {
                expect.step("history-back");
            },
        },
    });
    expect(`.o_form_editable`).not.toHaveClass(["o_form_saved", "o_form_dirty"]);
    expect(`.o_field_widget[name=foo] input`).toHaveValue("ABC");

    await contains(`.o_field_widget[name=foo] input`).edit("DEF");
    expect(`.o_form_editable`).toHaveClass("o_form_dirty");
    expect(`.o_form_editable`).not.toHaveClass("o_form_saved");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("DEF");

    await contains(`.o_form_button_cancel`).click();
    expect(`.o_form_editable`).not.toHaveClass(["o_form_saved", "o_form_dirty"]);
    expect(`.o_field_widget[name=foo] input`).toHaveValue("ABC");
    expect.verifySteps(["history-back"]);

    await contains(`.o_field_widget[name=foo] input`).edit("GHI");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("GHI");

    await contains(`.o_form_button_cancel`).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("ABC");
    expect.verifySteps(["history-back"]);
});

test(`discard has to wait for changes in each field`, async () => {
    const def = new Deferred();
    class CustomField extends Component {
        static template = xml`<input t-ref="input" t-att-value="value" t-on-blur="onBlur" t-on-input="onInput" />`;
        static props = {
            ...standardFieldProps,
        };

        setup() {
            this.input = useRef("input");
            useBus(this.props.record.model.bus, "NEED_LOCAL_CHANGES", ({ detail }) =>
                detail.proms.push(this.updateValue())
            );
        }

        get value() {
            return this.props.record.data[this.props.name];
        }

        async updateValue() {
            const value = this.input.el.value;
            await def;
            await this.props.record.update({ [this.props.name]: `update value: ${value}` });
        }

        onBlur() {
            return this.updateValue();
        }

        onInput() {
            this.props.record.model.bus.trigger("FIELD_IS_DIRTY", true);
        }
    }
    fieldsRegistry.add("custom", { component: CustomField });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" widget="custom"/></form>`,
        resId: 2,
    });

    expect(`[name="foo"] input`).toHaveValue("blip");

    await contains(`[name="foo"] input`).edit("test");
    expect(`[name="foo"] input`).toHaveValue("test");

    // should never display 'update value'
    await contains(`.o_form_button_cancel`).click();
    expect(`[name="foo"] input`).toHaveValue("test");

    def.resolve();
    await animationFrame();
    expect(`[name="foo"] input`).toHaveValue("blip");
});

test(`save a new dirty record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
    });
    expect(`.o_form_editable`).not.toHaveClass("o_form_saved o_form_dirty");

    await contains(`.o_field_widget[name=foo] input`).edit("DEF");
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_editable`).toHaveClass("o_form_saved");
    expect(`.o_form_editable`).not.toHaveClass("o_form_dirty");
});

test(`discard changes on a duplicated record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resId: 1,
        actionMenus: {},
    });
    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    await contains(`.o_form_button_save`).click();
    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("tralala");

    await contains(`.o_form_button_cancel`, { visible: false }).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("tralala");
});

test(`discard invalid value`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field"></field></form>`,
        resId: 1,
    });
    await contains(`.o_field_widget[name=int_field] input`).edit("tralala");
    expect(`.o_field_invalid`).toHaveCount(1);
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("tralala");

    await contains(`.o_form_button_cancel`).click();
    expect(`.o_field_invalid`).toHaveCount(0);
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("10");
});

test(`Domain: allow empty domain on fieldInfo`, async () => {
    Partner._fields.product_id = fields.Many2one({
        relation: "product",
        domain: `[("display_name", "=", name)]`,
    });

    onRpc("search_read", ({ kwargs }) => {
        expect.step("search_read");
        expect(JSON.stringify(kwargs.domain)).toBe("[]");
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <field name="product_id" widget="statusbar" domain="[]"></field>
                </header>
                <sheet>
                    <group>
                        <field name="name"></field>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["search_read"]);
});

test(`discard form with specialdata`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <field name="product_id" domain="[('name', '=', name)]" widget="statusbar"/>
                </header>
                <sheet>
                    <group>
                        <field name="name"></field>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_statusbar_status button:not(.d-none)`).toHaveCount(1);

    await contains(`.o_field_widget[name=name] input`).edit("xpad");
    expect(`.o_statusbar_status button:not(.d-none)`).toHaveCount(2);

    await animationFrame(); // @todo remove
    await contains(`.o_form_button_cancel`).click();
    expect(`.o_statusbar_status button:not(.d-none)`).toHaveCount(1);
    expect(`.o_statusbar_status button:not(.d-none)`).toHaveText("xphone");
});

test(`switching to another record from a dirty one`, async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_field_widget[name=foo] input`).toHaveValue("yop");

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("new value");

    await contains(`.o_pager_next`).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("blip");
    expect.verifySteps(["web_save"]);

    await contains(`.o_pager_previous`).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("new value");
    expect.verifySteps([]);
});

test.tags("desktop")(`switching to another record from a dirty one on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    await contains(`.o_pager_next`).click();
    expect(getPagerValue()).toEqual([2]);

    await contains(`.o_pager_previous`).click();
    expect(getPagerValue()).toEqual([1]);
});

test(`do not reload after save when using pager`, async () => {
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);
    expect(`.o_input`).toHaveValue("yop");

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    await contains(`.o_pager_next`).click();
    expect(`.o_input`).toHaveValue("blip");
    expect.verifySteps(["web_save"]);
});

test.tags("desktop")(`do not reload after save when using pager on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    await contains(`.o_pager_next`).click();
    expect(getPagerValue()).toEqual([2]);
});

test(`switching to another record from an invalid one`, async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" required="1"/></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_required_modifier");

    await contains(`.o_field_widget[name=foo] input`).edit("");
    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_form_status_indicator .text-danger`).toHaveAttribute(
        "data-tooltip",
        "Unable to save. Correct the issue or discard all changes"
    );
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_field_invalid");
    expect(`.o_notification_manager .o_notification`).toHaveCount(1);
    expect.verifySteps([]);
});

test.tags("desktop")(`switching to another record from an invalid one on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" required="1"/></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);

    await contains(`.o_field_widget[name=foo] input`).edit("");
    await contains(`.o_pager_next`).click();
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);
});

test(`keynav: switching to another record from an invalid one`, async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" required="1"/></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_required_modifier");

    await contains(`.o_field_widget[name=foo] input`).edit("");
    await press(["alt", "n"]);
    await animationFrame();
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_form_status_indicator .text-danger`).toHaveAttribute(
        "data-tooltip",
        "Unable to save. Correct the issue or discard all changes"
    );
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_field_invalid");
    expect(`.o_notification_manager .o_notification`).toHaveCount(1);
    expect.verifySteps([]);
});

test.tags("desktop");
test(`keynav: switching to another record from an invalid one on desktop`, async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" required="1"/></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_pager_counter`).toHaveText("1 / 2");

    await contains(`.o_field_widget[name=foo] input`).edit("");
    await press(["alt", "n"]);
    await animationFrame();
    expect(`.o_pager_counter`).toHaveText("1 / 2");
});

test(`switching to another record from an invalid one (2)`, async () => {
    // in this scenario, the record is already invalid in db, so we should be allowed to
    // leave it
    Partner._records[0].foo = false;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" required="1"/></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_required_modifier");

    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("second record");

    await contains(`.o_pager_previous`).click();
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_required_modifier");
});

test.tags("desktop")(`switching to another record from an invalid one (2) on desktop`, async () => {
    // in this scenario, the record is already invalid in db, so we should be allowed to
    // leave it
    Partner._records[0].foo = false;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" required="1"/></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_pager_counter`).toHaveText("1 / 2");

    await contains(`.o_pager_next`).click();
    expect(`.o_pager_counter`).toHaveText("2 / 2");

    await contains(`.o_pager_previous`).click();
    expect(`.o_pager_counter`).toHaveText("1 / 2");
});

test(`keynav: switching to another record from a dirty one`, async () => {
    onRpc("web_save", () => expect.step("web_save"));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_field_widget[name=foo] input`).toHaveValue("yop");

    await contains(`.o_field_widget[name=foo] input`).edit("new value", { confirm: false });
    await press(["alt", "n"]);
    await animationFrame();
    expect.verifySteps(["web_save"]);
    expect(`.o_field_widget[name=foo] input`).toHaveValue("blip");

    await press(["alt", "p"]);
    await animationFrame();
    expect.verifySteps([]);
    expect(`.o_field_widget[name=foo] input`).toHaveValue("new value");
});

test.tags("desktop");
test(`keynav: switching to another record from a dirty one on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resIds: [1, 2],
        resId: 1,
    });
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);

    await contains(`.o_field_widget[name=foo] input`).edit("new value", { confirm: false });
    await press(["alt", "n"]);
    await animationFrame();
    expect(`.o_pager_counter`).toHaveText("2 / 2");

    await press(["alt", "p"]);
    await animationFrame();
    expect(`.o_pager_counter`).toHaveText("1 / 2");
});

test(`handling dirty state: switching to another record`, async () => {
    Partner._fields.priority = fields.Selection({
        default: 1,
        selection: [
            [1, "Low"],
            [2, "Medium"],
            [3, "High"],
        ],
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"></field>
                <field name="priority" widget="priority"></field>
            </form>
        `,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("yop");

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("new value");

    await contains(`.o_form_button_save`).click();
    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("second record");
    expect(`.o_priority .fa-star-o`).toHaveCount(2);

    await contains(`.o_priority .fa-star-o`).click();
    expect(`.o_priority .fa-star`).toHaveCount(1);

    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("first record");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("new value");

    await contains(`.o_field_widget[name=foo] input`).edit("wrong value");
    await contains(`.o_form_button_cancel`).click();
    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("second record");
});

test.tags("desktop")(`handling dirty state: switching to another record on desktop`, async () => {
    Partner._fields.priority = fields.Selection({
        default: 1,
        selection: [
            [1, "Low"],
            [2, "Medium"],
            [3, "High"],
        ],
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"></field>
                <field name="priority" widget="priority"></field>
            </form>
        `,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_pager_counter`).toHaveText("1 / 2");

    await contains(`.o_field_widget[name=foo] input`).edit("new value");

    await contains(`.o_form_button_save`).click();
    await contains(`.o_pager_next`).click();
    expect(`.o_pager_counter`).toHaveText("2 / 2");

    await contains(`.o_priority .fa-star-o`).click();

    await contains(`.o_pager_next`).click();
    expect(`.o_pager_counter`).toHaveText("1 / 2");

    await contains(`.o_field_widget[name=foo] input`).edit("wrong value");
    await contains(`.o_form_button_cancel`).click();
    await contains(`.o_pager_next`).click();
    expect(getPagerValue()).toEqual([2]);
});

test(`restore local state when switching to another record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <notebook>
                    <page string="First Page" name="first">
                        <field name="foo"/>
                    </page>
                    <page string="Second page" name="second">
                        <field name="bar"/>
                    </page>
                </notebook>
            </form>
        `,
        resIds: [1, 2],
        resId: 1,
    });
    await contains(`.o_notebook .nav-link:eq(1)`).click();
    expect(`.o_notebook .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook .nav-link:eq(1)`).toHaveClass("active");

    await contains(`.o_pager_next`).click();
    expect(`.o_notebook .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook .nav-link:eq(1)`).toHaveClass("active");
});

test(`restore the open notebook page when switching to another view`, async () => {
    Partner._views = {
        search: `<search/>`,
        list: `<list><field name="foo"/></list>`,
        form: `
            <form>
                <notebook>
                    <page string="First Page" name="first">
                        <field name="foo"/>
                    </page>
                    <page string="Second page" name="second">
                        <field name="bar"/>
                    </page>
                </notebook>
                <notebook>
                    <page string="Page1" name="p1">
                        <field name="foo"/>
                    </page>
                    <page string="Page2" name="p2" autofocus="autofocus">
                        <field name="bar"/>
                    </page>
                    <page string="Page3" name="p3">
                        <field name="bar"/>
                    </page>
                </notebook>
            </form>
        `,
    };

    defineActions([
        {
            id: 1,
            name: "test",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
        {
            id: 2,
            name: "test2",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(2);

    expect(`.o_notebook:eq(0) .nav-link:eq(0)`).toHaveClass("active");
    expect(`.o_notebook:eq(0) .nav-link:eq(1)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(1)`).toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(2)`).not.toHaveClass("active");

    // click on second page tab of the first notebook
    await contains(`.o_notebook:eq(0) .nav-link:eq(1)`).click();
    // click on third page tab of the second notebook
    await contains(`.o_notebook:eq(1) .nav-link:eq(2)`).click();
    expect(`.o_notebook:eq(0) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(0) .nav-link:eq(1)`).toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(1)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(2)`).toHaveClass("active");

    // switch to a list view
    await getService("action").doAction(1);

    // back to the form view
    await contains(`.o_back_button`).click();
    expect(`.o_notebook:eq(0) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(0) .nav-link:eq(1)`).toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(1)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(2)`).toHaveClass("active");
});

test.tags("desktop");
test(`don't restore the open notebook page when we create a new record`, async () => {
    Partner._views = {
        search: `<search/>`,
        list: `<list><field name="foo"/></list>`,
        form: `
                <form>
                    <notebook>
                        <page string="First Page" name="first">
                            <field name="foo"/>
                        </page>
                        <page string="Second page" name="second">
                            <field name="bar"/>
                        </page>
                    </notebook>
                    <notebook>
                        <page string="Page1" name="p1">
                            <field name="foo"/>
                        </page>
                        <page string="Page2" name="p2" autofocus="autofocus">
                            <field name="bar"/>
                        </page>
                        <page string="Page3" name="p3">
                            <field name="bar"/>
                        </page>
                    </notebook>
                </form>
            `,
    };

    defineActions([
        {
            id: 1,
            name: "test",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(`.o_data_cell`).click();
    expect(`.o_notebook:eq(0) .nav-link:eq(0)`).toHaveClass("active");
    expect(`.o_notebook:eq(0) .nav-link:eq(1)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(1)`).toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(2)`).not.toHaveClass("active");

    // click on second page tab of the first notebook
    await contains(`.o_notebook:eq(0) .nav-link:eq(1)`).click();
    // click on third page tab of the second notebook
    await contains(`.o_notebook:eq(1) .nav-link:eq(2)`).click();
    expect(`.o_notebook:eq(0) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(0) .nav-link:eq(1)`).toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(1)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(2)`).toHaveClass("active");

    // back to the list view
    await contains(`.o_back_button`).click();
    // Create a new record
    await contains(`.o_control_panel_main_buttons button.o_list_button_add`).click();
    expect(`.o_notebook:eq(0) .nav-link:eq(0)`).toHaveClass("active");
    expect(`.o_notebook:eq(0) .nav-link:eq(1)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(0)`).not.toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(1)`).toHaveClass("active");
    expect(`.o_notebook:eq(1) .nav-link:eq(2)`).not.toHaveClass("active");
});

test(`pager is hidden in create mode`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
        resIds: [1, 2],
    });
    expect(`.o_pager`).toHaveCount(1);

    await contains(`.o_form_button_create`).click();
    expect(`.o_pager`).toHaveCount(0);

    await contains(`.o_form_button_save`).click();
    expect(`.o_pager`).toHaveCount(1);
});

test.tags("desktop")(`pager is hidden in create mode on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
        resIds: [1, 2],
    });
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);

    await contains(`.o_form_button_create`).click();
    expect(`.o_pager`).toHaveCount(0);

    await contains(`.o_form_button_save`).click();
    expect(getPagerValue()).toEqual([3]);
    expect(getPagerLimit()).toBe(3);
});

test(`switching to another record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resId: 1,
        resIds: [1, 2],
    });
    expect(`.o_breadcrumb`).toHaveText("first record");

    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("second record");
});

test.tags("desktop")(`switching to another record on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resId: 1,
        resIds: [1, 2],
    });
    expect(getPagerValue()).toEqual([1]);

    await contains(`.o_pager_next`).click();
    expect(getPagerValue()).toEqual([2]);
});

test(`switching to non-existing record`, async () => {
    expect.errors(1);

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resId: 1,
        resIds: [1, 999, 2],
    });
    expect(`.o_breadcrumb`).toHaveText("first record");

    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("first record");

    await animationFrame();
    expect(`.o_notification_body`).toHaveCount(1);
    expect.verifyErrors([
        "It seems the records with IDs 999 cannot be found. They might have been deleted.",
    ]);

    await contains(`.o_pager_next`).click();
    expect(`.o_breadcrumb`).toHaveText("second record");
    expect(`.o_notification_body`).toHaveCount(1);
});

test.tags("desktop")(`switching to non-existing record on desktop`, async () => {
    expect.errors(1);

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resId: 1,
        resIds: [1, 999, 2],
    });
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(3);

    await contains(`.o_pager_next`).click();
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);

    await animationFrame();

    await contains(`.o_pager_next`).click();
    expect(getPagerValue()).toEqual([2]);
    expect(getPagerLimit()).toBe(2);
});

test(`modifiers are reevaluated when creating new record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo" class="foo_field" invisible='bar'/>
                        <field name="bar"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.foo_field`).toHaveCount(0);

    await contains(`.o_form_button_create`).click();
    expect(`.foo_field`).toHaveCount(1);
});

test(`empty readonly fields are visible on new records`, async () => {
    Partner._fields.foo = fields.Char({ readonly: true });
    Partner._records[0].foo = undefined;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_empty`).toHaveCount(1);

    await contains(`.o_form_button_create`).click();
    expect(`.o_field_empty`).toHaveCount(0);
});

test(`all group children have correct layout classname`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <group class="inner_group">
                            <field name="name"/>
                        </group>
                        <div class="inner_div">
                            <field name="foo"/>
                        </div>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.inner_group`).toHaveClass("col-lg-6");
    expect(`.inner_div`).toHaveClass("col-lg-6");
});

test(`deleting a record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        actionMenus: {},
        resIds: [1, 2, 4],
        resId: 1,
    });
    expect(`.o_breadcrumb`).toHaveText("first record");

    // open action menu and delete
    await toggleActionMenu();
    await toggleMenuItem("Delete");
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal-footer button.btn-primary`).click();
    expect(`.o_breadcrumb`).toHaveText("second record");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("blip");
});

test.tags("desktop")(`deleting a record on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        actionMenus: {},
        resIds: [1, 2, 4],
        resId: 1,
    });
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(3);

    // open action menu and delete
    await toggleActionMenu();
    await toggleMenuItem("Delete");

    await contains(`.modal-footer button.btn-primary`).click();
    expect(getPagerValue()).toEqual([1]);
    expect(getPagerLimit()).toBe(2);
});

test(`deleting the last record`, async () => {
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"></field></form>`,
        resIds: [1],
        resId: 1,
        actionMenus: {},
        config: {
            historyBack() {
                expect.step("history-back");
            },
        },
    });
    expect.verifySteps(["get_views", "web_read"]);
    await toggleActionMenu();
    await toggleMenuItem("Delete");
    expect(`.modal`).toHaveCount(1);
    expect.verifySteps([]);

    await contains(`.modal-footer button.btn-primary`).click();
    expect(`.modal`).toHaveCount(0);
    expect.verifySteps(["unlink", "history-back"]);
});

test(`empty required fields cannot be saved`, async () => {
    Partner._fields.foo = fields.Char({ required: true });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><group><field name="foo"/></group></form>`,
    });
    await contains(`.o_form_button_save`).click();
    expect(`label.o_form_label`).toHaveClass("o_field_invalid");
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_field_invalid");
    expect(`.o_notification`).toHaveCount(1);
    expect(`.o_notification_title`).toHaveText("Invalid fields:");
    expect(queryFirst(`.o_notification_content`).innerHTML).toBe("<ul><li>Foo</li></ul>");
    expect(`.o_notification_bar`).toHaveClass("bg-danger");

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    expect(`.o_field_invalid`).toHaveCount(0);
});

test(`display a dialog if onchange result is a warning`, async () => {
    Partner._onChanges = { foo: true };

    onRpc("onchange", () => ({
        value: { int_field: 10 },
        warning: {
            title: "Warning",
            message: "You must first select a partner",
            type: "dialog",
        },
    }));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="int_field"/></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("9");

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("10");
    expect(`.modal`).toHaveCount(1);
    expect(`.modal-title`).toHaveText("Warning");
    expect(`.modal-body`).toHaveText("You must first select a partner");
});

test(`display a notificaton if onchange result is a warning with type notification`, async () => {
    Partner._onChanges = { foo: true };

    onRpc("onchange", () => ({
        value: { int_field: 10 },
        warning: {
            title: "Warning",
            message: "You must first select a partner",
            type: "notification",
            className: "abc",
            sticky: true,
        },
    }));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="int_field"/></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("9");

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("10");
    expect(`.o_notification`).toHaveCount(1);
    expect(`.o_notification`).toHaveClass("abc");
    expect(`.o_notification_title`).toHaveText("Warning");
    expect(`.o_notification_content`).toHaveText("You must first select a partner");
});

test(`can create record even if onchange returns a warning`, async () => {
    Partner._onChanges = { foo: true };

    onRpc("onchange", () => ({
        value: { int_field: 10 },
        warning: {
            title: "Warning",
            message: "You must first select a partner",
        },
    }));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="int_field"/></form>`,
    });
    expect(`.o_field_widget[name="int_field"] input`).toHaveValue("10");
    expect(`.o_notification`).toHaveCount(1);
});

test(`onchange returns an error`, async () => {
    expect.errors(1);
    Partner._onChanges = { int_field: () => {} };

    onRpc("onchange", ({ args }) => {
        if (args[1].int_field === 64) {
            throw makeServerError({ message: "Some business message" });
        }
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field"/></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name=int_field] input`).toHaveValue("9");

    await contains(`.o_field_widget[name=int_field] input`).edit("64");
    expect.verifyErrors(["Some business message"]);
    expect(`.modal`).toHaveCount(1);
    expect(`.modal-body`).toHaveText(/Some business message/);
    expect(`.o_field_widget[name="int_field"] input`).toHaveValue("9");

    await contains(`.modal .btn-primary`).click();
    expect(`.modal`).toHaveCount(0);

    await contains(`.o_field_widget[name=int_field] input`).edit("32");
    expect(`.modal`).toHaveCount(0);
    expect(`.o_field_invalid`).toHaveCount(0);
});

test(`button box is rendered in create mode`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    <button type="object" class="oe_stat_button" icon="fa-check-square">
                        <field name="bar"/>
                    </button>
                </div>
            </form>
        `,
        resId: 2,
    });
    expect(`.oe_stat_button`).toHaveCount(1);

    await contains(`.o_form_button_cancel`, { visible: false }).click();
    await contains(`.o_form_button_create`).click();
    expect(`.oe_stat_button`).toHaveCount(1);
});

test(`button box is not rendered in form views in dialogs`, async () => {
    await mountViewInDialog({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    <button type="object" class="oe_stat_button" icon="fa-check-square">
                        <field name="bar"/>
                    </button>
                </div>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_dialog`).toHaveCount(1);
    expect(`.oe_stat_button`).toHaveCount(0);
});

test(`properly apply onchange on one2many fields`, async () => {
    Partner._records[0].child_ids = [4];
    Partner._onChanges = {
        foo(record) {
            record.child_ids = [
                [5],
                [1, 4, { name: "updated record" }],
                [0, null, { name: "created record" }],
            ];
        },
    };
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group><field name="foo"/></group>
                <field name="child_ids">
                    <list><field name="name"/></list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_one2many .o_data_row`).toHaveCount(1);
    expect(`.o_field_one2many .o_data_row .o_data_cell`).toHaveText("aaa");

    await contains(`.o_field_widget[name=foo] input`).edit("let us trigger an onchange");
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_data_row:eq(0) .o_data_cell`).toHaveText("updated record");
    expect(`.o_data_row:eq(1) .o_data_cell`).toHaveText("created record");
});

test(`properly apply onchange on one2many fields direct click`, async () => {
    Partner._records[0].child_ids = [2, 4];
    Partner._onChanges = {
        int_field(record) {
            record.child_ids = [
                [1, 2, { name: "updated record 1", int_field: record.int_field }],
                [1, 4, { name: "updated record 2", int_field: record.int_field * 2 }],
            ];
        },
    };
    Partner._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="int_field"/>
            </form>
        `,
    };

    const deferred = new Deferred();
    onRpc("onchange", () => deferred);
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="child_ids">
                    <list>
                        <field name="display_name"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_field_widget[name=int_field] input`).edit("2");
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.modal`).toHaveCount(0);

    deferred.resolve();
    await animationFrame();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .o_field_widget[name=int_field] input`).toHaveValue("2");
});

test(`update many2many value in one2many after onchange`, async () => {
    Partner._records[1].child_ids = [4];
    Partner._onChanges = {
        foo(record) {
            record.child_ids = [[5], [1, 4, { name: "gold", type_ids: [[5]] }]];
        },
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="child_ids">
                    <list editable="top">
                        <field name="name" readonly="not type_ids"/>
                        <field name="type_ids"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(queryAllTexts`.o_data_cell`).toEqual(["aaa", "No records"]);

    await contains(`.o_field_widget[name=foo] input`).edit("tralala");
    expect(queryAllTexts`.o_data_cell`).toEqual(["gold", "No records"]);
});

test(`delete a line in a one2many while editing another line`, async () => {
    Partner._records[0].child_ids = [1, 2];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="bottom">
                        <field name="name" required="True"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_data_cell:eq(0)`).click();
    await contains(`.o_field_widget[name=name] input`).clear();
    await contains(`.fa-trash-o:eq(1)`).click();
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_data_cell:eq(0)`).toHaveClass(["o_invalid_cell"]);
});

test(`properly apply onchange on many2many fields`, async () => {
    Partner._onChanges = {
        foo(record) {
            record.type_ids = [
                [4, 12],
                [4, 14],
            ];
        },
    };

    onRpc(({ method }) => expect.step(method));
    onRpc("web_save", ({ args }) => {
        expect(args[1].type_ids).toEqual([
            [4, 12],
            [4, 14],
        ]);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="type_ids">
                    <list><field name="display_name"/></list>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps(["get_views", "web_read"]);
    expect(`.o_field_many2many .o_data_row`).toHaveCount(0);

    await contains(`.o_field_widget[name=foo] input`).edit("let us trigger an onchange");
    expect.verifySteps(["onchange"]);
    expect(`.o_data_row`).toHaveCount(2);
    expect(`.o_data_row .o_data_cell:eq(0)`).toHaveText("gold");
    expect(`.o_data_row .o_data_cell:eq(1)`).toHaveText("silver");

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`form with domain widget: opening a many2many form and save should not crash`, async () => {
    // We just test that there is no crash in this situation
    Partner._records[0].type_ids = [12];
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo" widget="domain"/>
                </group>
                <field name="type_ids">
                    <list>
                        <field name="display_name"/>
                    </list>
                    <form>
                        <field name="name"/>
                        <field name="color"/>
                    </form>
                </field>
            </form>
        `,
        resId: 1,
    });

    // open a form view and save many2many record
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.modal-dialog footer .btn-primary`).click();
    expect.verifyErrors([]);
});

test(`display_name not sent for onchanges if not in view`, async () => {
    Partner._records[0].type_ids = [12];
    Partner._onChanges = { foo() {} };
    PartnerType._onChanges = { name() {} };

    onRpc("partner", "web_read", ({ kwargs }) => {
        expect.step(`partner.web_read`);
        expect(kwargs.specification).toEqual({
            display_name: {},
            foo: {},
            type_ids: {
                fields: {
                    name: {},
                    color: {},
                },
                limit: 40,
                order: "",
            },
        });
    });
    onRpc("partner.type", "web_read", ({ kwargs }) => {
        expect.step(`partner.type.web_read`);
        expect(kwargs.specification).toEqual({
            color: {},
            name: {},
        });
    });

    onRpc("partner", "onchange", ({ args }) => {
        expect.step(`partner.onchange`);
        expect(args[1]).toEqual({ foo: "coucou" });
        expect(args[3]).toEqual({
            display_name: {},
            foo: {},
            type_ids: {
                fields: {
                    name: {},
                    color: {},
                },
                limit: 40,
                order: "",
            },
        });
    });
    onRpc("partner.type", "onchange", ({ args }) => {
        expect.step(`partner.type.onchange`);
        expect(args[1]).toEqual({ name: "new name" });
        expect(args[3]).toEqual({
            name: {},
            color: {},
        });
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo"/>
                    <field name="type_ids">
                        <list><field name="name"/></list>
                        <form>
                            <field name="name"/>
                            <field name="color"/>
                        </form>
                    </field>
                </group>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["partner.web_read"]);

    // trigger the onchange
    await contains(`.o_field_widget[name=foo] input`).edit("coucou");
    expect.verifySteps(["partner.onchange"]);

    // open a subrecord and trigger an onchange
    await contains(`.o_data_row .o_data_cell`).click();
    expect.verifySteps(["partner.type.web_read"]);

    await contains(`.modal .o_field_widget[name=name] input`).edit("new name");
    expect.verifySteps(["partner.type.onchange"]);
});

test(`onchanges on date(time) fields`, async () => {
    mockTimeZone(2);

    Partner._onChanges = {
        foo(record) {
            record.date = "2021-12-12";
            record.datetime = "2021-12-12 10:55:05";
        },
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="date"/>
                <field name="datetime"/>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_field_widget[name=date] input`).toHaveValue("01/25/2017");
    expect(`.o_field_widget[name=datetime] input`).toHaveValue("12/12/2016 12:55:05");

    // trigger the onchange
    await contains(`.o_field_widget[name="foo"] input`).edit("coucou");
    expect(`.o_field_widget[name=date] input`).toHaveValue("12/12/2021");
    expect(`.o_field_widget[name=datetime] input`).toHaveValue("12/12/2021 12:55:05");
});

test(`onchanges are not sent for invalid values`, async () => {
    Partner._onChanges = {
        int_field(record) {
            record.foo = String(record.int_field);
        },
    };

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="int_field"/></form>`,
        resId: 2,
    });
    expect.verifySteps(["get_views", "web_read"]);

    // edit int_field, and check that an onchange has been applied
    await contains(`.o_field_widget[name="int_field"] input`).edit("123");
    expect(`.o_field_widget[name="foo"] input`).toHaveValue("123");

    // enter an invalid value in a float, and check that no onchange has
    // been applied
    await contains(`.o_field_widget[name="int_field"] input`).edit("123a");
    expect(`.o_field_widget[name="foo"] input`).toHaveValue("123");
    expect.verifySteps(["onchange"]);

    // save, and check that the int_field input is marked as invalid
    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name="int_field"]`).toHaveClass("o_field_invalid");
    expect.verifySteps([]);
});

test(`rpc complete after destroying parent`, async () => {
    Partner._views = {
        form: `
            <form>
                <button name="update_module" type="object" class="o_form_button_update"/>
            </form>
        `,
        list: `<list><field name="display_name"/></list>`,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        },
        {
            id: 2,
            name: "Partner 2",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    ]);

    const deferred = new Deferred();
    onRpc("update_module", async () => {
        await deferred;
        return { type: "ir.actions.act_window_close" };
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_form_view`).toHaveCount(1);

    // should not crash when the call to "update_module" returns, as we should not
    // try to reload the form view, which will no longer be in the DOM
    await contains(`.o_form_button_update`).click();

    // simulate that we executed another action before update_module returns
    await getService("action").doAction(2);
    expect(`.o_list_view`).toHaveCount(1);

    deferred.resolve(); // call to update_module finally returns
    await animationFrame();
    expect(`.o_list_view`).toHaveCount(1);
});

test(`onchanges that complete after discarding`, async () => {
    Partner._onChanges = {
        foo(record) {
            record.int_field = record.foo.length + 1000;
        },
    };

    const deferred = new Deferred();
    onRpc("onchange", async () => {
        await deferred;
        expect.step("onchange is done");
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="int_field"/></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name="foo"] input`).toHaveValue("blip");

    // edit a field and discard
    await contains(`.o_field_widget[name=foo] input`).edit("1234");
    await contains(`.o_form_button_cancel`).click();
    expect(`.modal`).toHaveCount(0);
    expect(`.o_field_widget[name="foo"] input`).toHaveValue("1234");
    expect.verifySteps([]);

    // complete the onchange
    deferred.resolve();
    await animationFrame();
    expect(`.o_field_widget[name="foo"] input`).toHaveValue("blip");
    expect.verifySteps(["onchange is done"]);
});

test(`discarding before save returns`, async () => {
    const deferred = new Deferred();
    onRpc("web_save", async () => {
        await deferred;
    });
    const view = await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 2,
    });
    const form = findComponent(view, (c) => c instanceof FormController);

    expect(`.o_form_view .o_form_editable`).toHaveCount(1);
    await contains(`.o_field_widget[name=foo] input`).edit("1234");

    // save the value and discard directly
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_button_cancel`).not.toBeEnabled();
    // with form view extensions, it may happen that someone tries to discard
    // while there is a pending save, so we simulate this here
    form.discard();
    await animationFrame();
    expect(`.o_form_view .o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget[name="foo"] input`).toHaveValue("1234");
    expect(`.modal`).toHaveCount(0);

    // complete the write
    deferred.resolve();
    await animationFrame();
    expect(`.modal`).toHaveCount(0);
    expect(`.o_field_widget[name="foo"] input`).toHaveValue("1234");
});

test(`unchanged relational data is not sent for onchanges`, async () => {
    Partner._records[1].child_ids = [4];
    Partner._onChanges = {
        foo(record) {
            record.int_field = record.foo.length + 1000;
        },
    };

    onRpc("onchange", ({ args }) => {
        expect.step("onchange");
        expect(args[1]).toEqual({ foo: "trigger an onchange" });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="child_ids">
                    <list>
                        <field name="foo"/>
                        <field name="bar"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });
    await contains(`.o_field_widget[name=foo] input`).edit("trigger an onchange");
    expect.verifySteps(["onchange"]);
});

test(`onchange value are not discarded on o2m edition`, async () => {
    Partner._records[1].child_ids = [4];
    Partner._onChanges = {
        foo() {},
    };

    onRpc("onchange", () => ({
        value: {
            child_ids: [[1, 4, { foo: "foo changed" }]],
        },
    }));
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].child_ids).toEqual([[1, 4, { foo: "foo changed" }]]);
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="child_ids">
                    <list>
                        <field name="foo"/>
                        <field name="bar"/>
                    </list>
                    <form>
                        <field name="foo"/>
                        <field name="product_id"/>
                    </form>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_data_row .o_data_cell[name=foo]`).toHaveText("My little Foo Value");

    await contains(`.o_field_widget[name=foo] input`).edit("trigger an onchange");
    expect(`.o_data_row .o_data_cell[name=foo]`).toHaveText("foo changed");

    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.modal .modal-title`).toHaveText("Open: one2many field");
    expect(`.modal .o_field_widget[name=foo] input`).toHaveValue("foo changed");
});

test(`args of onchanges in o2m fields are correct (inline edition)`, async () => {
    Partner._fields.int_field = fields.Integer({ default: 14 });
    Partner._onChanges = {
        int_field(record) {
            record.foo = "[blip] " + record.int_field;
        },
    };
    Partner._records[1].child_ids = [4];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="child_ids">
                    <list editable="top">
                        <field name="foo"/>
                        <field name="int_field"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_data_row td[name=foo]`).toHaveText("My little Foo Value");

    await contains(`.o_data_row td:eq(1)`).click();
    await contains(`.o_field_widget[name=int_field] input`).edit("77", { confirm: false });
    await contains(`.o_content`).click();
    expect(`.o_data_row td[name=foo]`).toHaveText("[blip] 77");

    // create a new o2m record
    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.o_data_row input:eq(0)`).toHaveValue("[blip] 14");
});

test(`args of onchanges in o2m fields are correct (dialog edition)`, async () => {
    Partner._fields.int_field = fields.Integer({ default: 14 });
    Partner._onChanges = {
        int_field(record) {
            record.foo = "[blip] " + record.int_field;
        },
    };
    Partner._records[1].child_ids = [4];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="child_ids" string="custom label">
                    <list>
                        <field name="foo"/>
                    </list>
                    <form>
                        <field name="foo"/>
                        <field name="int_field"/>
                    </form>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_data_row .o_data_cell`).toHaveText("My little Foo Value");

    await contains(`.o_data_row td`).click();
    await contains(`.modal .o_field_widget[name=int_field] input`).edit("77");
    expect(`.modal .o_field_widget[name=foo] input`).toHaveValue("[blip] 77");

    await contains(`.modal-footer .btn-primary`).click();
    expect(`.o_data_row .o_data_cell`).toHaveText("[blip] 77");

    // create a new o2m record
    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.modal .modal-title`).toHaveText("Create custom label");
    expect(`.modal .o_field_widget[name=foo] input`).toHaveValue("[blip] 14");
    await contains(`.modal-footer .btn-primary`).click();
    expect(`.o_data_row:eq(1) .o_data_cell`).toHaveText("[blip] 14");
});

test(`context of onchanges contains the context of changed fields`, async () => {
    Partner._onChanges = {
        foo() {},
    };

    onRpc("onchange", ({ kwargs }) => {
        expect.step("onchange");
        expect(kwargs.context.test).toBe(1);
        expect(kwargs.context.int_ctx).toBeEmpty();
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo" context="{'test': 1}"/>
                <field name="int_field" context="{'int_ctx': 1}"/>
            </form>
        `,
        resId: 2,
    });
    await contains(`.o_field_widget[name=foo] input`).edit("coucou");
    expect.verifySteps(["onchange"]);
});

test.tags("desktop")(`clicking on a stat button with a context on desktop`, async () => {
    mockService("action", {
        doActionButton({ buttonContext }) {
            // button context should have been evaluated and given to the
            // action, with magic keys but without previous context
            expect(buttonContext).toEqual({ test: 2 });
            expect.step("doActionButton");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1" context="{'test': id}">
                            <field name="float_field" widget="statinfo"/>
                        </button>
                    </div>
                </sheet>
            </form>`,
        resId: 2,
        context: { some_context: true },
    });
    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("mobile")(`clicking on a stat button with a context on mobile`, async () => {
    mockService("action", {
        doActionButton({ buttonContext }) {
            // button context should have been evaluated and given to the
            // action, with magic keys but without previous context
            expect(buttonContext).toEqual({ test: 2 });
            expect.step("doActionButton");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1" context="{'test': id}">
                            <field name="float_field" widget="statinfo"/>
                        </button>
                    </div>
                </sheet>
            </form>`,
        resId: 2,
        context: { some_context: true },
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("desktop")(`clicking on a stat button with x2many in context on desktop`, async () => {
    Partner._records[1].type_ids = [12];

    mockService("action", {
        doActionButton({ buttonContext }) {
            expect(buttonContext).toEqual({ test: [12] });
            expect.step("doActionButton");
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1" context="{'test': type_ids}">
                            <field name="float_field" widget="statinfo"/>
                        </button>
                    </div>
                    <field name="type_ids" invisible="1"/>
                </sheet>
            </form>
        `,
        resId: 2,
        context: { some_context: true },
    });
    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("mobile")(`clicking on a stat button with x2many in context on mobile`, async () => {
    Partner._records[1].type_ids = [12];

    mockService("action", {
        doActionButton({ buttonContext }) {
            expect(buttonContext).toEqual({ test: [12] });
            expect.step("doActionButton");
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1" context="{'test': type_ids}">
                            <field name="float_field" widget="statinfo"/>
                        </button>
                    </div>
                    <field name="type_ids" invisible="1"/>
                </sheet>
            </form>
        `,
        resId: 2,
        context: { some_context: true },
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("desktop")(`clicking on a stat button with no context on desktop`, async () => {
    mockService("action", {
        doActionButton({ buttonContext }) {
            // button context should have been evaluated and given to the
            // action, with magic keys but without previous context
            expect(buttonContext).toEqual({});
            expect.step("doActionButton");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1">
                            <field name="float_field" widget="statinfo"/>
                        </button>
                    </div>
                </sheet>
            </form>
        `,
        resId: 2,
        context: { some_context: true },
    });
    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("mobile")(`clicking on a stat button with no context on mobile`, async () => {
    mockService("action", {
        doActionButton({ buttonContext }) {
            // button context should have been evaluated and given to the
            // action, with magic keys but without previous context
            expect(buttonContext).toEqual({});
            expect.step("doActionButton");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" type="action" name="1">
                            <field name="float_field" widget="statinfo"/>
                        </button>
                    </div>
                </sheet>
            </form>
        `,
        resId: 2,
        context: { some_context: true },
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    await contains(`button.oe_stat_button`).click();
    expect.verifySteps(["doActionButton"]);
});

test(`display a stat button outside a buttonbox`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <button class="oe_stat_button" type="action" name="1">
                        <field name="int_field" widget="statinfo"/>
                    </button>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button .o_field_widget`).toHaveCount(1);
    expect(`button .o_field_widget > *`).toHaveCount(2);
    expect(`button .o_field_widget .o_stat_value`).toHaveText("9");
});

test.tags("desktop")(`display something else than a button in a buttonbox on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    <button type="recordect" class="oe_stat_button" icon="fa-check-square">
                        <field name="bar"/>
                    </button>
                    <label/>
                </div>
            </form>
        `,
        resId: 2,
    });
    expect(`.o-form-buttonbox > *`).toHaveCount(2);
    expect(`.o-form-buttonbox > .oe_stat_button`).toHaveCount(1);
    expect(`.o-form-buttonbox > label`).toHaveCount(1);
});

test.tags("mobile")(`display something else than a button in a buttonbox on mobile`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    <button type="recordect" class="oe_stat_button" icon="fa-check-square">
                        <field name="bar"/>
                    </button>
                    <label/>
                </div>
            </form>
        `,
        resId: 2,
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    expect(`.o-form-buttonbox-small > .o-dropdown-item`).toHaveCount(2);
    expect(`.o-form-buttonbox-small > .o-dropdown-item > .oe_stat_button`).toHaveCount(1);
    expect(`.o-form-buttonbox-small > .o-dropdown-item > label`).toHaveCount(1);
});

test.tags("desktop");
test(`invisible fields are not considered as visible in a buttonbox on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    <field name="foo" invisible="1"/>
                    <field name="bar" invisible="1"/>
                    <field name="int_field" invisible="1"/>
                    <field name="float_field" invisible="1"/>
                    <field name="display_name" invisible="1"/>
                    <field name="state" invisible="1"/>
                    <field name="date" invisible="1"/>
                    <field name="datetime" invisible="1"/>
                    <button type="recordect" class="oe_stat_button" icon="fa-check-square"/>
                </div>
            </form>
        `,
        resId: 2,
    });
    expect(`.o-form-buttonbox > *`).toHaveCount(1);
    expect(`.o-form-buttonbox`).toHaveClass("o_not_full");
});

test.tags("mobile");
test(`invisible fields are not considered as visible in a buttonbox on mobile`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    <field name="foo" invisible="1"/>
                    <field name="bar" invisible="1"/>
                    <field name="int_field" invisible="1"/>
                    <field name="float_field" invisible="1"/>
                    <field name="display_name" invisible="1"/>
                    <field name="state" invisible="1"/>
                    <field name="date" invisible="1"/>
                    <field name="datetime" invisible="1"/>
                    <button type="recordect" class="oe_stat_button" icon="fa-check-square"/>
                </div>
            </form>
        `,
        resId: 2,
    });
    expect(`.o-form-buttonbox > *`).toHaveCount(1);
    expect(`.o-form-buttonbox`).toHaveClass("o_full");
});

test(`display correctly buttonbox, in large size class`, async () => {
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            get() {
                return false;
            },
        });
        return {
            bus: new EventBus(),
            get size() {
                return 6;
            },
            isSmall: false,
        };
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    <button type="recordect" class="oe_stat_button" icon="fa-check-square">
                        <field name="bar"/>
                    </button>
                    <button type="recordect" class="oe_stat_button" icon="fa-check-square">
                        <field name="foo"/>
                    </button>
                </div>
            </form>
        `,
        resId: 2,
    });
    expect(`.o-form-buttonbox > *`).toHaveCount(2);
});

test(`empty button box`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><div class="oe_button_box" name="button_box"/></form>`,
        resId: 2,
    });
    expect(`.o-form-buttonbox`).toHaveCount(0);
});

test(`button box accepts extra classes`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div class="oe_button_box my_class" name="button_box"><div/></div>
            </form>
        `,
        resId: 2,
    });
    expect(`.o-form-buttonbox.my_class`).toHaveCount(1);
});

test.tags("desktop")(`many2manys inside one2manys are saved correctly`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const command = args[1].child_ids;
        expect(command).toEqual([[0, command[0][1], { type_ids: [[4, 12]] }]]);
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="top">
                        <field name="type_ids" widget="many2many_tags"/>
                    </list>
                </field>
            </form>
        `,
    });
    // add a o2m subrecord with a m2m tag
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_input_dropdown input`).click();
    await contains(`.dropdown-item:contains(gold)`).click();
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`one2manys (list editable) inside one2manys are saved correctly`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        const command = args[1].child_ids;
        expect(command).toEqual([
            [
                0,
                command[0][1],
                { child_ids: [[0, command[0][2].child_ids[0][1], { name: "xtv" }]] },
            ],
        ]);
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list><field name="child_ids"/></list>
                    <form>
                        <field name="child_ids">
                            <list editable="top">
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>
        `,
    });

    // add a o2m subrecord
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.modal .o_field_x2many_list_row_add a`).click();
    await contains(`.modal .o_field_widget[name=name] input`).edit("xtv");
    await contains(`.modal-footer .btn-primary`).click();
    expect(`.modal`).toHaveCount(0);
    expect(`.o_data_cell`).toHaveText("1 record");

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test.tags("desktop")(`*_view_ref in context are passed correctly`, async () => {
    PartnerType._views = {
        "list,module.list_view_ref": `<list/>`,
    };

    onRpc("partner.type", "get_views", ({ kwargs }) => expect.step(kwargs.context.list_view_ref));
    onRpc(({ kwargs }) => expect.step(`${kwargs.context.some_context}`));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="type_ids" widget="one2many" context="{'list_view_ref':'module.list_view_ref'}"/>
            </form>
        `,
        resId: 1,
        resIds: [1, 2],
        context: { some_context: 354 },
    });
    expect.verifySteps([
        "undefined", // main get_views
        "undefined", // x2many get_views
        "module.list_view_ref", // x2many get_views
        "354", // read
    ]);

    // reload to check that the record's context hasn't been modified
    await contains(`.o_pager_next`).click();
    expect.verifySteps(["354"]);
});

test(`non inline subview and create=0 in action context`, async () => {
    // the create=0 should apply on the main view (form), but not on subviews
    // this works because we pass the "base_model" in the context for the "get_views" call
    Product._views = {
        kanban: `
            <kanban>
                <templates><t t-name="card">
                    <field name="name"/>
                </t></templates>
            </kanban>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="product_ids" mode="kanban" widget="one2many"/></form>`,
        resId: 1,
        context: { create: false },
    });
    expect(`.o_form_button_create`).toHaveCount(0);
    expect(`.o-kanban-button-new`).toHaveCount(1);
});

test(`readonly fields with modifiers may be saved`, async () => {
    // the readonly property on the field description only applies on view,
    // this is not a DB constraint. It should be seen as a default value,
    // that may be overridden in views, for example with modifiers. So
    // basically, a field defined as readonly may be edited.
    Partner._fields.foo = fields.Char({ readonly: true });

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({ foo: "New foo value" });
    });
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="foo" readonly="not bar"/>
                <field name="bar"/>
            </form>
        `,
        resId: 1,
    });

    // bar being set to true, foo shouldn't be readonly and thus its value
    // could be saved, even if in its field description it is readonly
    expect(`.o_field_widget[name="foo"] input`).toHaveCount(1);
    await contains(`.o_field_widget[name="foo"] input`).edit("New foo value");
    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("New foo value");
    expect.verifySteps(["web_save"]);
});

test(`readonly sub fields fields with force_save attribute`, async () => {
    Partner._fields.foo = fields.Char({ readonly: true });
    Partner._fields.int_field = fields.Integer({ readonly: true });

    onRpc("web_save", ({ args }) => {
        // foo should be saved because of the "force_save" attribute
        // float_field should be saved because it isn't readonly
        // int_field should not be saved as it is readonly
        expect.step("web_save");
        const commands = args[1].child_ids;
        expect(commands).toEqual([[0, commands[0][1], { foo: "some value", float_field: 6.5 }]]);
    });
    onRpc("onchange", () => {
        expect.step("onchange");
        return {
            value: {
                child_ids: [[0, false, { foo: "some value", int_field: 44, float_field: 6.5 }]],
            },
        };
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="bottom">
                        <field name="foo" force_save="1"/>
                        <field name="int_field"/>
                        <field name="float_field"/>
                    </list>
                </field>
            </form>
        `,
    });
    expect.verifySteps(["onchange"]);

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`readonly set by modifier do not break many2many_tags`, async () => {
    Partner._onChanges = {
        bar(record) {
            record.type_ids = [[4, 12]];
        },
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="bar"/>
                <field name="type_ids" widget="many2many_tags" readonly="bar"/>
            </form>
        `,
        resId: 5,
    });
    expect(`.o_field_widget[name=type_ids] .o_tag`).toHaveCount(0);

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_field_widget[name=type_ids] .o_tag`).toHaveCount(1);
});

test(`check if id is available in evaluation context`, async () => {
    let checkOnchange = false;
    onRpc("onchange", ({ kwargs }) => {
        if (checkOnchange) {
            expect.step("onchange");
            expect(kwargs.context.current_id).toBe(false);
        }
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids" context="{'current_id': id}">
                    <list><field name="parent_id"/></list>
                    <form><field name="parent_id"/></form>
                </field>
            </form>
        `,
    });

    checkOnchange = true;
    await contains(`.o_field_x2many_list_row_add a`).click();
    expect.verifySteps(["onchange"]);
});

test(`modifiers are considered on multiple <footer/> tags`, async () => {
    Partner._views = {
        form: `
            <form>
                <field name="bar"/>
                <footer invisible="not bar">
                    <button>Hello</button>
                    <button>World</button>
                </footer>
                <footer invisible="bar">
                    <button>Foo</button>
                </footer>
            </form>
        `,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(queryAllTexts`.modal-footer button:not(.d-none)`).toEqual(["Hello", "World"]);

    await contains(`.o_field_boolean input`).click();
    expect(queryAllTexts`.modal-footer button:not(.d-none)`).toEqual(["Foo"]);
});

test(`buttons in footer are moved to $buttons if necessary`, async () => {
    Partner._views = {
        form: `
            <form>
                <field name="foo"/>
                <footer>
                    <button string="Create" type="recordect" class="infooter"/>
                </footer>
            </form>
        `,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            target: "new",
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.modal-footer button.infooter`).toHaveCount(1);
    expect(`.o_form_view button.infooter`).toHaveCount(0);
});

test(`open new record even with warning message`, async () => {
    Partner._onChanges = { foo: true };

    onRpc("onchange", () => ({
        warning: {
            title: "Warning",
            message: "Any warning.",
        },
        value: {},
    }));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><group><field name="foo"/></group></form>`,
        resId: 2,
    });
    expect(`.o_field_widget[name=foo] input`).toHaveValue("blip");

    await contains(`.o_field_widget[name="foo"] input`).edit("tralala");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("tralala");

    await contains(`.o_form_button_cancel`).click();
    await contains(`.o_form_button_create`).click();
    expect(`.o_field_widget[name=foo] input`).toHaveValue("");
});

test.tags("desktop")(`render stat button with string inline on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button string="Inventory Moves" class="oe_stat_button" icon="oi-arrows-v"/>
                    </div>
                </sheet>
            </form>
        `,
    });
    expect(`.o_form_view .o-form-buttonbox button.oe_stat_button`).toHaveText("Inventory Moves");
});

test.tags("mobile")(`render stat button with string inline on mobile`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button string="Inventory Moves" class="oe_stat_button" icon="oi-arrows-v"/>
                    </div>
                </sheet>
            </form>
        `,
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    expect(`.o-form-buttonbox-small button.oe_stat_button`).toHaveText("Inventory Moves");
});

test(`open one2many form containing one2many`, async () => {
    Partner._records[0].product_ids = [37];

    Product._fields.type_ids = fields.One2many({ relation: "partner.type" });
    Product._records[0].type_ids = [12];
    Product._views = {
        form: `
            <form>
                <field name="type_ids">
                    <list create="0">
                        <field name="display_name"/>
                        <field name="color"/>
                    </list>
                </field>
            </form>
        `,
    };

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="product_ids" widget="one2many">
                    <list create="0">
                        <field name="display_name"/>
                        <field name="type_ids"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);
    expect(`.o_data_row .o_data_cell:eq(1)`).toHaveText("1 record");

    await contains(`.o_data_cell`).click();
    expect(`.modal .o_data_row .o_data_cell`).toHaveCount(2);
    expect(queryAllTexts`.modal .o_data_cell`).toEqual(["gold", "2"]);
    expect.verifySteps(["get_views", "web_read"]);
});

test(`no field should be focused`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="bar"/></form>`,
        resId: 1,
    });
    expect(document.body).toBeFocused();
});

test.tags("desktop")(`in create mode, first field is focused`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="bar"/></form>`,
    });
    const input = queryFirst`.o_field_widget[name="foo"] input`;
    expect(input).toBeFocused();
    expect(input.selectionStart).toBe(input.value.length);
});

test.tags("desktop")(`in create mode, autofocus fields are focused`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field"/><field name="foo" default_focus="1"/></form>`,
    });
    expect(`.o_field_widget[name="foo"] input`).toBeFocused();
});

test.tags("desktop")(`autofocus first visible field`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field" invisible="1"/><field name="foo"/></form>`,
    });
    expect(`.o_field_widget[name="foo"] input`).toBeFocused();
});

test(`on a touch screen, fields are not focused`, async () => {
    mockTouch(true);
    after(() => mockTouch(false));

    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="foo"/><field name="bar"/></form>`,
    });
    expect(`.o_field_widget[name="foo"] input`).not.toBeFocused();
});

test(`no autofocus with disable_autofocus option`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form disable_autofocus="1"><field name="int_field"/></form>`,
    });
    expect(`.o_field_widget[name="foo"] input`).not.toBeFocused();

    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name="foo"] input`).not.toBeFocused();
});

test.tags("desktop")(`In READ mode, focus the first primary button of the form`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form edit="0">
                <field name="state" invisible="1"/>
                <header>
                    <button name="post" class="btn-primary firstButton" string="Confirm" type="recordect"/>
                    <button name="post" class="btn-primary secondButton" string="Confirm2" type="recordect"/>
                </header>
                <sheet>
                    <group>
                        <div class="oe_title">
                            <field name="display_name"/>
                        </div>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });
    expect(`button.firstButton`).toBeFocused();
});

// should clearly be a mobile test too
test.tags("desktop")(`check scroll on small height screens`, async () => {
    Partner._views = {
        list: `<list><field name="display_name"/></list>`,
        form: `<form><field name="parent_id"/></form>`,
    };
    PartnerType._views = {
        list: `<list><field name="name"/></list>`,
    };
    Product._views = {
        list: `<list><field name="name"/></list>`,
    };

    onRpc("get_formview_id", () => false);
    await mountViewInDialog({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="display_name"/>
                        <field name="foo"/>
                        <field name="bar"/>
                        <field name="child_ids"/>
                        <field name="type_ids"/>
                        <field name="product_ids"/>
                        <field name="parent_id"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 2,
    });

    // we make the content height very small so we can test scrolling.
    Object.assign(queryFirst(`.o_content`).style, { overflow: "auto", "max-height": "300px" });
    expect(`.modal-dialog`).toHaveCount(1);

    expect(queryFirst(`.o_content`).scrollTop).toBe(0);
    // simply triggerEvent focus doesn't do the trick (doesn't scroll).
    queryFirst(`[name='parent_id'] input`).focus();
    expect(queryFirst(`.o_content`).scrollTop).not.toBe(0);

    await contains(`.o_external_button`).click();
    await contains(`.o_dialog:not(.o_inactive_modal) button[class="btn-close"]`).click();
    expect(queryFirst(`.o_content`).scrollTop).not.toBe(0);
    expect(`.modal-dialog`).toHaveCount(1);
});

test(`correct amount of buttons`, async () => {
    let screenSize = SIZES.XXL;
    mockService("ui", (env) => {
        Object.defineProperty(env, "isSmall", {
            get() {
                return false;
            },
        });
        return {
            bus: new EventBus(),
            get size() {
                return screenSize;
            },
            isSmall: false,
        };
    });

    const buttons = Array(8).join(`
        <button type="recordect" class="oe_stat_button" icon="fa-check-square">
            <field name="bar"/>
        </button>
    `);

    const formView = await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div name="button_box" class="oe_button_box">
                    ${buttons}
                </div>
            </form>
        `,
        resId: 2,
    });

    const assertFormContainsNButtonsWithSizeClass = async function (sizeClass, n) {
        screenSize = sizeClass;
        formView.render(true); // deep rendering
        await animationFrame();
        expect(`.o-form-buttonbox button.oe_stat_button`).toHaveCount(n);
    };

    await assertFormContainsNButtonsWithSizeClass(SIZES.XS, 0);
    await assertFormContainsNButtonsWithSizeClass(SIZES.VSM, 0);
    await assertFormContainsNButtonsWithSizeClass(SIZES.SM, 0);
    await assertFormContainsNButtonsWithSizeClass(SIZES.MD, 7);
    await assertFormContainsNButtonsWithSizeClass(SIZES.LG, 3);
    await assertFormContainsNButtonsWithSizeClass(SIZES.XL, 4);
    await assertFormContainsNButtonsWithSizeClass(SIZES.XXL, 7);
});

test(`can set bin_size to false in context`, async () => {
    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.context.bin_size).toBe(false);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
        context: {
            bin_size: false,
        },
    });
    expect.verifySteps(["web_read"]);
});

test(`create with false values`, async () => {
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].bar).toBe(false);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="bar"/></form>`,
    });
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`open one2many form containing many2many_tags`, async () => {
    Partner._records[0].product_ids = [37];
    Product._fields.type_ids = fields.Many2many({ relation: "partner.type" });
    Product._records[0].type_ids = [12, 14];

    onRpc(({ method }) => expect.step(method));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <field name="product_ids">
                    <list create="0">
                        <field name="display_name"/>
                        <field name="type_ids" widget="many2many_tags"/>
                    </list>
                    <form>
                        <group>
                            <label for="type_ids"/>
                            <div>
                                <field name="type_ids" widget="many2many_tags"/>
                            </div>
                        </group>
                    </form>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(`.o_data_cell`).click();
    expect.verifySteps(["web_read"]);
});

test(`display toolbar`, async () => {
    mockService("action", {
        doAction(id, { additionalContext }) {
            expect.step("doAction");
            expect(id).toBe(29);
            expect(additionalContext.active_id).toBe(1);
            expect(additionalContext.active_ids).toEqual([1]);
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="bar"/></form>`,
        resId: 1,
        info: {
            actionMenus: {
                action: [
                    {
                        id: 29,
                        name: "Action partner",
                    },
                ],
            },
        },
    });
    await toggleActionMenu();
    expect(`.o_cp_action_menus .dropdown-menu_group:contains(Print)`).toHaveCount(0);
    expect(`.o-dropdown--menu .dropdown-item`).toHaveCount(3);
    expect(queryAllTexts`.o-dropdown--menu .dropdown-item`).toEqual([
        "Duplicate",
        "Delete",
        "Action partner",
    ]);

    await toggleMenuItem("Action partner");
    expect.verifySteps(["doAction"]);
});

test(`execute ActionMenus actions`, async () => {
    mockService("action", {
        doAction(id, { additionalContext, onClose }) {
            expect.step(JSON.stringify({ action_id: id, context: additionalContext }));
            onClose(); // simulate closing of target new action's dialog
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
        arch: `<form><field name="bar"/></form>`,
        info: {
            actionMenus: {
                action: [
                    {
                        id: 29,
                        name: "Action partner",
                    },
                ],
            },
        },
    });
    expect(`.o_cp_action_menus .dropdown-toggle`).toHaveCount(1);
    expect.verifySteps(["get_views", "web_read"]);

    await toggleActionMenu();
    await toggleMenuItem("Action Partner");
    expect.verifySteps([
        `{"action_id":29,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_id":1,"active_ids":[1],"active_model":"partner","active_domain":[]}}`,
        "web_read",
    ]);
});

test(`execute ActionMenus actions (create)`, async () => {
    mockService("action", {
        doAction(id, { additionalContext, onClose }) {
            expect.step(JSON.stringify({ action_id: id, context: additionalContext }));
            onClose(); // simulate closing of target new action's dialog
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        info: {
            actionMenus: {
                action: [
                    {
                        id: 29,
                        name: "Action partner",
                    },
                ],
            },
        },
    });
    expect(`.o_field_widget[name='foo'] input`).toHaveValue("My little Foo Value");
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_field_widget[name='foo'] input`).edit("test");
    expect(`.o_cp_action_menus .dropdown-toggle`).toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Action Partner");
    expect.verifySteps([
        "web_save",
        `{"action_id":29,"context":{"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1],"active_id":6,"active_ids":[6],"active_model":"partner","active_domain":[]}}`,
        "web_read",
    ]);
    expect(`.o_field_widget[name='foo'] input`).toHaveValue("test");
});

test(`control panel is not present in FormViewDialogs`, async () => {
    Partner._records[0].product_id = 37;
    Product._views = {
        form: `<form><field name="display_name"/></form>`,
        list: `<list><field name="display_name"/></list>`,
    };

    onRpc("get_formview_id", () => false);
    await mountViewInDialog({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="product_id"/></form>`,
        resId: 1,
    });
    expect(`.modal`).toHaveCount(1);
    expect(`.o_control_panel`).toHaveCount(0);

    await contains(`.o_external_button`, { visible: false }).click();
    expect(`.modal`).toHaveCount(2);
    expect(`.o_control_panel`).toHaveCount(0);
});

test(`check interactions between multiple FormViewDialogs`, async () => {
    Partner._records[0].product_id = 37;
    Product._fields.product_ids = fields.One2many({ relation: "product" });
    Product._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="product_ids"/>
            </form>
        `,
        list: `<list><field name="name"/></list>`,
    };

    onRpc("get_formview_id", () => false);
    onRpc("web_save", ({ model, args }) => {
        expect.step("web_save");
        expect(model).toBe("product");
        expect(args[1].product_ids[0][2].name).toBe("xtv");
    });
    await mountViewInDialog({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="product_id"/></form>`,
        resId: 1,
    });
    expect(`.modal`).toHaveCount(1);

    await contains(`.o_external_button`, { visible: false }).click();
    expect(`.modal`).toHaveCount(2);
    expect(`.o_dialog:eq(1) .modal-title`).toHaveText("Open: Product");
    expect(`.o_dialog:eq(1) .o_field_widget[name=name] input`).toHaveValue("xphone");

    await contains(`.o_dialog:eq(1) .o_field_x2many_list_row_add a`).click();
    expect(`.modal`).toHaveCount(3);

    await contains(`.o_dialog:eq(2) .o_field_widget[name=name] input`).edit("xtv");
    await contains(`.o_dialog:eq(2) .modal-footer .btn-primary`).click();
    expect(`.modal`).toHaveCount(2);
    expect(`.o_dialog:eq(1) .o_data_row .o_data_cell`).toHaveText("xtv");

    await contains(`.o_dialog:eq(1) .modal-footer .btn-primary`).click();
    expect.verifySteps(["web_save"]);
});

test(`do not activate an hidden tab when switching between records`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <notebook>
                        <page string="Foo" invisible='id == 2'>
                            <field name="foo"/>
                        </page>
                        <page string="Bar">
                            <field name="bar"/>
                        </page>
                    </notebook>
                </sheet>
            </form>
        `,
        resIds: [1, 2],
        resId: 1,
    });
    expect(`.o_notebook .nav-item`).toHaveCount(2);
    expect(`.o_notebook .nav-link:eq(0)`).toHaveClass("active");

    // click on the pager to switch to the next record
    await contains(`.o_pager_next`).click();
    expect(`.o_notebook .nav-item`).toHaveCount(1);
    expect(`.o_notebook .nav-link`).toHaveClass("active");

    // click on the pager to switch back to the previous record
    await contains(`.o_pager_previous`).click();
    expect(`.o_notebook .nav-item`).toHaveCount(2);
    expect(`.o_notebook .nav-link:eq(1)`).toHaveClass("active");
});

test(`support anchor tags with action type`, async () => {
    mockService("action", {
        doActionButton(action) {
            expect.step("doActionButton");
            expect(action.name).toBe("42");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <a type="action" name="42" class="btn-primary"><i class="oi oi-arrow-right"/> Click me !</a>
            </form>
        `,
        resId: 1,
    });
    await contains(`a[type='action']`).click();
    expect(`a[type='action']`).toHaveClass("btn-primary");
    expect.verifySteps(["doActionButton"]);
});

test(`do not perform extra RPC to read invisible many2one fields`, async () => {
    // an invisible manyone should only requests the id, not the display_name
    // -> invisible: { parent_id: {} }, visible: { parent_id: { fields: { display_name }}}
    Partner._fields.parent_id = fields.Many2one({ relation: "partner", default: 2 });

    onRpc("onchange", ({ args }) => {
        expect.step("onchange");
        expect(args[3]).toEqual({
            display_name: {},
            parent_id: {
                fields: {}, // loads "id" only
            },
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="parent_id" invisible="1"/></form>`,
    });
    expect.verifySteps(["onchange"]);
});

test(`do not perform extra RPC to read invisible x2many fields`, async () => {
    Object.assign(Partner._records[0], {
        child_ids: [2], // one2many
        product_ids: [37], // one2many
        type_ids: [12], // many2many
    });

    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.specification).toEqual({
            child_ids: {},
            product_ids: {},
            type_ids: {},
            display_name: {},
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids" widget="one2many" invisible="1"/>
                <field name="product_ids" widget="one2many" invisible="1">
                    <list><field name="display_name"/></list>
                </field>
                <field name="type_ids" invisible="1" widget="many2many_tags"/>
            </form>
        `,
        resId: 1,
    });
    expect.verifySteps(["web_read"]);
});

test(`default_order on x2many embedded view`, async () => {
    Partner._fields.name = fields.Char({ sortable: true });
    Partner._records[0].child_ids = [1, 4];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list default_order="foo desc">
                        <field name="name"/>
                        <field name="foo"/>
                    </list>
                    <form><field name="foo"/></form>,
                </field>
            </form>
        `,
        resId: 1,
    });

    expect(queryAllTexts`.o_data_row .o_data_cell:nth-child(2)`).toEqual([
        "yop",
        "My little Foo Value",
    ]);

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal .o_field_widget[name=foo] input`).edit("xop");
    await contains(`.modal-footer .o_form_button_save_new`).click();
    await contains(`.modal .o_field_widget[name=foo] input`).edit("zop");
    await contains(`.modal-footer .o_form_button_save`).click();

    // client-side sort
    expect(queryAllTexts`.o_data_row .o_data_cell:nth-child(2)`).toEqual([
        "zop",
        "yop",
        "xop",
        "My little Foo Value",
    ]);

    // server-side sort
    await contains(`.o_form_button_save`).click();
    expect(queryAllTexts`.o_data_row .o_data_cell:nth-child(2)`).toEqual([
        "zop",
        "yop",
        "xop",
        "My little Foo Value",
    ]);

    // client-side sort on edit
    await contains(`.o_data_row:eq(1) .o_data_cell:eq(0)`).click();
    await contains(`.modal .o_field_widget[name=foo] input`).edit("zzz");
    await contains(`.modal-footer .o_form_button_save`).click();
    expect(queryAllTexts`.o_data_row .o_data_cell:nth-child(2)`).toEqual([
        "zzz",
        "zop",
        "xop",
        "My little Foo Value",
    ]);
});

test.tags("desktop")(`action context is used when evaluating domains`, async () => {
    onRpc("name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.args[0]).toEqual(["id", "in", [45, 46, 47]]);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="parent_id" domain="[('id', 'in', context.get('product_ids', []))]"/>
            </form>
        `,
        resId: 1,
        context: { product_ids: [45, 46, 47] },
    });
    await contains(`.o_field_widget[name="parent_id"] input`).click();
    expect.verifySteps(["name_search"]);
});

test(`form rendering with groups with col/colspan`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group col="6" class="parent_group">
                        <group col="4" colspan="3" class="group_4">
                            <div colspan="3"/>
                            <div colspan="2"/>
                            <div/>
                            <div colspan="4"/>
                        </group>
                        <group col="3" colspan="4" class="group_3">
                            <group col="1" class="group_1">
                                <div/>
                                <div/>
                                <div/>
                            </group>
                            <div/>
                            <group col="3" class="field_group">
                                <field name="foo" colspan="3"/>
                                <div/>
                                <field name="bar" nolabel="1"/>
                                <field name="float_field"/>
                                <field name="int_field" colspan="3" nolabel="1"/>
                                <span/>
                                <field name="product_id"/>
                            </group>
                        </group>
                    </group>
                    <group>
                        <field name="child_ids">
                            <list>
                                <field name="display_name"/>
                                <field name="foo"/>
                                <field name="int_field"/>
                            </list>
                        </field>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    // Verify outergroup/innergroup
    expect(`.parent_group`).toHaveProperty("tagName", "DIV");
    expect(`.group_4`).toHaveProperty("tagName", "DIV");
    expect(`.group_3`).toHaveProperty("tagName", "DIV");
    expect(`.group_1`).toHaveProperty("tagName", "DIV");
    expect(`.field_group`).toHaveProperty("tagName", "DIV");

    // Verify .parent_group content
    expect(`.parent_group > *`).toHaveCount(2);
    expect(`.parent_group > *:eq(0)`).toHaveClass("col-lg-6");
    expect(`.parent_group > *:eq(1)`).toHaveClass("col-lg-8");

    // Verify .group_4 content
    expect(`.group_4 > div.o_wrap_field`).toHaveCount(3);
    expect(`.group_4 > div.o_wrap_field:eq(0) div.o_cell`).toHaveCount(1);
    expect(`.group_4 > div.o_wrap_field:eq(0) div.o_cell`).toHaveAttribute(
        "style",
        "grid-column: span 3;"
    );
    expect(`.group_4 > div.o_wrap_field:eq(1) div.o_cell`).toHaveCount(2);
    expect(`.group_4 > div.o_wrap_field:eq(1) div.o_cell:eq(0)`).toHaveAttribute(
        "style",
        "grid-column: span 2;"
    );
    expect(`.group_4 > div.o_wrap_field:eq(2) div.o_cell`).toHaveCount(1);
    expect(`.group_4 > div.o_wrap_field:eq(2) div.o_cell`).toHaveAttribute(
        "style",
        "grid-column: span 4;"
    );

    // Verify .group_3 content
    expect(`.group_3 > *`).toHaveCount(3);
    expect(`.group_3 > .col-lg-4`).toHaveCount(3);

    // Verify .group_1 content
    expect(`.group_1 > .o_wrap_field`).toHaveCount(3);

    // Verify .field_group content
    expect(`.field_group > .o_wrap_field`).toHaveCount(5);
    expect(`.field_group > .o_wrap_field:eq(0) .o_cell`).toHaveCount(2);
    expect(`.field_group > .o_wrap_field:eq(0) .o_cell:eq(0)`).toHaveClass("o_wrap_label");
    expect(`.field_group > .o_wrap_field:eq(0) .o_cell:eq(1)`).toHaveAttribute(
        "style",
        "grid-column: span 2;"
    );

    expect(`.field_group > .o_wrap_field:eq(1) .o_cell`).toHaveCount(2);

    expect(`.field_group > .o_wrap_field:eq(2) .o_cell`).toHaveCount(2);
    expect(`.field_group > .o_wrap_field:eq(2) .o_cell:eq(0)`).toHaveClass("o_wrap_label");

    expect(`.field_group > .o_wrap_field:eq(3) .o_cell`).toHaveCount(1);
    expect(`.field_group > .o_wrap_field:eq(3) .o_cell`).toHaveAttribute(
        "style",
        "grid-column: span 3;"
    );

    expect(`.field_group > .o_wrap_field:eq(4) .o_cell`).toHaveCount(3);
    expect(`.field_group > .o_wrap_field:eq(4) .o_cell:eq(1)`).toHaveClass("o_wrap_label");
});

test(`form rendering innergroup: separator should take one line`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group>
                        <group>
                            <separator string="sep"/>
                            <td class="o_td_label">
                                <label for="display_name"/>
                            </td>
                            <field name="display_name" nolabel="1"/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_inner_group > div:eq(0) > .o_cell`).toHaveCount(1);
    expect(`.o_inner_group > div:eq(0) .o_horizontal_separator`).toHaveCount(1);
    expect(`.o_inner_group > div:eq(1) > .o_cell`).toHaveCount(2);
    expect(`.o_inner_group > div:eq(1) label[for=display_name_0]`).toHaveCount(1);
    expect(`.o_inner_group > div:eq(1) div[name=display_name]`).toHaveCount(1);
});

test(`outer and inner groups string attribute`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group string="parent group" class="parent_group">
                        <group string="child group 1" class="group_1">
                            <field name="bar"/>
                        </group>
                        <group string="child group 2" class="group_2">
                            <field name="bar"/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`div.o_inner_group`).toHaveCount(2);
    expect(`.group_1 .o_horizontal_separator`).toHaveCount(1);
    expect(`.group_1 .o_horizontal_separator:contains(child group 1)`).toHaveCount(1);
    expect(`.group_2 .o_horizontal_separator:contains(child group 2)`).toHaveCount(1);
    expect(`.parent_group > div.o_horizontal_separator:contains(parent group)`).toHaveCount(1);
});

test(`inner group with invisible cells`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <group>
                    <div class="cell1" invisible='foo == "1"'/>
                    <div class="cell2" invisible='foo == "2"'/>
                </group>
            </form>
        `,
    });

    await contains(`[name='foo'] input`).edit("1");
    expect(`.o_wrap_field`).toHaveCount(1);
    expect(`.o_wrap_field .cell1`).toHaveCount(0);
    expect(`.o_wrap_field .cell2`).toHaveCount(1);

    await contains(`[name='foo'] input`).edit("2");
    expect(`.o_wrap_field`).toHaveCount(1);
    expect(`.o_wrap_field .cell1`).toHaveCount(1);
    expect(`.o_wrap_field .cell2`).toHaveCount(0);

    await contains(`[name='foo'] input`).edit("3");
    expect(`.o_wrap_field`).toHaveCount(1);
    expect(`.o_wrap_field .cell1`).toHaveCount(1);
    expect(`.o_wrap_field .cell2`).toHaveCount(1);
});

test(`form group with newline tag inside`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <group col="5" class="main_inner_group">
                        <!-- col=5 otherwise the test is ok even without the
                        newline code as this will render a <newline/> DOM
                        element in the third column, leaving no place for
                        the next field and its label on the same line. -->
                        <field name="foo"/>
                        <newline/>
                        <field name="bar"/>
                        <field name="float_field"/>
                    </group>
                    <group col="3">
                        <!-- col=3 otherwise the test is ok even without the
                        newline code as this will render a <newline/> DOM
                        element with the g-col-2 class, leaving no
                        place for the next group on the same line. -->
                        <group class="top_group">
                            <div style="height: 200px;"/>
                        </group>
                        <newline/>
                        <group class="bottom_group">
                            <div/>
                        </group>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });

    // Inner group
    expect(`.main_inner_group > .o_wrap_field`).toHaveCount(2);
    expect(`.main_inner_group > .o_wrap_field:first > .o_wrap_label`).toHaveCount(1);
    expect(`.main_inner_group > .o_wrap_field:first .o_field_widget`).toHaveCount(1);
    expect(`.main_inner_group > .o_wrap_field:last .o_wrap_label`).toHaveCount(2);
    expect(`.main_inner_group > .o_wrap_field:last .o_field_widget`).toHaveCount(2);

    // Outer group
    const bottomGroupRect = queryFirst(`.bottom_group`).getBoundingClientRect();
    const topGroupRect = queryFirst(`.top_group`).getBoundingClientRect();
    expect(bottomGroupRect.top - topGroupRect.top).toBeGreaterThan(200, {
        message: "outergroup children should not be on the same line",
    });
});

test(`custom open record dialog title`, async () => {
    Partner._records[0].child_ids = [2];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids" widget="many2many" string="custom label">
                    <list><field name="display_name"/></list>
                    <form><field name="display_name"/></form>
                </field>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.modal .modal-title`).toHaveText("Open: custom label");
});

test(`can save without any dirty translatable fields`, async () => {
    serverState.multiLang = true;

    onRpc(({ method }) => expect.step(method));
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="name"/></form>`,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);
    expect(`.o_form_editable`).toHaveCount(1);
    // o_field_translate is on the input and on the translate button
    expect(`div[name='name'] .o_field_translate`).toHaveCount(2);

    await contains(`.o_form_button_save`, { visible: false }).click();
    expect(`.alert .o_field_translate`).toHaveCount(0);
    expect(`.o_form_saved`).toHaveCount(1);
    expect.verifySteps([]);
});

test(`translation dialog with right context and domain`, async () => {
    installLanguages({
        CUST: "custom lang",
        CUST2: "second custom",
    });

    onRpc("get_field_translations", ({ args, kwargs }) => {
        expect.step(`translate args ${JSON.stringify(args)}`);
        expect.step(`translate context ${JSON.stringify(kwargs.context)}`);
        return [
            [
                { lang: "CUST", source: "yop", value: "yop" },
                { lang: "CUST2", source: "yop", value: "valeur français" },
            ],
            { translation_type: "char", translation_show_source: false },
        ];
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="name"/></form>`,
        resId: 1,
    });
    await contains(".o_field_translate").click();
    await contains(`.o_field_translate.btn-link`).click();
    expect.verifySteps([
        `translate args [[1],"name"]`,
        `translate context {"lang":"en","tz":"taht","uid":7,"allowed_company_ids":[1]}`,
    ]);
    expect(`.modal`).toHaveCount(1);
    expect(`.modal-title`).toHaveText("Translate: name");
});

test(`save new record before opening translate dialog`, async () => {
    installLanguages({
        CUST: "custom lang",
        CUST2: "second custom",
    });

    onRpc("call_button", () => ({ context: {}, domain: [] }));
    onRpc("get_field_translations", () => [
        [
            { lang: "CUST", source: "yop", value: "yop" },
            { lang: "CUST2", source: "yop", value: "valeur français" },
        ],
        { translation_type: "char", translation_show_source: false },
    ]);
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="name"/></form>`,
    });
    expect.verifySteps(["get_views", "onchange"]);
    expect(`.o_form_editable`).toHaveCount(1);

    await contains(`.o_field_translate`).click();
    await contains(`.o_field_translate.btn-link`).click();
    expect.verifySteps(["web_save", "get_field_translations"]);
    expect(`.modal`).toHaveCount(1);
    expect(`.modal-title`).toHaveText("Translate: name");
});

test(`translate event correctly handled with multiple controllers`, async () => {
    installLanguages({
        en_US: "English",
        fr_BE: "French (Belgium)",
    });

    Partner._records[0].product_id = 37;
    Product._fields.name = fields.Char({ translate: true });
    Product._views = {
        form: `
            <form>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="partner_type_id"/>
                    </group>
                </sheet>
            </form>
        `,
    };

    onRpc("get_formview_id", () => false);
    onRpc("get_field_translations", () => {
        expect.step("get_field_translations");
        return [
            [
                { lang: "en_US", source: "yop", value: "yop" },
                { lang: "fr_BE", source: "yop", value: "valeur français" },
            ],
            { translation_type: "char", translation_show_source: false },
        ];
    });
    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="product_id"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    expect(`.o_dialog`).toHaveCount(1);

    await contains(`[name="product_id"] .o_external_button`, { visible: false }).click();
    await contains(`.o_field_translate`).click();
    expect(`.o_dialog:eq(1) span.o_field_translate`).toHaveCount(1);

    await contains(`.o_dialog:eq(1) span.o_field_translate`).click();
    expect.verifySteps(["get_field_translations"]);
});

test.tags("desktop")(`buttons are disabled until status bar action is resolved`, async () => {
    const deferred = new Deferred();
    mockService("action", {
        async doActionButton() {
            await deferred;
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object"/>
                    <button name="some_method" class="s" string="Do it" type="object"/>
                </header>
                <sheet>
                    <div name="button_box" class="oe_button_box">
                        <button class="oe_stat_button" name="some_action" type="action">
                            <field name="bar"/>
                        </button>
                    </div>
                    <group>
                        <field name="foo"/>
                    </group>
                </sheet>
            </form>
        `,
        resId: 1,
    });
    // Contains invisible buttons that are only displayed under xl screens
    expect(`.o_control_panel_breadcrumbs button:not(.fa):not(:disabled)`).toHaveCount(3);
    expect(`.o_form_statusbar button:not(:disabled)`).toHaveCount(2);
    expect(`.o-form-buttonbox button:not(:disabled)`).toHaveCount(1);

    await contains(`.o_form_statusbar button`).click();
    await animationFrame();

    // The unresolved promise lets us check the state of the buttons
    expect(`.o_control_panel_breadcrumbs button:not(.fa):disabled`).toHaveCount(3);
    expect(`.o_form_statusbar button:disabled`).toHaveCount(2);
    expect(`.o-form-buttonbox button:disabled`).toHaveCount(1);

    deferred.resolve();
    await animationFrame();
    expect(`.o_control_panel_breadcrumbs button:not(.fa):not(:disabled)`).toHaveCount(3);
    expect(`.o_form_statusbar button:not(:disabled)`).toHaveCount(2);
    expect(`.o-form-buttonbox button:not(:disabled)`).toHaveCount(1);
});

test.tags("desktop");
test(`buttons with "confirm" attribute save before calling the method on desktop`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("execute_action");
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object" confirm="Very dangerous. U sure?"/>
                </header>
                <sheet>
                    <field name="foo"/>
                </sheet>
            </form>
        `,
    });

    // click on button, and cancel in confirm dialog
    await contains(`.o_statusbar_buttons button`).click();
    expect(`.o_statusbar_buttons button`).not.toBeEnabled();

    await contains(`.modal-footer button.btn-secondary`).click();
    expect(`.o_statusbar_buttons button`).toBeEnabled();

    expect.verifySteps(["get_views", "onchange"]);

    // click on button, and click on ok in confirm dialog
    await contains(`.o_statusbar_buttons button`).click();
    expect.verifySteps([]);
    await contains(`.modal-footer button.btn-primary`).click();
    expect.verifySteps(["web_save", "execute_action"]);
});

test.tags("mobile");
test(`buttons with "confirm" attribute save before calling the method on mobile`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("execute_action");
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object" confirm="Very dangerous. U sure?"/>
                </header>
                <sheet>
                    <field name="foo"/>
                </sheet>
            </form>
        `,
    });

    // click on button, and cancel in confirm dialog
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(`.o-dropdown-item-unstyled-button button`).click();
    expect(`.o-dropdown-item-unstyled-button button`).not.toBeEnabled();

    await contains(`.modal-footer button.btn-secondary`).click();
    expect(`.o-dropdown-item-unstyled-button button`).toBeEnabled();

    expect.verifySteps(["get_views", "onchange"]);

    // click on button, and click on ok in confirm dialog
    await contains(`.o-dropdown-item-unstyled-button button`).click();
    expect.verifySteps([]);
    await contains(`.modal-footer button.btn-primary`).click();
    expect.verifySteps(["web_save", "execute_action"]);
});

test.tags("desktop");
test(`buttons with "confirm-title" and "confirm-label" attributes on desktop`, async () => {
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object" confirm="Very dangerous. U sure?"
                        confirm-title="Confirm Title" confirm-label="Confirm Label"/>
                </header>
                <sheet>
                    <field name="foo"/>
                </sheet>
            </form>
        `,
    });
    await contains(`.o_statusbar_buttons button`).click();
    expect(`.modal-title`).toHaveText("Confirm Title");
    expect(`.modal-footer button.btn-primary`).toHaveText("Confirm Label");
    expect.verifySteps(["get_views", "onchange"]);
});

test.tags("mobile");
test(`buttons with "confirm-title" and "confirm-label" attributes on mobile`, async () => {
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object" confirm="Very dangerous. U sure?"
                        confirm-title="Confirm Title" confirm-label="Confirm Label"/>
                </header>
                <sheet>
                    <field name="foo"/>
                </sheet>
            </form>
        `,
    });
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(`.o-dropdown-item-unstyled-button button`).click();
    expect(`.modal-title`).toHaveText("Confirm Title");
    expect(`.modal-footer button.btn-primary`).toHaveText("Confirm Label");
    expect.verifySteps(["get_views", "onchange"]);
});

test.tags("desktop");
test(`buttons with "confirm" attribute: click twice on "Ok" on desktop`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("execute_action"); // should be called only once
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object" confirm="U sure?"/>
                </header>
            </form>
        `,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_statusbar_buttons button`).click();
    expect.verifySteps([]);

    contains(`.modal-footer button.btn-primary`).click();
    await animationFrame();
    expect(`.modal-footer button.btn-primary`).not.toBeEnabled();
    expect.verifySteps(["web_save", "execute_action"]);
});

test.tags("mobile")(`buttons with "confirm" attribute: click twice on "Ok" on mobile`, async () => {
    mockService("action", {
        doActionButton() {
            expect.step("execute_action"); // should be called only once
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="post" class="child_ids" string="Confirm" type="object" confirm="U sure?"/>
                </header>
            </form>
        `,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(`.o-dropdown-item-unstyled-button button`).click();
    expect.verifySteps([]);

    contains(`.modal-footer button.btn-primary`).click();
    await animationFrame();
    expect(`.modal-footer button.btn-primary`).not.toBeEnabled();
    expect.verifySteps(["web_save", "execute_action"]);
});

test(`multiple clicks on save should reload only once`, async () => {
    const deferred = new Deferred();

    onRpc("web_save", () => deferred);
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);
    await contains(`.o_field_widget[name="foo"] input`).edit("test");
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_button_save`).not.toBeEnabled(); // Save button is disabled, it can't be clicked

    deferred.resolve();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test(`form view is not broken if save operation fails`, async () => {
    expect.errors(1);

    onRpc("web_save", ({ args }) => {
        if (args[1].foo === "incorrect value") {
            throw makeServerError();
        }
    });
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(`.o_field_widget[name=foo] input`).edit("incorrect value");
    await contains(`.o_form_button_save`).click();
    await animationFrame();
    expect(`.o_dialog`).toHaveCount(1);
    expect.verifyErrors(["RPC_ERROR: Odoo Server Error"]);
    expect.verifySteps(["web_save"]); // write on save (it fails, does not trigger a read)

    await contains(`.o_dialog .modal-footer .btn-primary`).click();
    await contains(`.o_field_widget[name=foo] input`).edit("correct value");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]); // write on save (it works)
});

test(`form view is not broken if save failed in readonly mode on field changed`, async () => {
    expect.errors(1);

    let failFlag = false;
    onRpc("web_save", () => {
        expect.step("web_save");
        if (failFlag) {
            throw makeServerError();
        }
    });
    onRpc("web_read", () => expect.step("web_read"));

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <field name="parent_id" widget="statusbar" options="{'clickable': '1'}"/>
                </header>
            </form>
        `,
        mode: "readonly",
        resId: 1,
    });
    expect.verifySteps(["web_read"]);
    expect(`button[data-value="4"]`).toHaveClass("o_arrow_button_current");
    expect(`button[data-value="4"]`).not.toBeEnabled();

    failFlag = true;
    await contains(`button[data-value="1"]`).click();
    expect(`button[data-value="4"]`).toHaveClass("o_arrow_button_current");
    expect.verifyErrors(["RPC_ERROR: Odoo Server Error"]);
    expect.verifySteps(["web_save", "web_read"]); // must reload when saving fails

    failFlag = false;
    await contains(`button[data-value="1"]`).click();
    expect(`button[data-value="4"]`).toHaveClass("o_arrow_button_current");
    expect.verifySteps(["web_save"]);
});

test.tags("desktop")(`context is correctly passed after save & new in FormViewDialog`, async () => {
    Product._views = {
        form: `<form><field name="partner_type_id" context="{'color': parent.id}"/></form>`,
        list: `<list><field name="display_name"/></list>`,
    };

    onRpc("name_search", ({ kwargs }) => {
        expect.step("name_search");
        expect(kwargs.context.color).toBe(4);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="product_ids"/></form>`,
        resId: 4,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.modal`).toHaveCount(1);

    // set a value on the m2o and click save & new
    await contains(`.o_field_many2one[name="partner_type_id"] input`).click();
    expect.verifySteps(["name_search"]);

    await contains(`.dropdown .dropdown-item:contains(gold)`).click();
    await contains(`.modal-footer .o_form_button_save_new`).click();

    // set a value on the m2o
    await contains(`.o_field_many2one[name="partner_type_id"] input`).click();
    expect.verifySteps(["name_search"]);

    await contains(`.dropdown .dropdown-item:contains(silver)`).click();
    await contains(`.modal-footer .o_form_button_save`).click();
});

test(`readonly fields are not sent when saving`, async () => {
    // define an onchange on name to check that the value of readonly
    // fields is correctly sent for onchanges
    Partner._onChanges = {
        name() {},
        child_ids() {},
    };
    let checkOnchange = false;

    onRpc("onchange", ({ args }) => {
        if (checkOnchange) {
            expect.step("onchange");
            if (args[2][0] === "name") {
                // onchange on field name
                expect(args[1].foo).toBe("foo value");
            } else {
                // onchange on field p
                expect(args[1].child_ids).toEqual([
                    [0, args[1].child_ids[0][1], { name: "readonly", foo: "foo value" }],
                ]);
            }
        }
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({
            child_ids: [[0, args[1].child_ids[0][1], { name: "readonly" }]],
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list><field name="name"/></list>
                    <form>
                        <field name="name"/>
                        <field name="foo" readonly="name == 'readonly'"/>
                    </form>
                </field>
            </form>
        `,
    });

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.modal .o_field_widget[name=foo] input`).toHaveCount(1);

    checkOnchange = true;
    await contains(`.modal .o_field_widget[name=foo] input`).edit("foo value");
    await contains(`.modal .o_field_widget[name=name] input`).edit("readonly");
    expect.verifySteps(["onchange"]);
    expect(`.modal .o_field_widget[name=foo] input`).toHaveCount(0);

    await contains(`.modal-footer .btn-primary`).click();
    expect.verifySteps(["onchange"]);

    checkOnchange = false;
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.modal .o_field_widget[name=foo]`).toHaveText("foo value");
    await contains(`.modal-footer .btn-primary`).click();

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`id is False in evalContext for new records`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="id"/>
                <field name="foo" readonly="not id"/>
            </form>
        `,
    });
    expect(`.o_field_widget[name=foo]`).toHaveClass("o_readonly_modifier");

    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name=foo]`).not.toHaveClass("o_readonly_modifier");
});

test(`delete a duplicated record`, async () => {
    const newRecordID = 6; // ids from 1 to 5 are already taken so the new record will have id 6
    onRpc("unlink", ({ args }) => {
        expect.step("unlink");
        expect(args[0]).toEqual([newRecordID]);
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="display_name"/></form>`,
        resId: 1,
        actionMenus: {},
    });

    await toggleActionMenu();
    await toggleMenuItem("Duplicate");
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget`).toHaveText("first record (copy)");

    await toggleActionMenu();
    await toggleMenuItem("Delete");
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal-footer .btn-primary`).click();
    expect(`.o_field_widget`).toHaveText("first record");
    expect.verifySteps(["unlink"]);
});

test.tags("desktop")(`display tooltips for buttons (debug = false)`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="some_method" class="oe_highlight" string="Button" type="object" title="This is title"/>
                    <button name="empty_method" string="Empty Button" type="object"/>
                </header>
                <button name="other_method" class="oe_highlight" string="Button2" type="object" help="help Button2"/>
            </form>
        `,
    });

    await hover(`button[name='empty_method']`);
    await runAllTimers();
    expect(`.o-tooltip`).toHaveCount(0);

    await hover(`button[name='some_method']`);
    await runAllTimers();
    expect(`.o-tooltip`).toHaveText("This is title");

    await hover(`button[name='other_method']`);
    await runAllTimers();
    expect(`.o-tooltip`).toHaveText("Button2\n\nhelp Button2");
});

test.tags("desktop")(`display tooltips for buttons (debug = true)`, async () => {
    serverState.debug = true;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="some_method" class="oe_highlight" string="Button" type="object" title="This is title" readonly="display_name == 'readonly'"/>
                    <button name="empty_method" string="Empty Button" type="object"/>
                </header>
                <button name="other_method" class="oe_highlight" string="Button2" type="object" help="help Button2"/>
            </form>
        `,
    });

    await hover(`button[name='empty_method']`);
    await runAllTimers();
    expect(`.o-tooltip`).toHaveText(
        "Button : Empty Button\nObject:partner\nButton Type:object\nMethod:empty_method"
    );

    await hover(`button[name='some_method']`);
    await runAllTimers();
    expect(`.o-tooltip`).toHaveText(
        `Button : Button\n\nThis is title\n\nObject:partner\nReadonly:display_name == 'readonly'\nButton Type:object\nMethod:some_method`
    );

    await hover(`button[name='other_method']`);
    await runAllTimers();
    expect(`.o-tooltip`).toHaveText(
        `Button : Button2\n\nhelp Button2\n\nObject:partner\nButton Type:object\nMethod:other_method`
    );
});

test(`reload event is handled only once`, async () => {
    // In this test, several form controllers are nested (all of them are
    // opened in dialogs). When the users clicks on save in the last
    // opened dialog, a 'reload' event is triggered up to reload the (direct)
    // parent view. If this event isn't stopPropagated by the first controller
    // catching it, it will crash when the other one will try to handle it,
    // as this one doesn't know at all the dataPointID to reload.
    Partner._views = {
        form: `<form><field name="name"/><field name="parent_id"/></form>`,
    };

    onRpc("get_formview_id", () => false);
    onRpc(({ method }) => expect.step(method));
    await mountViewInDialog({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="display_name"/><field name="parent_id"/></form>`,
        resId: 2,
    });
    expect.verifySteps(["get_views", "web_read"]);
    expect(`.o_dialog`).toHaveCount(1);

    await contains(`.o_external_button`, { visible: false }).click();
    expect(`.o_dialog`).toHaveCount(2);
    expect.verifySteps([
        "get_formview_id", // id of first form view opened in a dialog
        "get_views", // arch of first form view opened in a dialog
        "web_read", // first dialog
    ]);

    await contains(`.o_dialog:eq(1) .o_external_button`, { visible: false }).click();
    expect(`.o_dialog`).toHaveCount(3);
    expect.verifySteps([
        "get_formview_id", // id of second form view opened in a dialog
        "web_read", // second dialog
    ]);

    await contains(`.o_dialog:eq(2) .o_field_widget[name=name] input`).edit("new name");
    await contains(`.o_dialog:eq(2) footer .o_form_button_save`).click();
    expect.verifySteps([
        "web_save",
        "read", // reload the name (first dialog)
    ]);
    expect(`.o_dialog:eq(1) .o_field_widget[name="parent_id"] input`).toHaveValue("new name");
});

test(`process the context for inline subview`, async () => {
    Partner._records[0].child_ids = [2];

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list>
                        <field name="foo"/>
                        <field name="bar" column_invisible="context.get('hide_bar', False)"/>
                        <field name="int_field" column_invisible="True"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
        context: { hide_bar: true },
    });
    expect(`.o_list_renderer thead tr th:not(.o_list_actions_header)`).toHaveCount(1);
});

test.tags("desktop")(`process the context for subview not inline`, async () => {
    Partner._records[0].child_ids = [2];
    Partner._views = {
        list: `
            <list>
                <field name="foo"/>
                <field name="bar" column_invisible="context.get('hide_bar', False)"/>
            </list>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="child_ids" widget="one2many"/></form>`,
        resId: 1,
        context: { hide_bar: true },
    });
    expect(`.o_list_renderer thead tr th:not(.o_list_actions_header)`).toHaveCount(1);
});

test(`Can switch to form view on inline tree`, async () => {
    const id = 2;
    mockService("action", {
        doAction(action, options) {
            expect.step("doAction");
            expect(action).toEqual({
                res_id: id,
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            });
            expect(options.props).toEqual({ resIds: [id] });
        },
    });

    Partner._records[0].child_ids = [id];
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="top" open_form_view="1">
                        <field name="foo"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    expect(`td.o_list_record_open_form_view`).toHaveCount(1);

    await contains(`td.o_list_record_open_form_view`).click();
    expect.verifySteps(["doAction"]);
});

test(`can toggle column in x2many in sub form view`, async () => {
    Partner._records[2].child_ids = [1, 2];
    Partner._fields.foo = fields.Char({ sortable: true });
    Partner._views = {
        form: `
            <form>
                <field name="child_ids">
                    <list><field name="foo"/></list>
                </field>
            </form>
        `,
    };

    onRpc("get_formview_id", () => false);
    await mountViewInDialog({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="parent_id"/></form>`,
        resId: 1,
    });
    await contains(`.o_external_button`, { visible: false }).click();
    expect(queryAllTexts`.o_dialog:not(.o_inactive_modal) .o_data_cell`).toEqual(["yop", "blip"]);

    await contains(`.o_dialog:not(.o_inactive_modal) th.o_column_sortable`).click();
    expect(queryAllTexts`.o_dialog:not(.o_inactive_modal) .o_data_cell`).toEqual(["blip", "yop"]);
});

test.tags("desktop");
test(`rainbowman attributes correctly passed on button click on desktop`, async () => {
    mockService("action", {
        doActionButton({ effect }) {
            expect.step("doActionButton");
            expect(effect).toBe("{'message': 'Congrats!'}");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="action_won" string="Won" type="object" effect="{'message': 'Congrats!'}"/>
                </header>
            </form>
        `,
    });
    await contains(`.o_form_statusbar .btn-secondary`).click();
    expect.verifySteps(["doActionButton"]);
});

test.tags("mobile");
test(`rainbowman attributes correctly passed on button click on mobile`, async () => {
    mockService("action", {
        doActionButton({ effect }) {
            expect.step("doActionButton");
            expect(effect).toBe("{'message': 'Congrats!'}");
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <header>
                    <button name="action_won" string="Won" type="object" effect="{'message': 'Congrats!'}"/>
                </header>
            </form>
        `,
    });
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    await contains(`.o-dropdown-item-unstyled-button button`).click();
    expect.verifySteps(["doActionButton"]);
});

test(`basic support for widgets`, async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<div t-esc="value"/>`;
        get value() {
            return JSON.stringify(this.props.record.data);
        }
    }
    widgetsRegistry.add("test_widget", { component: MyComponent });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="bar"/>
                <widget name="test_widget"/>
            </form>
        `,
    });
    expect(`.o_widget`).toHaveText(`{"foo":"My little Foo Value","bar":false,"display_name":""}`);
});

test(`widget with class attribute`, async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<span>Hello</span>`;
    }
    widgetsRegistry.add("test_widget", { component: MyComponent });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><widget name="test_widget" class="my_classname"/></form>`,
    });
    expect(`.o_widget.my_classname`).toHaveCount(1);
});

test(`widget with readonly attribute`, async () => {
    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<span t-esc="value"/>`;
        get value() {
            return this.props.readonly ? "readonly" : "not readonly";
        }
    }
    widgetsRegistry.add("test_widget", {
        component: MyComponent,
        extractProps(widgetInfo, dynamicInfo) {
            return { readonly: dynamicInfo.readonly };
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="bar"/>
                <widget name="test_widget" readonly="bar"/>
            </form>
        `,
    });
    expect(`.o_widget`).toHaveText("not readonly");

    await contains(`.o_field_widget[name=bar] input`).click();
    expect(`.o_widget`).toHaveText("readonly");
});

test.tags("desktop")(`support header button as widgets on form statusbar on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><header><widget name="attach_document" string="Attach document"/></header></form>`,
    });
    expect(`button.o_attachment_button`).toHaveCount(1);
    expect(`span.o_attach_document`).toHaveText("Attach document");
});

test.tags("mobile")(`support header button as widgets on form statusbar on mobile`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><header><widget name="attach_document" string="Attach document"/></header></form>`,
    });
    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    expect(`button.o_attachment_button`).toHaveCount(1);
    expect(`span.o_attach_document`).toHaveText("Attach document");
});

test(`basic support for widgets: onchange update`, async () => {
    class MyWidget extends Component {
        static props = ["*"];
        static template = xml`<t t-esc="state.dataToDisplay" />`;
        setup() {
            this.state = useState({
                dataToDisplay: this.props.record.data.foo,
            });
            useEffect(() => {
                this.state.dataToDisplay = this.props.record.data.foo + "!";
            });
        }
    }
    widgetsRegistry.add("test_widget", { component: MyWidget });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><widget name="test_widget"/></form>`,
    });
    await contains(`.o_field_widget[name="foo"] input`).edit("I am alive");
    await animationFrame(); // wait for effect
    expect(`.o_widget`).toHaveText("I am alive!");
});

test.tags("desktop")(`proper stringification in debug mode tooltip`, async () => {
    serverState.debug = true;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" domain="[]" context="{'lang': 'en_US'}" invisible="product_id == 33" widget="many2one"/>
                </sheet>
            </form>
        `,
    });

    await hover(`[name='product_id']`);
    await runAllTimers();
    expect(`.o-tooltip--technical > li[data-item="context"]`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="context"]`).toHaveText(/{'lang': 'en_US'}/);
    expect(`.o-tooltip--technical > li[data-item="domain"]`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="domain"]`).toHaveText(/\[\]/);
    expect(`.o-tooltip--technical > li[data-item="invisible"]`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="invisible"]`).toHaveText(/product_id == 33/);
    expect(`.o-tooltip--technical > li[data-item="widget"]`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="widget"]`).toHaveText(
        /Widget:Many2one \(many2one\)/
    );
});

test.tags("desktop")(`field tooltip in debug mode, on field with domain attr`, async () => {
    serverState.debug = true;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="product_id" domain="[['id', '>', 3]]"/>
                </sheet>
            </form>
        `,
    });

    await hover(`[name='product_id']`);
    await runAllTimers();
    expect(`.o-tooltip--technical > li[data-item="domain"]`).toHaveCount(1);
    expect(`.o-tooltip--technical > li[data-item="domain"]`).toHaveText(/\[\['id', '>', 3\]\]/);
});

test.tags("desktop")(`do not display unset attributes in debug field tooltip`, async () => {
    serverState.debug = true;

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="product_id"/>
                </sheet>
            </form>
        `,
    });

    await hover(`[name='product_id']`);
    await runAllTimers();
    expect(queryAllTexts`.o-tooltip--technical > li`).toEqual([
        "Label:Product",
        "Field:product_id",
        "Type:many2one",
        "Context:{}",
        "Relation:product",
    ]);
});

test.tags("desktop")(`do not change pager when discarding current record on desktop`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resIds: [1, 2],
        resId: 2,
    });
    expect(getPagerValue()).toEqual([2]);
    expect(getPagerLimit()).toBe(2);

    await contains(`.o_form_button_cancel`, { visible: false }).click();
    expect(getPagerValue()).toEqual([2]);
    expect(getPagerLimit()).toBe(2);
});

test.tags("desktop")(`coming to a form view from a grouped and sorted list`, async () => {
    defineActions([
        {
            id: 1,
            name: "test",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    Partner._fields.foo = fields.Char({ default: "My little Foo Value", sortable: true });
    Partner._records[0].type_ids = [12, 14];
    Partner._views = {
        list: `<list><field name="foo"/></list>`,
        search: `
            <search>
                <filter string="bar" name="Bar" context="{'group_by': 'bar'}"/>
            </search>
        `,
        form: `
            <form>
                <field name="foo"/>
                <field name="type_ids"/>
            </form>
        `,
    };
    PartnerType._views = {
        list: `<list><field name="display_name"/></list>`,
    };

    onRpc("partner", "web_read", ({ kwargs }) => {
        expect(kwargs.context).toEqual({
            bin_size: true,
            lang: "en",
            tz: "taht",
            uid: 7,
            allowed_company_ids: [1],
        });
    });
    onRpc(({ model, method }) => expect.step(`${model}:${method}`));

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect.verifySteps(["partner:get_views", "partner:web_search_read", "res.users:has_group"]);
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(4);
    expect(queryAllTexts`.o_data_cell`).toEqual(["yop", "blip", "My little Foo Value", ""]);

    await contains(`th.o_column_sortable`).click();
    expect(queryAllTexts`.o_data_cell`).toEqual(["", "My little Foo Value", "blip", "yop"]);
    expect.verifySteps(["partner:web_search_read"]);

    await toggleSearchBarMenu();
    await toggleMenuItem("bar");
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(0);
    expect.verifySteps(["partner:web_read_group"]);

    await contains(`.o_group_header:eq(1)`).click();
    expect(`.o_group_header`).toHaveCount(2);
    expect(`.o_data_row`).toHaveCount(2);
    expect.verifySteps(["partner:web_search_read"]);

    await contains(`.o_data_row:eq(1) .o_data_cell`).click();
    expect(`.o_form_view`).toHaveCount(1);
    expect(queryAllTexts`.o_data_cell`).toEqual(["gold", "silver"]);
    expect.verifySteps(["partner:web_read"]);
});

test.tags("desktop")(`keep editing after call_button fail`, async () => {
    expect.errors(1);

    let values = null;
    mockService("action", {
        doActionButton({ name, type }) {
            expect([name, type]).toEqual(["post", "object"]);
            throw makeServerError();
        },
    });

    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].child_ids[0][2]).toEqual(values);
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <button name="post" class="child_ids" string="Raise Error" type="object"/>
                <field name="child_ids">
                    <list editable="top">
                        <field name="name"/>
                        <field name="product_id"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_field_widget[name=name] input`).edit("abc", { confirm: false });
    values = {
        name: "abc",
        product_id: false,
    };
    await contains(`button.child_ids`).click();
    expect.verifySteps(["web_save"]);
    expect.verifyErrors(["RPC_ERROR: Odoo Server Error"]);

    await contains(`.o_form_view .o_field_one2many .o_data_row .o_data_cell:eq(1)`).click();
    await contains(`.o_field_many2one[name="product_id"] input`).click();
    await contains(`.dropdown .dropdown-item:contains(xphone)`).click();
    expect(`.o_field_many2one input`).toHaveValue("xphone");

    values = {
        product_id: 37,
    };
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`no deadlock when saving with uncommitted changes`, async () => {
    // Before saving a record, all field widgets are asked to commit their changes (new values
    // that they wouldn't have sent to the model yet). This test is added alongside a bug fix
    // ensuring that we don't end up in a deadlock when a widget actually has some changes to
    // commit at that moment. By chance, this situation isn't reached when the user clicks on
    // 'Save' (which is the natural way to save a record), because by clicking outside the
    // widget, the 'change' event (this is mainly for InputFields) is triggered, and the widget
    // notifies the model of its new value on its own initiative, before being requested to.
    // In this test, we try to reproduce the deadlock situation by forcing the field widget to
    // commit changes before the save. We thus manually call 'saveRecord', instead of clicking
    // on 'Save'.
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_field_widget[name=foo] input`).edit("some foo value");
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget[name=foo] input`).toHaveValue("some foo value");
    expect.verifySteps(["web_save"]);
});

test(`saving with invalid uncommitted changes`, async () => {
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="float_field"/></form>`,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_field_widget[name=float_field] input`).edit("some float_field value");
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_form_view .o_form_editable input`).toHaveValue("some float_field value");
    expect(`[name=float_field]`).toHaveClass("o_field_invalid");
    expect(`.o_notification_bar.bg-danger`).toHaveCount(1);
    expect(`.o_form_editable .o_field_invalid[name=float_field]`).toHaveCount(1);
    expect.verifySteps([]);
});

test(`save record with onchange on one2many with required field`, async () => {
    // in this test, we have a one2many with a required field, whose value is
    // set by an onchange on another field ; we manually set the value of that
    // first field, and directly click on Save (before the onchange RPC returns
    // and sets the value of the required field)

    Partner._fields.foo = fields.Char();
    Partner._onChanges = {
        name(record) {
            record.foo = record.name ? "foo value" : undefined;
        },
    };

    let onchangeDeferred = undefined;
    onRpc("onchange", () => onchangeDeferred);
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1].child_ids[0][2].foo).toBe("foo value");
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="top">
                        <field name="name"/>
                        <field name="foo" required="1"/>
                    </list>
                </field>
            </form>
        `,
    });

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.o_field_widget[name=name] input`).toHaveValue("");
    expect(`.o_field_widget[name=foo] input`).toHaveValue("");

    onchangeDeferred = new Deferred();
    await contains(`.o_field_widget[name=name] input`).edit("some value");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps([]);

    onchangeDeferred.resolve();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test.tags("desktop")(`leave the form view while saving`, async () => {
    Partner._onChanges = {
        foo(record) {
            record.name = record.foo === "trigger onchange" ? "changed" : "default";
        },
    };
    Partner._views = {
        list: `<list><field name="name"/></list>`,
        form: `
            <form>
                <field name="name"/>
                <field name="foo"/>
            </form>
        `,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "test",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    let onchangeDeferred = undefined;
    onRpc("onchange", () => onchangeDeferred);

    const createDeferred = new Deferred();
    onRpc("web_save", () => createDeferred);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(`.o_control_panel_main_buttons button.o_list_button_add`).click();

    // edit foo to trigger a delayed onchange
    onchangeDeferred = new Deferred();
    await contains(`.o_field_widget[name=foo] input`).edit("trigger onchange");
    expect(`.o_field_widget[name=name] input`).toHaveValue("default");

    // save (will wait for the onchange to return), and will be delayed as well
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget[name=name] input`).toHaveValue("default");

    // click on the breadcrumbs to leave the form view
    await contains(`.breadcrumb-item.o_back_button a`).click();
    await animationFrame();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget[name=name] input`).toHaveValue("default");

    // unlock the onchange
    onchangeDeferred.resolve();
    await animationFrame();
    expect(`.o_form_editable`).toHaveCount(1);
    expect(`.o_field_widget[name=name] input`).toHaveValue("changed");

    // unlock the create
    createDeferred.resolve();
    await animationFrame();
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_list_table .o_data_row:last-child td.o_data_cell`).toHaveText("changed");
});

test.tags("desktop");
test(`leave the form twice (clicking on the breadcrumb) should save only once`, async () => {
    defineActions([
        {
            id: 1,
            name: "test",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    Partner._views = {
        list: `<list><field name="foo"/></list>`,
        search: `<search/>`,
        form: `
                <form>
                    <field name="display_name"/>
                    <field name="foo"/>
                </form>
            `,
    };

    const writeDeferred = new Deferred();
    onRpc("web_save", async () => {
        await writeDeferred;
        expect.step("web_save");
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    // switch to form view
    await contains(`.o_list_table .o_data_row .o_data_cell`).click();
    expect(`.o_form_editable`).toHaveCount(1);

    await contains(`.o_field_widget[name=foo] input`).edit("some value");
    await contains(`.breadcrumb-item.o_back_button a`).click();
    expect(`.modal`).toHaveCount(0);
    expect.verifySteps([]);

    await contains(`.breadcrumb-item.o_back_button a`).click();
    expect(`.modal`).toHaveCount(0);
    expect.verifySteps([]);

    // unlock the create
    writeDeferred.resolve();
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test.tags("desktop")(`discard after a failed save (and close notifications)`, async () => {
    Partner._views = {
        form: `
            <form>
                <field name="date" required="true"/>
                <field name="foo" required="true"/>
            </form>
        `,
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                    </t>
                </templates>
            </kanban>
        `,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "kanban"],
                [false, "form"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(`.o_control_panel_main_buttons button.o-kanban-button-new`).click();

    //cannot save because there is a required field
    await contains(`.o_control_panel .o_form_button_save`).click();
    expect(`.o_notification`).toHaveCount(1);

    await contains(`.o_control_panel .o_form_button_cancel`).click();
    expect(`.o_form_view`).toHaveCount(0);
    expect(`.o_kanban_view`).toHaveCount(1);
    expect(`.o_notification`).toHaveCount(0);
});

test(`one2many create record dialog shouldn't have a 'remove' button`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="foo"/>
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="foo"/>
                    </form>
                </field>
            </form>
        `,
        resId: 1,
    });
    await contains(`.o_form_button_create`).click();
    await contains(`.o-kanban-button-new`).click();
    expect(`.modal`).toHaveCount(1);
    expect(`.modal .modal-footer .o_btn_remove`).toHaveCount(0);
});

test(`"bare" buttons in template should not trigger button click`, async () => {
    mockService("action", {
        doActionButton(args) {
            expect.step("doActionButton");
            delete args.onClose;
            expect(args).toEqual({
                buttonContext: {},
                context: {
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                    allowed_company_ids: [1],
                },
                resId: 2,
                resIds: [2],
                resModel: "partner",
                special: "save",
            });
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <button string="Save" class="btn-primary" special="save"/>
                <button class="mybutton">westvleteren</button>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_form_view button.mybutton`).not.toBeEnabled();

    await contains(`.o_form_view .o_content button.btn-primary`).click();
    expect.verifySteps(["doActionButton"]);
});

test(`form view with inline list view with optional fields and local storage mock`, async () => {
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            expect.step(`getItem ${key}`);
            return super.getItem(key);
        },
        setItem(key, value) {
            expect.step(`setItem ${key} to ${value}`);
            return super.setItem(key, value);
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="float_field"/>
                <field name="child_ids">
                    <list>
                        <field name="foo"/>
                        <field name="bar" optional="hide"/>
                    </list>
                </field>
            </form>
        `,
    });

    const localStorageKey = "partner,form,123456789,child_ids,list,bar,foo";
    expect.verifySteps([
        "getItem pwaService.installationState",
        `getItem optional_fields,${localStorageKey}`,
        `getItem debug_open_view,${localStorageKey}`,
    ]);
    expect(`.o_list_table th`).toHaveCount(2);
    expect(`th[data-name="foo"]`).toBeVisible();
    expect(`th[data-name="bar"]`).not.toBeVisible();

    // optional fields
    await contains(`.o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(`.o-dropdown--menu .dropdown-item`).toHaveCount(1);

    // enable optional field
    await contains(`.o-dropdown--menu input[name="bar"]`).click();
    expect.verifySteps([
        `setItem optional_fields,${localStorageKey} to bar`,
        `getItem optional_fields,${localStorageKey}`,
        `getItem debug_open_view,${localStorageKey}`,
    ]);

    expect(`.o_list_table th`).toHaveCount(3);
    expect(`th[data-name="foo"]`).toBeVisible();
    expect(`th[data-name="bar"]`).toBeVisible();
});

test.tags("desktop");
test(`form view with list_view_ref with optional fields and local storage mock`, async () => {
    patchWithCleanup(browser.localStorage, {
        getItem(key) {
            expect.step(`getItem ${key}`);
            return super.getItem(key);
        },
        setItem(key, value) {
            expect.step(`setItem ${key} to ${value}`);
            return super.setItem(key, value);
        },
    });

    Partner._views = {
        "list,nope_not_this_one": `<list><field name="foo"/><field name="bar"/></list>`,
        "list,34": `
                <list>
                    <field name="foo" optional="hide"/>
                    <field name="bar"/>
                </list>
            `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        // we add a widget= as a bit of a hack. Without widget, the views are inlined by the server.
        // the mock server doesn't replicate fully this behavior.
        // Putting a widget prevent the inlining.
        arch: `
            <form>
                <field name="float_field"/>
                <field name="child_ids" widget="one2many" context="{'list_view_ref': '34'}"/>
            </form>
        `,
    });

    const localStorageKey = "partner,form,123456789,child_ids,list,bar,foo";
    expect.verifySteps([
        "getItem pwaService.installationState",
        `getItem optional_fields,${localStorageKey}`,
        `getItem debug_open_view,${localStorageKey}`,
    ]);
    expect(`.o_list_table th`).toHaveCount(2);
    expect(`th[data-name="foo"]`).not.toBeVisible();
    expect(`th[data-name="bar"]`).toBeVisible();

    // optional fields
    await contains(`.o_optional_columns_dropdown .dropdown-toggle`).click();
    expect(`.o-dropdown--menu .dropdown-item`).toHaveCount(1);

    // enable optional field
    await contains(`.o-dropdown--menu input[name="foo"]`).click();
    expect.verifySteps([
        `setItem optional_fields,${localStorageKey} to foo`,
        `getItem optional_fields,${localStorageKey}`,
        `getItem debug_open_view,${localStorageKey}`,
    ]);

    expect(`.o_list_table th`).toHaveCount(3);
    expect(`th[data-name="foo"]`).toBeVisible();
    expect(`th[data-name="bar"]`).toBeVisible();
});

test(`resequence list lines when discardable lines are present`, async () => {
    Partner._onChanges = {
        child_ids(record) {
            expect.step("onchange");
            record.foo = record.child_ids ? record.child_ids.length.toString() : "0";
        },
    };

    Partner._views = {
        list: `
            <list editable="bottom">
                <field name="int_field" widget="handle"/>
                <field name="name" required="1"/>
            </list>
        `,
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="child_ids"/></form>`,
    });
    expect.verifySteps(["onchange"]);
    expect(`[name="foo"] input`).toHaveValue("0");

    // Add one line
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_field_cell [name="name"] input`).edit("first line");
    expect.verifySteps(["onchange"]);
    expect(`[name="foo"] input`).toHaveValue("1");

    await contains(`.o_field_x2many_list_row_add a`).click();
    await animationFrame();
    // Drag and drop second line before first one (with 1 draft and invalid line)
    await contains(`tbody.ui-sortable tr:nth-child(1) .o_handle_cell`).dragAndDrop(
        `tbody.ui-sortable tr:nth-child(2)`
    );
    expect.verifySteps(["onchange"]);
    expect(`[name="foo"] input`).toHaveValue("1");

    // Add a second line
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_selected_row input`).edit("second line");
    expect.verifySteps(["onchange"]);
    expect(`[name="foo"] input`).toHaveValue("2");
});

test(`reload company when creating records of model res.company`, async () => {
    mockService("action", {
        async doAction(actionRequest) {
            if (actionRequest === "reload_context") {
                expect.step("reload company");
            }
        },
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "res.company",
        type: "form",
        arch: `<form><field name="name"/></form>`,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_field_widget[name="name"] input`).edit("Test Company");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save", "reload company"]);
});

test(`reload company when writing on records of model res.company`, async () => {
    mockService("action", {
        async doAction(actionRequest) {
            if (actionRequest === "reload_context") {
                expect.step("reload company");
            }
        },
    });

    ResCompany._records = [{ id: 1, name: "Test Company" }];

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "res.company",
        type: "form",
        arch: `<form><field name="name"/></form>`,
        resId: 1,
    });
    expect.verifySteps(["get_views", "web_read"]);

    await contains(`.o_field_widget[name="name"] input`).edit("Test Company2");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save", "reload company"]);
});

test.tags("desktop")(`company_dependent field in form view, in multi company group`, async () => {
    Partner._fields.foo = fields.Char({ company_dependent: true });
    Partner._fields.product_id = fields.Many2one({
        relation: "product",
        company_dependent: true,
        help: "this is a tooltip",
    });

    patchWithCleanup(session, { display_switch_company_menu: true });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="foo"/>
                    <field name="product_id"/>
                </group>
            </form>
        `,
    });

    await hover(`.o_form_label[for=product_id_0] sup`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--help`).toHaveText(
        "this is a tooltip\n\nValues set here are company-specific."
    );

    await hover(`.o_form_label[for=foo_0] sup`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--help`).toHaveText("Values set here are company-specific.");
});

test.tags("desktop");
test(`company_dependent field in form view, not in multi company group`, async () => {
    Partner._fields.product_id = fields.Many2one({
        relation: "product",
        company_dependent: true,
        help: "this is a tooltip",
    });

    patchWithCleanup(session, { display_switch_company_menu: false });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
                <form>
                    <group>
                        <field name="product_id"/>
                    </group>
                </form>
            `,
    });

    await hover(`.o_form_label sup`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--help`).toHaveText("this is a tooltip");
});

test(`no 'oh snap' error when clicking on a view button`, async () => {
    expect.errors(1);

    onRpc("web_save", () => {
        throw makeServerError({ message: "Some business message" });
    });
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <button name="do_it" type="object" string="Do it"/>
                <field name="name"/>
            </form>
        `,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`button[name=do_it]`).click();
    await animationFrame();
    expect.verifyErrors(["Some business message"]);
    expect.verifySteps(["web_save"]);
    expect(`.modal`).toHaveCount(1);
    expect(`.o_form_error_dialog`).toHaveCount(0);
});

test(`no 'oh snap' error in form view in dialog`, async () => {
    expect.errors(1);

    Partner._views = {
        form: `
            <form>
                <field name="foo"/>
                <footer>
                    <button type="object" name="some_method" class="myButton"/>
                </footer>
            </form>
        `,
    };

    onRpc("web_save", () => {
        expect.step("save");
        throw makeServerError({ message: "Some business message" });
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.act_window",
        target: "new",
        res_model: "partner",
        view_mode: "form",
        views: [[false, "form"]],
    });

    await contains(`.o_field_widget[name='foo'] input`).edit("test");
    await contains(`.modal  footer .myButton`).click();
    expect.verifyErrors(["Some business message"]);
    expect.verifySteps(["save"]);
    await animationFrame();
    expect(`.modal`).toHaveCount(2);
    expect(`.o_error_dialog`).toHaveCount(1);
});

test(`field "length" with value 0: can apply onchange`, async () => {
    Partner._fields.length = fields.Float();
    Partner._fields.foo = fields.Char({ default: "foo default" });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/><field name="length"/></form>`,
    });
    expect(`.o_field_widget[name=foo] input`).toHaveValue("foo default");
    expect(`.o_field_widget[name=length] input`).toHaveValue("0.00");
});

test(`field "length" with value 0: readonly fields are not sent when saving`, async () => {
    Partner._fields.length = fields.Float();
    Partner._fields.foo = fields.Char({ default: "foo default" });

    // define an onchange on name to check that the value of readonly
    // fields is correctly sent for onchanges
    Partner._onChanges = {
        name() {},
        child_ids() {},
    };

    onRpc("web_save", ({ args }) => {
        expect.step("save");
        expect(args[1]).toEqual({
            child_ids: [[0, args[1].child_ids[0][1], { length: 0, name: "readonly" }]],
        });
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <field name="length"/>
                        <field name="name"/>
                        <field name="foo" readonly="name =='readonly'"/>
                    </form>
                </field>
            </form>
        `,
    });

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.modal .o_field_widget[name=foo] input`).toHaveCount(1);

    await contains(`.modal .o_field_widget[name=foo] input`).edit("foo value");
    await contains(`.modal .o_field_widget[name=name] input`).edit("readonly");
    expect(`.modal .o_field_widget[name=foo] span`).toHaveCount(1);

    await contains(`.modal .o_form_button_save`).click();
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["save"]);
});

test(`fieldDependencies support for fields`, async () => {
    Partner._records = [{ id: 1, int_field: 2 }];

    fieldsRegistry.add("custom_field", {
        component: class CustomField extends Component {
            static props = ["*"];
            static template = xml`<span t-esc="props.record.data.int_field"/>`;
        },
        fieldDependencies: [{ name: "int_field", type: "integer" }],
    });

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
        arch: `<form><field name="foo" widget="custom_field"/></form>`,
    });
    expect(`[name=foo] span`).toHaveText("2");
});

test(`fieldDependencies support for fields: dependence on a relational field`, async () => {
    Partner._records[0].product_id = 37;

    registry.category("fields").add("custom_field", {
        component: class CustomField extends Component {
            static props = ["*"];
            static template = xml`<span t-esc="props.record.data.product_id[1]"/>`;
        },
        fieldDependencies: [{ name: "product_id", type: "many2one", relation: "product" }],
    });

    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
        arch: `<form><field name="foo" widget="custom_field"/></form>`,
    });
    expect.verifySteps(["get_views", "web_read"]);
    expect(`[name=foo] span`).toHaveText("xphone");
});

test.tags("desktop")(`Action Button clicked with failing action on desktop`, async () => {
    expect.errors(1);

    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            throw new Error("test");
        }
    }
    registry.category("actions").add("someaction", MyComponent);

    Partner._views = {
        form: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box test">
                        <button class="oe_stat_button" type="action" name="someaction">
                            Test
                        </button>
                    </div>
                </sheet>
            </form>
        `,
        search: `<search/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_id: 1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "partner",
        view_mode: "form",
        views: [[false, "form"]],
    });
    expect(`.o_form_view .test`).toHaveCount(1);

    await contains(`button.oe_stat_button`).click();
    expect(`.o_form_view .test`).toHaveCount(1);
    expect.verifyErrors(["test"]);
});

test.tags("mobile")(`Action Button clicked with failing action on mobile`, async () => {
    expect.errors(1);

    class MyComponent extends Component {
        static props = ["*"];
        static template = xml`<div/>`;
        setup() {
            throw new Error("test");
        }
    }
    registry.category("actions").add("someaction", MyComponent);

    Partner._views = {
        form: `
            <form>
                <sheet>
                    <div name="button_box" class="oe_button_box test">
                        <button class="oe_stat_button" type="action" name="someaction">
                            Test
                        </button>
                    </div>
                </sheet>
            </form>
        `,
        search: `<search/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_id: 1,
        type: "ir.actions.act_window",
        target: "current",
        res_model: "partner",
        view_mode: "form",
        views: [[false, "form"]],
    });
    expect(`.o_form_view .test`).toHaveCount(1);

    await contains(".o-form-buttonbox .o_button_more").click();
    await contains(`button.oe_stat_button`).click();
    expect(`.o_form_view .test`).toHaveCount(1);
    expect.verifyErrors(["test"]);
});

test(`form view with edit='0' but create='1', existing record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form edit="0"><field name="foo"/></form>`,
        resId: 1,
    });
    expect(`.o_form_readonly`).toHaveCount(1);

    await contains(`.o_form_button_create`).click();
    expect(`.o_form_editable`).toHaveCount(1);
});

test(`form view with edit='0' but create='1', new record`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form edit="0"><field name="foo"/></form>`,
    });
    expect(`.o_form_editable`).toHaveCount(1);
});

test(`save a form view with an invisible required field`, async () => {
    Partner._fields.text = fields.Text({ required: 1 });

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ int_field: 0, text: false });
    });
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="text" invisible="1"/>
                    <field name="int_field"/>
                </sheet>
            </form>
        `,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});

test(`save a form view with a duplicated invisible required field`, async () => {
    Partner._fields.text = fields.Char({ required: 1 });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <field name="text"/>
                    <field name="text" invisible="1"/>
                </group>
            </form>
        `,
    });
    await contains(`.o_form_button_save`).click();
    expect(`.o_form_label.o_field_invalid`).toHaveCount(1);
    expect(`.o_field_char.o_field_invalid`).toHaveCount(1);
});

test(`save a form view with an invisible required field in a x2many`, async () => {
    Partner._fields.text = fields.Char({ required: 1 });

    onRpc("web_save", ({ args }) => {
        expect(args[1].child_ids[0][2]).toEqual({ int_field: 1, text: false });
    });
    onRpc(({ method }) => expect.step(method));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <sheet>
                    <field name="child_ids">
                        <list editable="top">
                            <field name="text" invisible="1"/>
                            <field name="int_field"/>
                        </list>
                    </field>
                </sheet>
            </form>
        `,
    });
    expect.verifySteps(["get_views", "onchange"]);

    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`[name='int_field'] input`).edit("1", { confirm: "blur" });
    expect(`[name='int_field'] input`).toHaveCount(0);
    expect.verifySteps(["onchange"]);

    await contains(`.o_form_button_save`).click();
    expect(`.o_list_renderer .o_data_row`).toHaveCount(1);
    expect(`.o_list_renderer .o_data_row [name='int_field']`).toHaveText("1");
    expect.verifySteps(["web_save"]);
});

test(`help on field as precedence over field's declaration -- form`, async () => {
    Partner._fields.foo = fields.Char({ help: "pythonhelp" });
    serverState.debug = true;

    await mountView({
        resModel: "partner",
        type: "form",
        resId: 1,
        arch: `<form><sheet><field name="foo" help="xmlHelp"/></sheet></form>`,
    });
    const element = queryFirst`.o_field_widget`;
    const tooltipInfo = JSON.parse(element.dataset.tooltipInfo);
    expect(tooltipInfo.field.help).toBe("xmlHelp");
});

test.tags("desktop")(`help on field is shown without debug mode -- form`, async () => {
    Partner._fields.bar = fields.Boolean({ help: "bar tooltip" });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <group>
                    <label for="foo"/>
                    <div><field name="foo" help="foo xml tooltip"/></div>
                    <label for="bar"/>
                    <div><field name="bar" help="bar xml tooltip"/></div>
                </group>
            </form>
        `,
    });

    await hover(`.o_form_label[for=foo_0] sup`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--help`).toHaveText(/foo xml tooltip/);

    await hover(`.o_form_label[for=bar_0] sup`);
    await runAllTimers();
    expect(`.o-tooltip .o-tooltip--help`).toHaveText(/bar xml tooltip/);
});

test(`onSave/onDiscard props`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
        onSave: () => expect.step("save"),
        onDiscard: () => expect.step("discard"),
    });

    await contains(`.o_field_widget input`).edit("to save");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["save"]);

    await contains(`.o_field_widget input`).edit("to cancel");
    await contains(`.o_form_button_cancel`).click();
    expect.verifySteps(["discard"]);
});

test.tags("desktop")(`form view does not deactivate sample data on other views`, async () => {
    ResUsers._records = [];
    Partner._records = [];
    Partner._views = {
        list: `<list sample="1"><field name="name"/></list>`,
        form: `<form><field name="name"/></form>`,
        search: `<search/>`,
    };

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });
    expect(`.o_list_view .o_content.o_view_sample_data`).toHaveCount(1);

    await contains(`.o_control_panel_main_buttons button.o_list_button_add`).click();
    expect(`.o_form_view`).toHaveCount(1);

    await contains(`.o_form_view .breadcrumb-item a`).click();
    expect(`.o_list_view .o_content.o_view_sample_data`).toHaveCount(1);
});

test.tags("desktop")(`empty x2manys when coming form a list with sample data`, async () => {
    ResUsers._records = [];
    Partner._records = [];
    Partner._views = {
        list: `<list sample="1"><field name="name"/></list>`,
        form: `
            <form>
                <field name="child_ids">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
            </form>
        `,
        search: `<search/>`,
    };
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        name: "Partner",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [false, "form"],
        ],
    });
    expect(`.o_list_view .o_content.o_view_sample_data`).toHaveCount(1);

    await contains(`.o_control_panel_main_buttons button.o_list_button_add`).click();
    expect(`.o_form_view .o_field_x2many .o_kanban_renderer`).toHaveCount(1);
    expect(`.o_view_nocontent`).toHaveCount(0);
});

test(`status indicator: saved state`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect(`.o_form_status_indicator`).toHaveCount(1);
    expect(`.o_form_status_indicator_buttons`).toHaveCount(1);
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);
    expect(`.o_form_status_indicator_buttons button`).toHaveCount(2);
});

test(`status indicator: dirty state`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);

    await contains(`.o_field_widget input`).edit("dirty");
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(0);
});

test(`status indicator: field dirty state`, async () => {
    // this test check that the indicator don't need the onchange to be displayed
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);

    await contains(`.o_field_widget input`).edit("dirty", { confirm: false });
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(0);
});

test(`status indicator: field dirty state (date)`, async () => {
    // this test check that the indicator don't need the onchange to be displayed
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="date"/></form>`,
        resId: 1,
    });
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);

    await contains(`.o_field_widget input`).edit("03/26/2019", { confirm: false });
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(0);
});

test(`status indicator: field dirty state (datetime)`, async () => {
    // this test check that the indicator don't need the onchange to be displayed
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="datetime"/></form>`,
        resId: 1,
    });
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);

    await contains(`.o_field_widget input`).edit("12/12/2012 11:55:05", { confirm: false });
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(0);
});

test(`status indicator: save dirty state`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect(`.o_field_widget input`).toHaveValue("yop");

    await contains(`.o_field_widget input`).edit("dirty");
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(0);

    await contains(`.o_form_button_save`).click();
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);
    expect(`.o_field_widget input`).toHaveValue("dirty");
});

test(`status indicator: discard dirty state`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo"/></form>`,
        resId: 1,
    });
    expect(`.o_field_widget input`).toHaveValue("yop");

    await contains(`.o_field_widget input`).edit("dirty");
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(0);

    await contains(`.o_form_button_cancel`).click();
    expect(`.o_form_status_indicator_buttons.invisible`).toHaveCount(1);
    expect(`.o_field_widget input`).toHaveValue("yop");
});

test(`status indicator: invalid state`, async () => {
    onRpc("web_save", () => {
        expect.step("save"); // not called
        throw makeServerError();
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="foo" required="1"/></form>`,
        resId: 1,
    });
    expect(`.o_form_status_indicator`).toHaveText("");

    await contains(`.o_field_widget input`).edit("");
    expect(`.o_form_status_indicator`).toHaveText("");

    await contains(`.o_form_button_save`).click();
    expect.verifySteps([]);
    expect(`.o_form_status_indicator .text-danger`).toHaveAttribute(
        "data-tooltip",
        "Unable to save. Correct the issue or discard all changes"
    );
});

test(`execute an action before and after each valid save in a form view`, async () => {
    const formView = registry.category("views").get("form");
    class CustomFormController extends formView.Controller {
        async onRecordSaved(record) {
            expect.step(`onRecordSaved ${record.resId}`);
        }

        async onWillSaveRecord(record) {
            expect.step(`onWillSaveRecord ${record.resId}`);
        }
    }
    registry.category("views").add("custom_form", {
        ...formView,
        Controller: CustomFormController,
    });

    onRpc("web_save", ({ args }) => expect.step(`write ${args[0]}`));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form js_class="custom_form"><field name="foo" required="1"/></form>`,
        resId: 1,
    });

    await contains(`[name='foo'] input`).edit("");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps([]);

    await contains(`[name='foo'] input`).edit("YOLO");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["onWillSaveRecord 1", "write 1", "onRecordSaved 1"]);
});

test(`don't exec a valid save with onWillSaveRecord in a form view`, async () => {
    const formView = registry.category("views").get("form");
    class CustomFormController extends formView.Controller {
        async onRecordSaved() {
            throw new Error("should not execute onRecordSaved");
        }

        async onWillSaveRecord(record) {
            expect.step(`onWillSaveRecord ${record.resId}`);
            return false;
        }
    }
    registry.category("views").add("custom_form", {
        ...formView,
        Controller: CustomFormController,
    });

    onRpc("web_save", () => expect.step(`web_save`));
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form js_class="custom_form"><field name="foo" required="1"/></form>`,
        resId: 1,
    });

    await contains(`[name='foo'] input`).edit("");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps([]);

    await contains(`[name='foo'] input`).edit("YOLO");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["onWillSaveRecord 1"]);
});

test(`Can't use FormRenderer implementation details in arch`, async () => {
    // using t-esc in form view archs isn't accepted, so it displays a warning
    // in the console
    patchWithCleanup(console, {
        warn: () => expect.step("warn"),
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <div>
                    <t t-esc="__owl__"/>
                    <t t-esc="props"/>
                    <t t-esc="env"/>
                    <t t-esc="render"/>
                </div>
            </form>
        `,
    });
    expect(queryFirst`.o_form_nosheet`).toHaveInnerHTML("<div></div>");
    expect.verifySteps(["warn", "warn", "warn", "warn"]);
});

test(`reload form view with an empty notebook`, async () => {
    Partner._views = {
        form: `
            <form>
                <sheet>
                    <notebook>
                    </notebook>
                </sheet>
            </form>
        `,
        list: `<list><field name="foo"/></list>`,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_back_button`).click();
    await contains(`.o_data_row .o_data_cell`).click();
    expect(`.o_form_view`).toHaveCount(1);
});

test(`setting : boolean field`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <setting help="this is bar" documentation="/applications/technical/web/settings/this_is_a_test.html">
                    <field name="bar"/>
                    <button name="buttonName" icon="oi-arrow-right" type="action" string="Manage Users" class="btn-link"/>
                </setting>
            </form>
        `,
    });
    expect(`.o_setting_left_pane .form-check-input`).toHaveCount(1);
    expect(`.o_form_label`).toHaveText("Bar");
    expect(`.o_doc_link`).toHaveCount(1);
    expect(`.o_doc_link`).toHaveAttribute(
        "href",
        "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_a_test.html"
    );
    expect(`.btn-link[name='buttonName']`).toHaveCount(1);
});

test(`setting : char field`, async () => {
    patchWithCleanup(session, {
        display_switch_company_menu: true,
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <setting help="this is foo" company_dependent="1">
                    <field name="foo"/>
                </setting>
            </form>
        `,
    });
    expect(`.o_setting_left_pane > *`).toHaveCount(0);
    expect(`.o_form_label`).toHaveText("Foo");
    expect(`.text-muted`).toHaveText("this is foo");
    expect(`.fa-building-o`).toHaveCount(1);
    expect(`.o_field_char input`).toHaveCount(1);
});

test(`setting : without field`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <setting string="Personalize setting" help="this is full personalize setting">
                    <div>This is a different setting</div>
                </setting>
            </form>
        `,
    });
    expect(`.o_setting_left_pane > *`).toHaveCount(0);
    expect(`.o_field_char input`).toHaveCount(0);
    expect(`.o_form_label`).toHaveText("Personalize setting");
    expect(`.text-muted`).toHaveText("this is full personalize setting");
});

test(`action button in x2many should display a notification if the record is virtual`, async () => {
    mockService("notification", {
        add(message, { type }) {
            expect.step(`${type}:${message}`);
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="bottom">
                        <field name="foo"/>
                        <button class="oe_stat_button" name="test_action" type="object" icon="fa-check">MyButton</button>
                    </list>
                </field>
            </form>
        `,
    });

    await contains(`.o_field_one2many .o_field_x2many_list_row_add a`).click();
    await contains(`button.oe_stat_button[name='test_action']`).click();
    expect.verifySteps([`danger:Please save your changes first`]);
});

test(`open form view action in x2many should display a notification if the record is virtual`, async () => {
    mockService("notification", {
        add(message, { type }) {
            expect.step(`${type}:${message}`);
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="bottom" open_form_view="1">
                        <field name="foo"/>
                    </list>
                </field>
            </form>
        `,
    });

    await contains(`.o_field_one2many .o_field_x2many_list_row_add a`).click();
    await contains(`.o_list_record_open_form_view`).click();
    expect.verifySteps([`danger:Please save your changes first`]);
});

test(`prevent recreating a deleted record`, async () => {
    Partner._records = [{ id: 1, name: "first record" }];
    Partner._views = {
        list: `<list><field name="name"/></list>`,
        form: `
            <form>
                <group>
                    <field name="name"/>
                </group>
            </form>
        `,
        search: `<search/>`,
    };

    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        },
    ]);

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);
    expect(`.o_data_row`).toHaveCount(1);
    expect(`.o_data_row`).toHaveText("first record");

    await contains(`.o_data_row .o_data_cell`).click();
    await contains(`.o_field_char .o_input`).edit("now dirty");
    expect(`.o_form_status_indicator_buttons`).toBeVisible();

    await contains(`.o_cp_action_menus .dropdown-toggle`).click();
    await contains(`.o-dropdown--menu .dropdown-item:contains(Delete)`).click();
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal-footer button.btn-primary`).click();
    expect(`.o_list_view`).toHaveCount(1);
    expect(`.o_data_row`).toHaveCount(0);
});

test.tags("desktop");
test(`coming to an action with an error from a form view with a dirty x2m`, async () => {
    expect.errors(1);

    class TestClientAction extends Component {
        static props = ["*"];
        static template = xml`<div></div>`;
        setup() {
            throw new Error("Something went wrong");
        }
    }
    registry.category("actions").add("TestClientAction", TestClientAction);

    class MyWidget extends Component {
        static props = ["*"];
        static template = xml`
            <div class="test_widget">
                <button t-on-click="onClick">MyButton</button>
            </div>
        `;
        setup() {
            this.actionService = useService("action");
        }
        onClick() {
            this.actionService.doAction({
                tag: "TestClientAction",
                target: "main",
                type: "ir.actions.client",
            });
        }
    }
    widgetsRegistry.add("test_widget", { component: MyWidget });

    defineActions([
        {
            id: 1,
            name: "test",
            res_model: "partner",
            res_id: 1,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
    ]);

    Partner._views = {
        list: `<list editable="bottom"><field name="foo"/></list>`,
        form: `
                <form>
                    <widget name="test_widget"/>
                    <field name="foo"/>
                    <field name="child_ids"/>
                </form>
            `,
        search: `<search/>`,
    };

    onRpc(({ method, args }) => {
        if ((method === "web_read" || method === "web_save") && args[0][0] === 1) {
            expect.step(method);
        }
    });
    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(`.o_field_one2many[name="child_ids"] .o_field_x2many_list_row_add a`).click();
    await contains(`[name="child_ids"] input`).edit("new");
    expect.verifySteps(["web_read"]);

    await contains(`.test_widget button`).click();
    await animationFrame();
    expect.verifyErrors(["Something went wrong"]);

    // Close ErrorDialog
    await contains(`.o_dialog .btn-close`).click();
    expect(`[name="child_ids"] .o_data_row`).toHaveCount(1);
    expect.verifySteps(["web_save", "web_read"]);

    await contains(`[name=foo] input`).edit("new value");
    await contains(`.o_form_button_save`).click();
    expect(`[name="child_ids"] .o_data_row`).toHaveCount(1);
    expect.verifySteps(["web_save"]);
});

test(`coming to an action with an error from a form view with a record in creation`, async () => {
    expect.errors(1);

    class TestClientAction extends Component {
        static props = ["*"];
        static template = xml`<div></div>`;
        setup() {
            throw new Error("Something went wrong");
        }
    }
    registry.category("actions").add("TestClientAction", TestClientAction);

    class MyWidget extends Component {
        static props = ["*"];
        static template = xml`
                <div class="test_widget">
                    <button t-on-click="onClick">MyButton</button>
                </div>`;
        setup() {
            this.actionService = useService("action");
        }
        onClick() {
            this.actionService.doAction({
                tag: "TestClientAction",
                target: "main",
                type: "ir.actions.client",
            });
        }
    }
    widgetsRegistry.add("test_widget", { component: MyWidget });

    defineActions([
        {
            id: 1,
            name: "test",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        },
    ]);

    Partner._views = {
        form: `
            <form>
                <widget name="test_widget"/>
                <field name="foo"/>
            </form>
        `,
        search: `<search/>`,
    };

    onRpc("web_read", ({ args }) => {
        expect.step("web_read");
        expect(args[0]).toEqual([6]);
    });
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({ foo: "new value" });
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction(1);

    await contains(`[name=foo] input`).edit("new value");
    expect(`[name=foo] input`).toHaveValue("new value");

    await contains(`.test_widget button`).click();
    await animationFrame();
    expect.verifyErrors(["Something went wrong"]);

    // Close ErrorDialog
    await contains(`.o_dialog .btn-primary`).click();
    expect(`[name=foo] input`).toHaveValue("new value");
    expect.verifySteps(["web_save", "web_read"]);
});

test(`only re-render necessary fields after change`, async () => {
    function logLifeCycle(component) {
        patchWithCleanup(component.prototype, {
            setup() {
                super.setup();
                const prefix = `${this.constructor.name} ${this.props.name}`;
                onMounted(() => expect.step(`[${prefix}] onMounted`));
                onPatched(() => expect.step(`[${prefix}] onPatched`));
                onWillStart(() => expect.step(`[${prefix}] onWillStart`));
                onWillUpdateProps(() => expect.step(`[${prefix}] onWillUpdateProps`));
            },
        });
    }
    logLifeCycle(Field);
    logLifeCycle(CharField);
    logLifeCycle(IntegerField);
    logLifeCycle(DateTimeField);

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="date"/>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps([
        "[Field foo] onWillStart",
        "[Field int_field] onWillStart",
        "[Field date] onWillStart",
        "[CharField foo] onWillStart",
        "[IntegerField int_field] onWillStart",
        "[DateTimeField date] onWillStart",
        "[DateTimeField date] onMounted",
        "[IntegerField int_field] onMounted",
        "[CharField foo] onMounted",
        "[Field date] onMounted",
        "[Field int_field] onMounted",
        "[Field foo] onMounted",
    ]);

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    expect.verifySteps(["[Field foo] onPatched", "[CharField foo] onPatched"]);

    await contains(`.o_field_widget[name=int_field] input`).edit("5846");
    expect.verifySteps(["[Field int_field] onPatched", "[IntegerField int_field] onPatched"]);
});

test(`only re-render necessary fields after change (with onchange)`, async () => {
    function logLifeCycle(component) {
        patchWithCleanup(component.prototype, {
            setup() {
                super.setup();
                const prefix = `${this.constructor.name} ${this.props.name}`;
                onMounted(() => expect.step(`[${prefix}] onMounted`));
                onPatched(() => expect.step(`[${prefix}] onPatched`));
                onWillStart(() => expect.step(`[${prefix}] onWillStart`));
                onWillUpdateProps(() => expect.step(`[${prefix}] onWillUpdateProps`));
            },
        });
    }
    logLifeCycle(Field);
    logLifeCycle(CharField);
    logLifeCycle(IntegerField);
    logLifeCycle(DateTimeField);

    Partner._onChanges = {
        foo(record) {
            record.int_field = 23;
        },
    };

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="foo"/>
                <field name="int_field"/>
                <field name="date"/>
            </form>
        `,
        resId: 2,
    });
    expect.verifySteps([
        "[Field foo] onWillStart",
        "[Field int_field] onWillStart",
        "[Field date] onWillStart",
        "[CharField foo] onWillStart",
        "[IntegerField int_field] onWillStart",
        "[DateTimeField date] onWillStart",
        "[DateTimeField date] onMounted",
        "[IntegerField int_field] onMounted",
        "[CharField foo] onMounted",
        "[Field date] onMounted",
        "[Field int_field] onMounted",
        "[Field foo] onMounted",
    ]);

    await contains(`.o_field_widget[name=foo] input`).edit("new value");
    expect.verifySteps([
        "[Field foo] onPatched",
        "[CharField foo] onPatched",
        "[Field int_field] onPatched",
        "[IntegerField int_field] onPatched",
    ]);

    await contains(`.o_field_widget[name=int_field] input`).edit("5846");
    expect.verifySteps(["[Field int_field] onPatched", "[IntegerField int_field] onPatched"]);
});

test(`widget update several fields including an x2m`, async () => {
    Partner._onChanges = {
        name() {},
        child_ids() {},
    };
    class TestWidget extends Component {
        static props = ["*"];
        static template = xml`<div><button t-on-click="onClick">Click</button></div>`;

        onClick() {
            this.props.record.update({
                name: "New Name",
                child_ids: [[0, false, { name: "yop" }]],
            });
        }
    }

    widgetsRegistry.add("test", {
        component: TestWidget,
        fieldDependencies: [
            { name: "name", type: "char" },
            { name: "child_ids", type: "one2many", relation: "partner" },
        ],
    });

    onRpc("onchange", ({ args }) => {
        expect.step("onchange");
        expect(args[1].name).toBe("New Name");
        expect(args[1].child_ids).toHaveLength(1);
        expect(args[1].child_ids[0][2]).toEqual({ name: "yop" });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <widget name="test"/>
                <field name="name"/>
                <field name="child_ids">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(`[name=name] input`).toHaveValue("second record");
    expect(queryAllTexts`.o_data_row`).toEqual([]);

    await contains(`.o_widget_test button`).click();
    expect(`[name=name] input`).toHaveValue("New Name");
    expect(queryAllTexts`.o_data_row`).toEqual(["yop"]);
    expect.verifySteps(["onchange"]);
});

test(`commitChanges with a field input removed during an update`, async () => {
    Partner._records[1].child_ids = [1, 5];
    Partner._onChanges = {
        foo() {},
    };

    const onchangeDeferred = new Deferred();
    onRpc("onchange", () => onchangeDeferred);
    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ child_ids: [[1, 1, { foo: "new foo" }]] });
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <list editable="bottom">
                        <field name="foo"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });

    await contains(`.o_data_cell[name="foo"]`).click();
    await contains(`.o_data_cell[name="foo"] input`).edit("new foo", { confirm: "tab" });
    onchangeDeferred.resolve();
    await contains(`.o_form_button_save`).click();
});

test(`multiple views for m2m field after list item edit in form`, async () => {
    Partner._records[0].type_ids = [1, 2];

    PartnerType._fields.m2m = fields.Many2many({ relation: "extra" });
    PartnerType._records = [
        { id: 1, name: "ma", m2m: [1] },
        { id: 2, name: "cr", m2m: [2] },
    ];

    class Extra extends models.Model {
        name = fields.Char();

        _records = [
            { id: 1, name: "ma" },
            { id: 2, name: "cr" },
        ];
    }
    defineModels([Extra]);

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="type_ids">
                    <list>
                        <field name="display_name"/>
                        <field name="m2m" widget="many2many_tags"/>
                    </list>
                    <form>
                        <field name="name"/>
                        <field name="m2m">
                            <list>
                                <field name="name"/>
                            </list>
                        </field>
                    </form>
                </field>
            </form>
        `,
        resId: 1,
    });

    await contains(`.o_data_cell:eq(0)`).click();
    expect(`.modal`).toHaveCount(1);

    await contains(`.modal-body [name='name'] input`).edit("updated");
    await contains(`.modal-footer .o_form_button_save`).click();
    expect(`.modal`).toHaveCount(0);
    expect(`.o_data_cell:eq(0)`).toHaveText("updated");
});

test(`custom x2many with relatedFields and list view inline`, async () => {
    fieldsRegistry.add("my_widget", {
        ...x2ManyField,
        component: class MyField extends X2ManyField {},
        relatedFields: [
            { name: "parent_id", type: "many2one", relation: "partner" },
            { name: "int_field", type: "integer" },
        ],
    });

    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.specification.child_ids.fields).toEqual({
            parent_id: { fields: { display_name: {} } },
            foo: {},
            int_field: {},
        });
    });
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[1].child_ids[0][2]).toEqual({
            foo: "new record",
            int_field: 0,
        });
    });
    onRpc("web_save", ({ kwargs }) => {
        expect.step("web_save");
        expect(kwargs.specification.child_ids.fields).toEqual({
            parent_id: { fields: { display_name: {} } },
            foo: {},
            int_field: {},
        });
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids" widget="my_widget">
                    <list editable="bottom" >
                        <field name="foo"/>
                        <field name="int_field" />
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });

    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_data_row [name='foo'] input`).edit("new record");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_read", "web_save"]);
});

test(`custom x2many with a m2o in relatedFields and column_invisible`, async () => {
    fieldsRegistry.add("my_widget", {
        ...x2ManyField,
        component: class MyField extends X2ManyField {},
        relatedFields: [{ name: "parent_id", type: "many2one", relation: "partner" }],
    });

    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.specification.child_ids.fields).toEqual({
            parent_id: { fields: { display_name: {} } },
            foo: {},
        });
    });
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[1].child_ids[0][2]).toEqual({
            foo: "new record",
            int_field: 0,
        });
    });
    onRpc("web_save", ({ kwargs }) => {
        expect.step("web_save");
        expect(kwargs.specification.child_ids.fields).toEqual({
            parent_id: { fields: { display_name: {} } },
            foo: {},
        });
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids" widget="my_widget">
                    <list editable="bottom" >
                        <field name="foo"/>
                        <field name="parent_id" column_invisible="True"/>
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });

    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_data_row [name='foo'] input`).edit("new record");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_read", "web_save"]);
});

test.tags("desktop")(`custom x2many with relatedFields and list view not inline`, async () => {
    fieldsRegistry.add("my_widget", {
        ...x2ManyField,
        component: class MyField extends X2ManyField {},
        relatedFields: [
            { name: "parent_id", type: "many2one", relation: "partner" },
            { name: "int_field", type: "integer" },
        ],
    });

    Partner._views = {
        list: `
            <list editable="bottom">
                <field name="foo"/>
                <field name="int_field"/>
            </list>
        `,
    };

    onRpc("web_read", ({ kwargs }) => {
        expect.step("web_read");
        expect(kwargs.specification.child_ids.fields).toEqual({
            parent_id: { fields: { display_name: {} } },
            foo: {},
            int_field: {},
        });
    });
    onRpc("write", ({ args }) => {
        expect.step("write");
        expect(args[1].child_ids[0][2]).toEqual({
            foo: "new record",
            int_field: 0,
        });
    });
    onRpc("web_save", ({ kwargs }) => {
        expect.step("web_save");
        expect(kwargs.specification.child_ids.fields).toEqual({
            parent_id: { fields: { display_name: {} } },
            foo: {},
            int_field: {},
        });
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="child_ids" widget="my_widget"/></form>`,
        resId: 2,
    });

    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_data_row [name='foo'] input`).edit("new record");
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_read", "web_save"]);
});

test(`existing record with falsy display_name`, async () => {
    Partner._records[0].name = "";
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="int_field"/></form>`,
        resId: 1,
    });
    expect(`.o_breadcrumb`).toHaveText("Unnamed");
});

test(`field with special data`, async () => {
    class MyWidget extends Component {
        static props = ["*"];
        static template = xml`<div>MyWidget</div>`;
        setup() {
            this.specialData = useSpecialData((orm, props) => {
                const { record } = props;
                return orm.call("my.model", "get_special_data", [record.data.int_field]);
            });
        }
    }
    widgetsRegistry.add("my_widget", { component: MyWidget });

    onRpc("get_special_data", ({ args }) => {
        expect.step(`get_special_data ${args[0]}`);
        return {};
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="int_field" />
                <widget name="my_widget" />
            </form>
        `,
        resId: 2,
    });

    await contains(`[name='int_field'] input`).edit("42");
    expect.verifySteps(["get_special_data 9", "get_special_data 42"]);
});

test(`x2many field in form dialog view is correctly saved when using a view button`, async () => {
    defineActions([
        {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            res_id: 6,
        },
    ]);

    Partner._views = {
        form: `<form><field name="name"/></form>`,
        search: `<search/>`,
    };
    ResUsers._views = {
        form: `
            <form>
                <field name="partner_ids">
                    <list>
                        <field name="name"/>
                    </list>
                    <form>
                        <header>
                            <button type="action" name="1" string="test"/>
                        </header>
                        <field name="name"/>
                    </form>
                </field>
            </form>
        `,
        search: `<search/>`,
    };

    onRpc("partner", "web_save", ({ args }) => {
        expect.step("web_save_partner");
        expect(args[1]).toEqual({ name: "new value" });
    });
    onRpc("res.users", "web_save", ({ args }) => {
        expect.step("web_save_user");
        expect(args[1]).toEqual({ partner_ids: [[4, 6]] });
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_id: 19,
        type: "ir.actions.act_window",
        res_model: "res.users",
        view_mode: "form",
        views: [[false, "form"]],
    });

    expect(`.o_data_cell`).toHaveCount(0);
    await contains(`.o_field_x2many_list_row_add a`).click();
    await contains(`.o_field_widget[name=name] input`).edit("new value");
    await contains(`.modal-dialog .o_form_button_save`).click();
    await contains(`.o_data_cell`).click();
    await contains(`[name='1']`).click();
    expect.verifySteps(["web_save_partner", "web_save_user"]);
    expect(`.o_field_widget[name=name] input`).toHaveValue("new value");
});

test(`nested form view doesn't parasite the main one`, async () => {
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
            <form>
                <field name="child_ids">
                    <form>
                        <div name="button_box" invisible="crash == True">
                            <button name="somename" type="object" />
                        </div>
                        <field name="child_ids">
                            <form>
                                <footer>
                                    <button name="someothername" type="object" />
                                </footer>
                            </form>
                            <list><field name="display_name" /></list>
                        </field>
                        <footer>
                            <button name="somename" type="object" />
                        </footer>
                    </form>
                    <list>
                        <field name="display_name" />
                    </list>
                </field>
            </form>
        `,
        resId: 2,
    });
    expect(`.o_form_view`).toHaveCount(1);
    expect(`.o-form-buttonbox`).toHaveCount(0);

    await contains(`.o_field_x2many_list_row_add a`).click();
    expect(`.modal .modal-footer button[name='somename']`).toHaveCount(1);
    expect(`.modal .modal-footer button[name='someothername']`).toHaveCount(0);

    await contains(`.modal .o_field_x2many_list_row_add a`).click();
    expect(`.modal:not(.o_inactive_modal) .modal-footer button[name='someothername']`).toHaveCount(
        1
    );
});

test(`an empty json object does not pass the required check`, async () => {
    Partner._fields.json_field = fields.Json({ string: "json_field" });

    class JsonField extends Component {
        static props = ["*"];
        static supportedTypes = ["json"];
        static template = xml`<span><input t-on-change="onChange"/></span>`;

        onChange(ev) {
            this.props.record.update({ [this.props.name]: JSON.parse(ev.target.value) });
        }
    }
    fieldsRegistry.add("json", { component: JsonField });

    mockService("notification", {
        add(message, params) {
            expect.step("notification");
            expect(message.toString()).toBe("<ul><li>json_field</li></ul>");
            expect(params).toEqual({ title: "Invalid fields: ", type: "danger" });
        },
    });

    await mountView({
        resModel: "partner",
        type: "form",
        arch: `<form><field name="json_field" widget="json" required="1"/></form>`,
    });

    await contains(`.o_field_widget[name=json_field] input`).edit("{}");
    await contains(`.o_form_button_save`).click();
    expect(`.o_field_widget[name=json_field]`).toHaveClass("o_field_invalid");
    expect.verifySteps(["notification"]);
});

test("onchange returns values w.r.t. extended record specs, for not extended one", async () => {
    Product._fields.partner_type_ids = fields.One2many({
        string: "Partner type",
        relation: "partner",
    });
    Product._views = {
        form: `
            <form>
                <field name="name"/>
                <field name="partner_type_ids">
                    <list>
                        <field name="name"/>
                    </list>
                </field>
            </form>
        `,
    };
    Partner._records[1].product_ids = [37, 41];
    Partner._onChanges = {
        bar(record) {
            record.product_ids = [
                [
                    1,
                    37,
                    {
                        name: "name changed",
                        partner_type_ids: [[0, 0, { name: "one" }]],
                    },
                ],
                [
                    1,
                    41,
                    {
                        name: "name twisted",
                        partner_type_ids: [[0, 0, { name: "two" }]],
                    },
                ],
            ];
        },
    };
    onRpc("web_save", ({ args }) => {
        expect.step("web_save");
        expect(args[1]).toEqual({
            bar: false,
            product_ids: [
                [
                    1,
                    37,
                    {
                        name: "name changed",
                        partner_type_ids: [[0, 0, { name: "one" }]],
                    },
                ],
                [
                    1,
                    41,
                    {
                        name: "name twisted",
                        partner_type_ids: [[0, 0, { name: "two" }]],
                    },
                ],
            ],
        });
    });
    await mountView({
        resModel: "partner",
        type: "form",
        arch: `
                <form>
                    <field name="bar"/>
                    <field name="product_ids">
                        <list>
                            <field name="name"/>
                        </list>
                    </field>
                </form>
            `,
        resId: 2,
    });

    await contains(`.o_data_cell`).click();
    await contains(`.btn-secondary.o_form_button_cancel`).click();
    await contains(`.o-checkbox`).click();
    expect(queryAllTexts(`.o_data_cell`)).toEqual(["name changed", "name twisted"]);
    await contains(`.o_form_button_save`).click();
    expect.verifySteps(["web_save"]);
});
