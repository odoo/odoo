/** @odoo-module **/

import {
    Component,
    EventBus,
    onMounted,
    onPatched,
    onWillStart,
    onWillUpdateProps,
    useEffect,
    useState,
    xml,
} from "@odoo/owl";
import { makeServerError } from "@web/../tests/helpers/mock_server";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import {
    addRow,
    click,
    clickDiscard,
    clickOpenM2ODropdown,
    clickOpenedDropdownItem,
    clickSave,
    dragAndDrop,
    editInput,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    mouseEnter,
    nextTick,
    patchTimeZone,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import {
    toggleActionMenu,
    toggleMenuItem,
    toggleSearchBarMenu,
} from "@web/../tests/search/helpers";
import { makeView, makeViewInDialog, setupViewRegistries } from "@web/../tests/views/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { errorService } from "@web/core/errors/error_service";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { scrollerService } from "@web/core/scroller_service";
import { tooltipService } from "@web/core/tooltip/tooltip_service";
import { SIZES } from "@web/core/ui/ui_service";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { CharField } from "@web/views/fields/char/char_field";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";
import { Field } from "@web/views/fields/field";
import { IntegerField } from "@web/views/fields/integer/integer_field";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { FormController } from "@web/views/form/form_controller";
import { companyService } from "@web/webclient/company_service";

const fieldRegistry = registry.category("fields");
const serviceRegistry = registry.category("services");
const widgetRegistry = registry.category("view_widgets");

let target;
let serverData;

// Record
async function createRecord() {
    await click(target, ".o_control_panel_main_buttons .d-none button.o_form_button_create");
}

QUnit.module("Views", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char", translate: true },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean" },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        qux: {
                            string: "Qux",
                            type: "float",
                            digits: [16, 1],
                            group_operator: "sum",
                        },
                        p: { string: "one2many field", type: "one2many", relation: "partner" },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                        priority: {
                            string: "Priority",
                            type: "selection",
                            selection: [
                                [1, "Low"],
                                [2, "Medium"],
                                [3, "High"],
                            ],
                            default: 1,
                        },
                        state: {
                            string: "State",
                            type: "selection",
                            selection: [
                                ["ab", "AB"],
                                ["cd", "CD"],
                                ["ef", "EF"],
                            ],
                        },
                        date: { string: "Some Date", type: "date" },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        product_ids: {
                            string: "one2many product",
                            type: "one2many",
                            relation: "product",
                        },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner_type", "Partner Type"],
                                ["partner", "Partner"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            product_id: 37,
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            state: "ab",
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            state: "cd",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            state: "ef",
                        },
                        {
                            id: 5,
                            display_name: "aaa",
                            foo: "",
                            bar: false,
                            state: "ef",
                        },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        display_name: { string: "Product Name", type: "char" },
                        name: { string: "Product Name", type: "char" },
                        partner_type_id: {
                            string: "Partner type",
                            type: "many2one",
                            relation: "partner_type",
                        },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char" },
                        color: { string: "Color index", type: "integer" },
                        foo: { string: "Foo", type: "char" },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: {
                            string: "one2many partners field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "user_id",
                        },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Aline",
                            partner_ids: [1],
                        },
                        {
                            id: 19,
                            name: "Christine",
                        },
                    ],
                },
                "res.company": {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                },
            },

            actions: {
                1: {
                    id: 1,
                    name: "Partners Action 1",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "kanban"],
                        [false, "form"],
                    ],
                },
            },
        };

        setupViewRegistries();
        serviceRegistry.add("tooltip", tooltipService);
    });

    QUnit.module("FormView");

    QUnit.test("simple form rendering", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div class="test" style="opacity: 0.5;">some html<span>aa</span></div>
                    <sheet>
                        <group>
                            <group style="background-color: red">
                                <field name="foo" style="color: blue;"/>
                                <field name="bar"/>
                                <field name="int_field" string="f3_description"/>
                                <field name="qux"/>
                            </group>
                            <group>
                                <div class="hello"></div>
                            </group>
                        </group>
                        <notebook>
                            <page string="Partner Yo">
                                <field name="p">
                                    <tree>
                                        <field name="foo"/>
                                        <field name="bar"/>
                                    </tree>
                                </field>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, "div.test");
        assert.hasAttrValue(
            target.querySelector("div.test"),
            "style",
            "opacity: 0.5;",
            "should keep the inline style on html elements"
        );
        assert.containsOnce(target, "label:contains(Foo)");
        assert.containsOnce(target, ".o_field_char input");
        assert.strictEqual(target.querySelector(".o_field_char input").value, "blip");
        assert.hasAttrValue(
            target.querySelector(".o_group .o_inner_group"),
            "style",
            "background-color: red",
            "should apply style attribute on groups"
        );
        assert.hasAttrValue(
            target.querySelector(".o_field_widget[name=foo]"),
            "style",
            "color: blue;",
            "should apply style attribute on fields"
        );
        assert.containsNone(target, "label:contains(something_id)");
        assert.containsOnce(target, "label:contains(f3_description)");
        assert.containsOnce(target, "div.o_field_one2many table");
        assert.containsOnce(
            target,
            "div.o_cell:not(.o_list_record_selector) .o-checkbox input:checked"
        );
        assert.containsNone(target, "label.o_form_label_empty:contains(timmy)");
    });

    QUnit.test("form rendering with class and style attributes", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: /* xml */ `<form class="myCustomClass" style="border: 1px solid red;"/>`,
            resId: 2,
        });
        assert.containsNone(
            target,
            ".o_view_controller[style*='border: 1px solid red;'], .o_view_controller [style*='border: 1px solid red;']",
            "style attribute should not be copied"
        );
        assert.containsOnce(
            target,
            ".o_view_controller.o_form_view.myCustomClass",
            "class attribute should be passed to the view controller"
        );
        assert.containsOnce(
            target,
            ".myCustomClass",
            "class attribute should ONLY be passed to the view controller"
        );
    });

    QUnit.test("generic tags are case insensitive", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <Div class="test">Hello</Div>
                </form>`,
        });

        assert.containsOnce(target, "div.test");
    });

    QUnit.test("form view with a group that contains an invisible group", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <group invisible="1">
                                <field name="foo"/>
                            </group>
                        </group>
                    </sheet>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, ".o_form_view .o_group");
    });

    QUnit.test("status bar rendering without buttons", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><header/><sheet/></form>`,
            resId: 2,
        });

        assert.containsOnce(target, ".o_form_sheet_bg > .o_form_statusbar > .o_statusbar_buttons");
    });

    QUnit.test("button box rendering on small screen", async (assert) => {
        registry.category("services").add("ui", {
            start(env) {
                Object.defineProperty(env, "isSmall", {
                    value: false,
                });
                return {
                    bus: new EventBus(),
                    size: 0,
                    isSmall: true,
                };
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><sheet><div name="button_box"><button id="btn1">MyButton</button><button id="btn2">MyButton2</button><button id="btn3">MyButton3</button><button id="btn4">MyButton4</button></div></sheet></form>`,
            resId: 2,
        });

        assert.containsN(target, ".o-form-buttonbox > button", 3);
        assert.containsOnce(target, ".o-dropdown.oe_stat_button .o_button_more");

        await click(target, ".o-dropdown.oe_stat_button .o_button_more");
        assert.containsOnce(target, ".o-dropdown--menu #btn4");
    });

    QUnit.test("button box rendering on big screen", async (assert) => {
        registry.category("services").add("ui", {
            start(env) {
                Object.defineProperty(env, "isSmall", {
                    value: false,
                });
                return {
                    bus: new EventBus(),
                    size: 9,
                    isSmall: false,
                };
            },
        });

        let btnString = "";
        for (let i = 0; i < 9; i++) {
            btnString += `<button class="oe_stat_button" id="btn${i}">My Button ${i}</button>`;
        }

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><sheet><div name="button_box">${btnString}</div></sheet></form>`,
            resId: 2,
        });

        assert.containsN(target, ".o-form-buttonbox > button", 7);
        assert.containsOnce(target, ".o-form-buttonbox > .oe_stat_button.o-dropdown");

        const buttonBox = target.querySelector(".o-form-buttonbox");
        const buttonBoxRect = buttonBox.getBoundingClientRect();

        for (const btn of buttonBox.children) {
            assert.strictEqual(btn.getBoundingClientRect().top, buttonBoxRect.top);
        }
    });

    QUnit.test("form view gets size class on small and big screens", async (assert) => {
        let uiSize = SIZES.MD;
        const bus = new EventBus();
        registry.category("services").add("ui", {
            start(env) {
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
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><sheet><div></div></sheet></form>`,
            resId: 2,
        });

        assert.containsNone(target, ".o_xxl_form_view, .o_xxs_form_view");

        uiSize = SIZES.XXL;
        bus.trigger("resize");
        await nextTick();
        assert.containsNone(target, ".o_xxs_form_view");
        assert.containsOnce(target, ".o_xxl_form_view");

        uiSize = SIZES.XS;
        bus.trigger("resize");
        await nextTick();
        assert.containsNone(target, ".o_xxl_form_view");
        assert.containsOnce(target, ".o_xxs_form_view");
    });

    QUnit.test("duplicate fields rendered properly", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
        });

        assert.containsNone(target, ".o_field_widget[name=foo].foo_1");
        assert.containsOnce(target, ".o_field_widget[name=foo].foo_2");
        assert.containsOnce(target, ".o_field_widget[name=foo].foo_3");

        await editInput(target, ".o_field_widget[name=foo].foo_3 input", "hello");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo].foo_2 input").value,
            "hello"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget[name=int_field].int_field_1"),
            "o_readonly_modifier"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget[name=int_field].int_field_2"),
            "o_readonly_modifier"
        );
        assert.containsOnce(target, ".int_field_1 input");
        assert.containsOnce(target, ".int_field_2 span");

        await click(target.querySelector(".o_field_widget[name=bar] input"));

        assert.hasClass(
            target.querySelector(".o_field_widget[name=int_field].int_field_1"),
            "o_readonly_modifier"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget[name=int_field].int_field_2"),
            "o_readonly_modifier"
        );
        assert.containsOnce(target, ".int_field_1 span");
        assert.containsOnce(target, ".int_field_2 input");
    });

    QUnit.test("duplicate fields rendered properly (one2many)", async function (assert) {
        serverData.models.partner.records.push({ id: 6, p: [1] });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="foo"/>
                        </tree>
                        <form/>
                    </field>
                    <field name="p" readonly="True">
                        <tree editable="bottom">
                            <field name="foo"/>
                        </tree>
                        <form/>
                    </field>
                </form>`,
            resId: 6,
        });

        assert.containsN(target, ".o_field_one2many", 2);
        assert.doesNotHaveClass(
            target.querySelectorAll(".o_field_one2many")[0],
            "o_readonly_modifier"
        );
        assert.hasClass(target.querySelectorAll(".o_field_one2many")[1], "o_readonly_modifier");

        await click(target.querySelector(".o_field_one2many .o_data_cell"));
        assert.containsOnce(target.querySelector(".o_field_one2many"), ".o_selected_row");
        assert.strictEqual(
            target.querySelector(
                ".o_field_one2many .o_selected_row .o_field_widget[name=foo] input"
            ).value,
            "yop"
        );
        assert.strictEqual(
            target
                .querySelectorAll(".o_field_one2many")[1]
                .querySelector(".o_data_row .o_data_cell[name=foo]").innerText,
            "yop"
        );
        await editInput(
            target.querySelector(".o_field_one2many"),
            ".o_selected_row .o_field_widget[name=foo] input",
            "hello"
        );
        assert.strictEqual(
            target
                .querySelectorAll(".o_field_one2many")[1]
                .querySelector(".o_data_row .o_data_cell[name=foo]").innerText,
            "hello"
        );
        await click(target.querySelector(".o_field_one2many .o_field_x2many_list_row_add a"));
        assert.strictEqual(
            target.querySelector(
                '.o_field_one2many .o_selected_row .o_field_widget[name="foo"] input'
            ).value,
            "My little Foo Value"
        );
        assert.strictEqual(
            target
                .querySelectorAll(".o_field_one2many")[1]
                .querySelectorAll(".o_data_row .o_data_cell[name=foo]")[1].innerText,
            "My little Foo Value"
        );
    });

    QUnit.test("attributes are transferred on async widgets", async function (assert) {
        const def = makeDeferred();
        class AsyncField extends CharField {
            willStart() {
                return def;
            }
        }
        fieldRegistry.add("asyncwidget", { component: AsyncField });

        const viewProm = makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo" style="color: blue;" widget="asyncwidget"/></form>`,
            resId: 2,
        });
        await nextTick();
        def.resolve();
        await viewProm;
        assert.hasAttrValue(
            target.querySelector(".o_field_widget[name=foo]"),
            "style",
            "color: blue;",
            "should apply style attribute on fields"
        );
    });

    QUnit.test("placeholder attribute on input", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><input placeholder="chimay"/></form>',
            resId: 2,
        });

        assert.containsOnce(target, 'input[placeholder="chimay"]');
    });

    QUnit.test("decoration works on widgets", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="display_name" decoration-danger="int_field &lt; 5"/>
                    <field name="foo" decoration-danger="int_field &gt; 5"/>
                </form>`,
            resId: 2,
        });
        assert.doesNotHaveClass(
            target.querySelector('.o_field_widget[name="display_name"]'),
            "text-danger"
        );
        assert.hasClass(target.querySelector('.o_field_widget[name="foo"]'), "text-danger");
    });

    QUnit.test(
        "form with o2m having a many2many fields using the many2many_tags widget along the color_field option",
        async function (assert) {
            // In this scenario, the x2many form view isn't inline, so when we click on the record,
            // it does an independant getView, which doesn't return all fields of the model. In the
            // x2many list view, there's a field with a many2many_tags widget with the color option,
            // and the color field (color) in our case, isn't in the form view.
            // This test ensures that we can open the form view in this situation.
            serverData.models.partner.records[0].timmy = [12, 14];
            serverData.views = {
                "partner,false,form": `
                <form>
                    <field name="display_name"/>
                    <field name="timmy" widget="one2many">
                        <tree string="Values">
                            <field name="display_name"/>
                            <!--
                                Required to add at least one different field than the fields read
                                to display <field name="timmy" widget="many2many_tags"/> below.
                                To force to re-read the record with more fields.
                            -->
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            };
            await makeView({
                type: "form",
                resModel: "user",
                serverData,
                arch: `
                <form edit="0">
                    <field name="partner_ids">
                        <tree>
                            <field name="display_name"/>
                            <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                        </tree>
                    </field>
                </form>`,
                resId: 17,
            });
            assert.containsOnce(target, ".o_field_widget[name=timmy] .o_field_tags");
            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.containsOnce(target, ".modal .o_form_view .o_field_widget[name=timmy]");
        }
    );

    QUnit.test("form with o2m having a field with fieldDependencies", async function (assert) {
        // In this scenario, the x2many form view isn't inline, so when we click on the record,
        // it does an independant getView, which doesn't return all fields of the model. In the
        // x2many list view, there's a field with fieldDependencies, and the dependency field
        // (int_field) in our case, isn't in the form view. This test ensures that we can open
        // the form view in this situation.
        class MyField extends CharField {}
        fieldRegistry.add("my_widget", {
            component: MyField,
            fieldDependencies: [{ name: "int_field", type: "integer" }],
        });
        serverData.models.partner.records[1].p = [1];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo" widget="my_widget"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, ".o_field_widget[name=p] .o_data_row");
        await click(target.querySelector(".o_field_widget[name=p] .o_data_row .o_data_cell"));
        assert.containsOnce(target, ".modal .o_form_view .o_field_widget[name=p]");
    });

    QUnit.test("fieldDependencies are readonly by default", async function (assert) {
        class MyField extends CharField {}
        fieldRegistry.add("my_widget", {
            component: MyField,
            fieldDependencies: [
                { name: "int_field", type: "integer" },
                { name: "bar", type: "boolean" },
                { name: "qux", type: "float", readonly: false },
            ],
        });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="display_name"/>
                    <field name="foo" widget="my_widget"/>
                    <field name="int_field" readonly="1"/>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.args[1],
                        {
                            display_name: "plop",
                            foo: "My little Foo Value",
                            qux: 0,
                        },
                        " 'int_field' and 'bar' shouldn't be present"
                    );
                    assert.step("web_save");
                }
            },
        });

        await editInput(target, "[name='display_name'] input", "plop");
        await clickSave(target);
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("decoration-bf works on fields", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="display_name" decoration-bf="int_field &lt; 5"/>
                    <field name="foo" decoration-bf="int_field &gt; 5"/>
                </form>`,
            resId: 2,
        });
        assert.doesNotHaveClass(
            target.querySelector('.o_field_widget[name="display_name"]'),
            "fw-bold"
        );
        assert.hasClass(target.querySelector('.o_field_widget[name="foo"]'), "fw-bold");
    });

    QUnit.test("decoration-it works on fields", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="display_name" decoration-it="int_field &lt; 5"/>
                    <field name="foo" decoration-it="int_field &gt; 5"/>
                </form>`,
            resId: 2,
        });
        assert.doesNotHaveClass(
            target.querySelector('.o_field_widget[name="display_name"]'),
            "fst-italic"
        );
        assert.hasClass(target.querySelector('.o_field_widget[name="foo"]'), "fst-italic");
    });

    QUnit.test("decoration on widgets are reevaluated if necessary", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="display_name" decoration-danger="int_field &lt; 5"/>
                </form>`,
            resId: 2,
        });
        assert.doesNotHaveClass(
            target.querySelector('.o_field_widget[name="display_name"]'),
            "text-danger"
        );
        await editInput(target, ".o_field_widget[name=int_field] input", 3);
        assert.hasClass(
            target.querySelector('.o_field_widget[name="display_name"]'),
            "text-danger"
        );
    });

    QUnit.test("decoration on widgets works on same widget", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="int_field" decoration-danger="int_field &lt; 5"/></form>`,
            resId: 2,
        });
        assert.doesNotHaveClass(
            target.querySelector('.o_field_widget[name="int_field"]'),
            "text-danger"
        );
        await editInput(target, ".o_field_widget[name=int_field] input", 3);
        assert.hasClass(target.querySelector('.o_field_widget[name="int_field"]'), "text-danger");
    });

    QUnit.test("only necessary fields are fetched with correct context", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            resId: 1,
            mockRPC(route, { method, kwargs }) {
                if (method === "web_read") {
                    assert.deepEqual(
                        kwargs.specification,
                        { foo: {}, display_name: {} },
                        "should only fetch requested fields"
                    );
                    assert.strictEqual(
                        kwargs.context.bin_size,
                        true,
                        "bin_size should always be in the context"
                    );
                }
            },
        });
    });

    QUnit.test("group rendering", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, "div.o_inner_group");
    });

    QUnit.test("group with formLabel", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_field_char");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "col-lg-6");

        assert.hasClass(target.querySelector(".o_form_label[for=foo_0]"), "plop");
        assert.hasClass(target.querySelector(".o_form_label[for=foo_0]"), "plop2");
        assert.hasClass(target.querySelector(".o_form_label[for=foo_0]"), "col-lg-6");
    });

    QUnit.test("group containing both a field and a group", async function (assert) {
        // The purpose of this test is to check that classnames defined in a
        // field widget and those added by the form renderer are correctly
        // combined. For instance, the renderer adds className 'o_group_col_x'
        // on outer group's children (an outer group being a group that contains
        // at least a group).
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="foo"/>
                        <group>
                            <field name="int_field"/>
                        </group>
                    </group>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_group .o_field_widget[name=foo]");
        assert.containsOnce(target, ".o_group .o_inner_group .o_field_widget[name=int_field]");

        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_field_char");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "col-lg-6");
    });

    QUnit.test("Form and subview with _view_ref contexts", async function (assert) {
        assert.expect(3);

        serverData.models.product.fields.partner_type_ids = {
            string: "one2many field",
            type: "one2many",
            relation: "partner_type",
        };
        serverData.models.product.records = [
            { id: 1, name: "Tromblon", partner_type_ids: [12, 14] },
        ];
        serverData.models.partner.records[0].product_id = 1;

        // This is an old test, written before "get_views" (formerly "load_views") automatically
        // inlines x2many subviews. As the purpose of this test is to assert that the js fetches
        // the correct sub view when it is not inline (which can still happen in nested form views),
        // we bypass the inline mecanism of "get_views" by setting widget="one2many" on the field.
        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="name"/>
                    <field name="partner_type_ids" widget="one2many" context="{'tree_view_ref': 'some_other_tree_view'}"/>
                </form>`,

            "partner_type,false,list": `<tree><field name="color"/></tree>`,
            "product,false,search": "<search></search>",
            "partner,false,form": `
                <form>
                    <field name="name"/>
                    <field name="product_id" context="{'tree_view_ref': 'some_tree_view'}"/>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            if (args.method === "get_views") {
                const context = args.kwargs.context;
                if (args.model === "product") {
                    assert.strictEqual(
                        context.tree_view_ref,
                        "some_tree_view",
                        "The correct _view_ref should have been sent to the server, first time"
                    );
                }
                if (args.model === "partner_type") {
                    assert.strictEqual(
                        context.base_model_name,
                        undefined,
                        "The correct base_model_name should be removed from the context before sent to the server for the subview"
                    );
                    assert.strictEqual(
                        context.tree_view_ref,
                        "some_other_tree_view",
                        "The correct _view_ref should have been sent to the server for the subview"
                    );
                }
            }
            if (args.method === "get_formview_action") {
                return Promise.resolve({
                    res_id: 1,
                    type: "ir.actions.act_window",
                    target: "current",
                    res_model: args.model,
                    context: args.kwargs.context,
                    view_mode: "form",
                    views: [[false, "form"]],
                });
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, {
            res_id: 1,
            type: "ir.actions.act_window",
            target: "current",
            res_model: "partner",
            view_mode: "form",
            views: [[false, "form"]],
        });

        await click(target.querySelector('.o_field_widget[name="product_id"] .o_external_button'));
    });

    QUnit.test("Form and subsubview with only _view_ref contexts", async function (assert) {
        serverData.models.partner_type.fields.company_ids = {
            string: "one2many field",
            type: "one2many",
            relation: "res.company",
        };
        serverData.views = {
            "res.company,false,search": "<search></search>",
            "res.company,false,list": `<tree><field name="name"/></tree>`,
            "res.company,bar_rescompany_form_view,form": `<form><field name="name"/></form>`,
            "partner_type,false,search": "<search></search>",
            "partner_type,false,list": `<tree><field name="name"/></tree>`,
            "partner_type,foo_partner_type_form_view,form": `
                <form>
                    <field name="color"/>
                    <field name="company_ids" context="{
                        'default_color': 2,
                        'form_view_ref': 'bar_rescompany_form_view'
                    }"/>
                </form>`,
        };

        const userContext = {
            lang: "en",
            tz: "taht",
            uid: 7,
        };
        const expectedContexts = new Map();

        // Make main form view
        expectedContexts.set("view:partner", { ...userContext });
        expectedContexts.set("onchange:partner", { ...userContext });
        expectedContexts.set("view:partner_type", {
            ...userContext,
            form_view_ref: "foo_partner_type_form_view",
        });
        expectedContexts.set("onchange:partner_type", {
            ...userContext,
            base_model_name: "partner",
            form_view_ref: "foo_partner_type_form_view",
        });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field string="Partner Types" name="timmy" widget="one2many" context="{
                        'default_partner_id': id,
                        'form_view_ref': 'foo_partner_type_form_view'
                    }"/>
                </form>`,
            resId: 2,
            mockRPC: (route, { method, model, kwargs }) => {
                if (method === "get_views") {
                    const { context } = kwargs;
                    assert.step(`${method} (${model})`);
                    assert.deepEqual(context, expectedContexts.get("view:" + model));
                }
                if (method === "onchange") {
                    const { context } = kwargs;
                    assert.step(`${method} (${model})`);
                    assert.deepEqual(context, expectedContexts.get("onchange:" + model));
                }
            },
        });
        assert.verifySteps(["get_views (partner)", "get_views (partner_type)"]);

        // Add a line in the x2many timmy field
        expectedContexts.clear();
        expectedContexts.set("view:partner_type", {
            ...userContext,
            form_view_ref: "foo_partner_type_form_view",
        });
        expectedContexts.set("onchange:partner_type", {
            ...userContext,
            default_partner_id: 2,
            form_view_ref: "foo_partner_type_form_view",
        });
        await click(target, "[name=timmy] .o_field_x2many_list_row_add a");
        assert.verifySteps(["get_views (partner_type)"]);

        // Create a new timmy
        await click(target, ".modal .o_create_button");
        assert.verifySteps(["get_views (partner_type)", "onchange (partner_type)"]);

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
        await click(target, ".modal [name=company_ids] .o_field_x2many_list_row_add a");
        assert.verifySteps(["get_views (res.company)", "onchange (res.company)"]);
    });

    QUnit.test("invisible fields are properly hidden", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                        <field name="qux" invisible="1"/>
                        <field name="p" invisible="True"/>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsNone(target, "label:contains(Foo)");
        assert.containsNone(target, ".o_field_widget[name=foo]");
        assert.containsNone(target, ".o_field_widget[name=qux]");
        assert.containsNone(target, ".o_field_widget[name=p]");
    });

    QUnit.test("correctly copy attributes to compiled labels", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <label string="Apply after" for="bar" class="a"/>
                    <field name="bar" class="b"/>
                    <label string="hours" for="bar" class="c"/>
                </form>`,
        });

        assert.hasClass(target.querySelectorAll(".o_form_label")[0], "a");
        assert.hasClass(target.querySelector(".o_field_widget.o_field_boolean"), "b");
        assert.hasClass(target.querySelectorAll(".o_form_label")[1], "c");
    });

    QUnit.test("invisible fields are not used for the label generation", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="qux" invisible="1"/>
                        <label for="qux"/>
                        <field name="qux"/>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, "label:contains(Qux)");
    });

    QUnit.test("invisible elements are properly hidden", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });
        assert.containsNone(target, ".o_form_statusbar button:contains(coucou)");
        assert.containsOnce(target, ".o_notebook li a:contains(visible)");
        assert.containsNone(target, ".o_notebook li a:contains(invisible)");
        assert.containsOnce(target, "div.o_inner_group:contains(visgroup)");
        assert.containsNone(target, "div.o_inner_group:contains(invgroup)");
    });

    QUnit.test(
        "invisible attrs on fields are re-evaluated on field change",
        async function (assert) {
            // we set the value bar to simulate a falsy boolean value.
            serverData.models.partner.records[0].bar = false;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="int_field"/>
                                <field name="timmy" invisible="1"/>
                                <field name="foo" invisible="int_field == 10"/>
                                <field name="bar" invisible="not bar and not timmy"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, ".o_field_widget[name=int_field]");
            assert.containsNone(target, ".o_field_widget[name=timmy]");
            assert.containsNone(target, ".o_field_widget[name=foo]");
            assert.containsNone(target, ".o_field_widget[name=bar]");

            await editInput(target, ".o_field_widget[name=int_field] input", 44);
            assert.containsOnce(target, ".o_field_widget[name=int_field]");
            assert.containsNone(target, ".o_field_widget[name=timmy]");
            assert.containsOnce(target, ".o_field_widget[name=foo]");
            assert.containsNone(target, ".o_field_widget[name=bar]");
        }
    );

    QUnit.test("invisible attrs char fields", async function (assert) {
        // For a char/text field, the server can return false or "" (empty string),
        // depending if the field isn't set in db (NULL) or set to the empty string.
        // This makes no difference in the UI, but it matters when evaluating modifiers.
        serverData.models.partner.records[0].display_name = false;
        serverData.models.partner.records[0].foo = "";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div class="a" invisible="foo == False">b</div>
                    <div class="b" invisible="foo == ''">b</div>
                    <div class="c" invisible="not display_name">c</div>
                    <div class="d" invisible="display_name == ''">d</div>
                    <div class="e" invisible="not foo">e</div>
                    <div class="f" invisible="display_name == False">f</div>
                    <field name="foo" invisible="1"/>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, "div.a");
        assert.containsNone(target, "div.b");
        assert.containsNone(target, "div.c");
        assert.containsOnce(target, "div.d");
        assert.containsNone(target, "div.e");
        assert.containsNone(target, "div.f");
    });

    QUnit.test(
        "properly handle modifiers and attributes on notebook tags",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
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
                    </form>`,
                resId: 1,
            });

            assert.containsNone(target, ".o_notebook");
            await editInput(target, ".o_field_widget[name=int_field] input", 44);

            assert.containsOnce(target, ".o_notebook");
            assert.hasClass(target.querySelector(".o_notebook"), "new_class");
        }
    );

    QUnit.test("empty notebook", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook/>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsNone(target, ":scope .o_notebook .nav");
    });

    QUnit.test("notebook page name and class transferred to DOM", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form>
                        <sheet>
                            <notebook>
                                <page name="choucroute" string="Choucroute" class="sauerKraut">
                                    <field name="foo"/>
                                </page>
                            </notebook>
                        </sheet>
                    </form>`,
        });
        assert.hasClass(
            target.querySelector(".o_notebook .nav .nav-link[name='choucroute']"),
            "active sauerKraut"
        );
    });

    QUnit.test("no visible page", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });

        assert.containsNone(target, ".o_notebook_headers .nav-item");
        assert.containsNone(target, ".tab-content .tab-pane");
    });

    QUnit.test("notebook: pages with invisible modifiers", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                                <field name="qux"/>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsN(target, ".o_notebook .nav-link", 2);
        assert.containsOnce(target, ".o_notebook .nav .nav-link.active");
        assert.hasClass(target.querySelector(".o_notebook .nav .nav-link"), "active");
        assert.strictEqual(target.querySelector(".o_notebook .nav-link.active").textContent, "A");

        await click(target.querySelector(".o_field_widget[name=bar] input"));

        assert.containsN(target, ".o_notebook .nav-link", 2);
        assert.containsOnce(target, ".o_notebook .nav .nav-link.active");
        assert.hasClass(target.querySelector(".o_notebook .nav .nav-link"), "active");
        assert.strictEqual(target.querySelector(".o_notebook .nav-link.active").textContent, "B");
    });

    QUnit.test("invisible attrs on first notebook page", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });

        assert.containsN(target, ".o_notebook .nav .nav-link", 2);
        assert.hasClass(target.querySelector(".o_notebook .nav .nav-link"), "active");
        assert.hasClass(target.querySelector(".o_notebook .tab-content .tab-pane"), "active");

        await editInput(target, ".o_field_widget[name=int_field] input", 44);
        assert.containsOnce(target, ".o_notebook .nav .nav-link");
        assert.containsOnce(target, ".o_notebook .tab-content .tab-pane");
        assert.hasClass(target.querySelector(".o_notebook .nav .nav-link"), "active");
        assert.hasClass(target.querySelector(".o_notebook .tab-content .tab-pane"), "active");
    });

    QUnit.test("invisible attrs on notebook page which has only one page", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });

        assert.containsNone(target, ".o_notebook");

        // enable checkbox
        await click(target.querySelector(".o_field_boolean input"));
        assert.containsOnce(target, ".o_notebook .nav .nav-link");
        assert.containsOnce(target, ".o_notebook .tab-content .tab-pane");
        assert.hasClass(target.querySelector(".o_notebook .nav .nav-link"), "active");
        assert.hasClass(target.querySelector(".o_notebook .tab-content .tab-pane"), "active");
    });

    QUnit.test("first notebook page invisible", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_notebook .nav .nav-link");
        assert.hasClass(target.querySelector(".o_notebook .nav .nav-link"), "active");
    });

    QUnit.test("hide notebook element if all pages hidden", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="bar"/>
                        <notebook class="new_class">
                            <page string="Foo" invisible="bar">
                                <field name="foo"/>
                            </page>
                            <page string="Qux" invisible="1">
                                <field name="qux"/>
                            </page>
                            <page string="IntField" invisible="bar">
                                <field name="int_field"/>
                            </page>
                        </notebook>
                    </sheet>
                </form>`,
        });

        assert.containsN(target, ".o_notebook .nav .nav-link", 2);

        await click(target.querySelector(".o_field_boolean input"));
        assert.containsNone(target, ".o_notebook");
    });

    QUnit.test("autofocus on second notebook page", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });

        assert.doesNotHaveClass(
            target.querySelector(".o_notebook .nav .nav-item:first-child .nav-link"),
            "active"
        );
        assert.hasClass(
            target.querySelector(".o_notebook .nav .nav-item:nth-child(2) .nav-link"),
            "active"
        );
    });

    QUnit.test(
        "notebook page is changing when an anchor is clicked from another page",
        async (assert) => {
            serviceRegistry.add("scroller", scrollerService);

            const scrollableParent = document.createElement("div");
            scrollableParent.style.overflow = "auto";
            target.append(scrollableParent);

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `<form>
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
                </form>`,
                resId: 1,
            });

            scrollableParent.append(target.querySelector(".o_form_view"));

            // We set the height of the parent to the height of the second pane
            // We are then sure there will be no scrollable on this pane but a
            // only for the first pane
            scrollableParent.style.maxHeight = "400px";

            // The element must be contained in the scrollable parent (top and bottom)
            const isVisible = (el) => {
                return (
                    el.getBoundingClientRect().bottom <=
                        scrollableParent.getBoundingClientRect().bottom &&
                    el.getBoundingClientRect().top >= scrollableParent.getBoundingClientRect().top
                );
            };

            assert.ok(
                scrollableParent
                    .querySelector(".tab-pane.active")
                    .contains(scrollableParent.querySelector("#anchor1")),
                "the first pane is visible"
            );
            assert.containsNone(target, "#anchor2", "the second anchor is not visible");

            await click(scrollableParent.querySelector(".link2"));
            assert.ok(
                scrollableParent
                    .querySelector(".tab-pane.active")
                    .contains(scrollableParent.querySelector("#anchor2")),
                "the second pane is visible"
            );
            assert.ok(
                isVisible(scrollableParent.querySelector("#anchor2")),
                "the second anchor is visible"
            );

            await click(scrollableParent.querySelector(".link1"));
            assert.ok(
                scrollableParent
                    .querySelector(".tab-pane.active")
                    .contains(scrollableParent.querySelector("#anchor1")),
                "the first pane is visible"
            );
            assert.ok(
                isVisible(scrollableParent.querySelector("#anchor1")),
                "the first anchor is visible"
            );

            await click(target.querySelector(".outerLink2"));
            assert.ok(
                scrollableParent
                    .querySelector(".tab-pane.active")
                    .contains(scrollableParent.querySelector("#anchor2")),
                "the second pane is visible"
            );
            assert.ok(
                isVisible(scrollableParent.querySelector("#anchor2")),
                "the second anchor is visible"
            );
        }
    );

    QUnit.test(
        "invisible attrs on group are re-evaluated on field change",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
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
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, "div.o_group");
            await click(target.querySelector(".o_field_boolean input"));
            assert.containsNone(target, "div.o_group");
        }
    );

    QUnit.test(
        "invisible attrs with zero value in domain and unset value in data",
        async function (assert) {
            serverData.models.partner.fields.int_field.type = "monetary";

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <field name="foo"/>
                            <group invisible='int_field == 0.0'>
                                <div class="hello">this should be invisible</div>
                                <field name="int_field"/>
                            </group>
                        </sheet>
                    </form>`,
            });

            assert.containsNone(target, "div.hello");
        }
    );

    QUnit.test("reset local state when switching to another view", async function (assert) {
        serverData.views = {
            "partner,false,form": `
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
                </form>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
            "partner,false,search": "<search></search>",
        };

        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        };

        const target = getFixture();
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        await click(target, ".o_control_panel_main_buttons .d-none button.o_list_button_add");
        assert.containsOnce(target, ".o_form_view");
        // sanity check: notebook active page is first page
        assert.hasClass(target.querySelector(".o_notebook .nav-link"), "active");

        // click on second page tab
        await click(target.querySelectorAll(".o_notebook .nav-link")[1]);
        assert.hasClass(target.querySelectorAll(".o_notebook .nav-link")[1], "active");

        await click(target.querySelector(".o_control_panel .o_form_button_cancel"));
        assert.containsNone(target, ".o_form_view");

        await click(target, ".o_control_panel_main_buttons .d-none button.o_list_button_add");
        assert.containsOnce(target, ".o_form_view");
        // check notebook active page is first page again
        assert.hasClass(target.querySelector(".o_notebook .nav-link"), "active");
    });

    QUnit.test(
        "trying to leave an invalid form view should not change the navbar",
        async function (assert) {
            serverData.menus = {
                root: { id: "root", children: [1, 2], name: "root", appID: "root" },
                1: { id: 1, children: [], name: "App0", appID: 1, xmlid: "menu_3", actionID: 1 },
                2: { id: 2, children: [], name: "App1", appID: 2, xmlid: "menu_3", actionID: 2 },
            };
            serverData.views = {
                "partner,false,form": `
                <form>
                    <sheet>
                        <field name="display_name" required="1"/>
                        <field name="foo"/>
                    </sheet>
                </form>`,
                "product,false,list": '<tree><field name="display_name"/></tree>',
                "product,false,search": "<search></search>",
                "partner,false,search": "<search></search>",
            };

            serverData.actions = {
                1: {
                    id: 1,
                    name: "Partner",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
                2: {
                    id: 2,
                    name: "Product",
                    res_model: "product",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
            };

            const target = getFixture();
            const webClient = await createWebClient({ serverData });

            await doAction(webClient, 1);
            await nextTick();
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_main_navbar .o_menu_brand").textContent,
                "App0"
            );

            await editInput(target, "[name='foo'] input", "blop");
            await click(target, ".o_navbar_apps_menu button");
            await click(target, ".o_navbar_apps_menu .dropdown-item[data-section='2']");
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_main_navbar .o_menu_brand").textContent,
                "App0"
            );

            await editInput(target, "[name='display_name'] input", "blop");
            await click(target, ".o_navbar_apps_menu button");
            await click(target, ".o_navbar_apps_menu .dropdown-item[data-section='2']");
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o_main_navbar .o_menu_brand").textContent,
                "App1"
            );
        }
    );

    QUnit.test("rendering stat buttons with action", async function (assert) {
        assert.expect(3);

        const fakeActionService = {
            start() {
                return {
                    doActionButton(params) {
                        assert.strictEqual(params.name, "someaction");
                        assert.strictEqual(params.type, "action");
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, "button.oe_stat_button");
        await click(target.querySelector(".oe_stat_button")); // should not call doActionButton
    });

    QUnit.test("rendering stat buttons without class", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
        });

        assert.containsOnce(
            target,
            "button.oe_stat_button",
            "button should have oe_stat_button class"
        );
    });

    QUnit.test("rendering stat buttons without action", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
        });

        assert.containsOnce(
            target,
            "button.oe_stat_button[disabled]",
            "stat button should be disabled"
        );
    });

    QUnit.test("readonly stat buttons stays disabled", async function (assert) {
        assert.expect(4);

        const fakeActionService = {
            start() {
                return {
                    async doActionButton(params) {
                        if (params.name == "action_to_perform") {
                            assert.containsN(
                                target,
                                "button.oe_stat_button[disabled]",
                                2,
                                "While performing the action, both buttons should be disabled."
                            );
                        }
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
        });

        assert.containsN(target, "button.oe_stat_button", 2);
        assert.containsN(target, "button.oe_stat_button[disabled]", 1);
        await click(target.querySelector("button[name=action_to_perform]"));
        assert.containsOnce(
            target,
            "button.oe_stat_button[disabled]",
            "After performing the action, only one button should be disabled."
        );
    });

    QUnit.test(
        "label with no string attribute gets the default label for the corresponding field",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
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
                </form>`,
                resId: 2,
            });

            assert.containsOnce(target, "label.o_form_label");
            assert.strictEqual(target.querySelector("label.o_form_label").textContent, "Bar");
        }
    );

    QUnit.test("label uses the string attribute when present", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, "label.o_form_label");
        assert.strictEqual(target.querySelector("label.o_form_label").textContent, "customstring");
    });

    QUnit.test("label ignores the content of the label when present", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, "label.o_form_label");
        assert.strictEqual(target.querySelector("label.o_form_label").textContent, "Bar");
    });

    QUnit.test(
        "label with empty string attribute renders to an empty label",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
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
                </form>`,
                resId: 2,
            });

            assert.containsOnce(target, "label.o_form_label");
            assert.equal(target.querySelector("label.o_form_label").textContent, "");
        }
    );

    QUnit.test(
        "two mutually exclusive labels with a dynamic invisible attribute",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <sheet>
                        <group>
                            <label for="bar" string="label1" invisible='bar'/>
                            <label for="bar" string="label2" invisible='not bar'/>
                            <field name="bar" nolabel="1"/>
                        </group>
                    </sheet>
                </form>`,
                resId: 2,
            });
            assert.containsOnce(target, "label.o_form_label", "Only one label should be displayed");
            assert.strictEqual(target.querySelector("label.o_form_label").textContent, "label2");
            assert.containsOnce(
                target,
                ".o_inner_group > div",
                "This group should only contain one line"
            );
        }
    );

    QUnit.test(
        "label is not rendered when invisible and not at top-level in a group",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
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
                </form>`,
                resId: 2,
            });
            assert.containsNone(target, "label.o_form_label");
        }
    );

    QUnit.test(
        "input ids for multiple occurrences of fields in form view",
        async function (assert) {
            // A same field can occur several times in the view, but its id must be
            // unique by occurrence, otherwise there is a warning in the console (in
            // edit mode) as we get several inputs with the same "id" attribute, and
            // several labels the same "for" attribute.
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="foo"/>
                            <label for="qux"/>
                            <div><field name="qux"/></div>
                        </group>
                        <group>
                            <field name="foo"/>
                            <label for="qux2"/>
                            <div><field name="qux" id="qux2"/></div>
                        </group>
                    </form>`,
            });

            const fieldIdAttrs = [...target.querySelectorAll(".o_field_widget input")].map((n) =>
                n.getAttribute("id")
            );
            const labelForAttrs = [...target.querySelectorAll(".o_form_label")].map((n) =>
                n.getAttribute("for")
            );

            assert.strictEqual(
                [...new Set(fieldIdAttrs)].length,
                4,
                "should have generated a unique id for each field occurrence"
            );
            assert.deepEqual(
                fieldIdAttrs,
                labelForAttrs,
                "the for attribute of labels must coincide with field ids"
            );
        }
    );

    QUnit.test(
        "input ids for multiple occurrences of fields in sub form view (inline)",
        async function (assert) {
            // A same field can occur several times in the view, but its id must be
            // unique by occurrence, otherwise there is a warning in the console (in
            // edit mode) as we get several inputs with the same "id" attribute, and
            // several labels the same "for" attribute.
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree><field name="foo"/></tree>
                        <form>
                            <group>
                                <field name="foo"/>
                                <label for="qux"/>
                                <div><field name="qux"/></div>
                            </group>
                            <group>
                                <field name="foo"/>
                                <label for="qux2"/>
                                <div><field name="qux" id="qux2"/></div>
                            </group>
                        </form>
                    </field>
                </form>`,
            });

            await click(target.querySelector(".o_field_x2many_list_row_add a"));

            assert.containsOnce(document.body, ".modal .o_form_view");

            const fieldIdAttrs = [...$(".modal .o_form_view .o_field_widget input")].map((n) =>
                n.getAttribute("id")
            );
            const labelForAttrs = [...$(".modal .o_form_view .o_form_label")].map((n) =>
                n.getAttribute("for")
            );

            assert.strictEqual(
                [...new Set(fieldIdAttrs)].length,
                4,
                "should have generated a unique id for each field occurrence"
            );
            assert.deepEqual(
                fieldIdAttrs,
                labelForAttrs,
                "the for attribute of labels must coincide with field ids"
            );
        }
    );

    QUnit.test(
        "input ids for multiple occurrences of fields in sub form view (not inline)",
        async function (assert) {
            // A same field can occur several times in the view, but its id must be
            // unique by occurrence, otherwise there is a warning in the console (in
            // edit mode) as we get several inputs with the same "id" attribute, and
            // several labels the same "for" attribute.
            serverData.views = {
                "partner,false,list": '<tree><field name="foo"/></tree>',
                "partner,false,form": `
                    <form>
                        <group>
                            <field name="foo"/>
                            <label for="qux"/>
                            <div><field name="qux"/></div>
                        </group>
                        <group>
                            <field name="foo"/>
                            <label for="qux2"/>
                            <div><field name="qux" id="qux2"/></div>
                        </group>
                    </form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="p" widget="one2many"/></form>',
            });

            await click(target.querySelector(".o_field_x2many_list_row_add a"));

            assert.containsOnce(document.body, ".modal .o_form_view");

            const fieldIdAttrs = [...$(".modal .o_form_view .o_field_widget input")].map((n) =>
                n.getAttribute("id")
            );
            const labelForAttrs = [...$(".modal .o_form_view .o_form_label")].map((n) =>
                n.getAttribute("for")
            );

            assert.strictEqual(
                [...new Set(fieldIdAttrs)].length,
                4,
                "should have generated a unique id for each field occurrence"
            );
            assert.deepEqual(
                fieldIdAttrs,
                labelForAttrs,
                "the for attribute of labels must coincide with field ids"
            );
        }
    );

    QUnit.test("two occurrences of invalid field in form view", async function (assert) {
        serverData.models.partner.fields.trululu.required = true;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="trululu"/>
                        <field name="trululu"/>
                    </group>
                </form>`,
        });

        await clickSave(target);

        assert.containsN(target, ".o_form_label.o_field_invalid", 2);
        assert.containsN(target, ".o_field_many2one.o_field_invalid", 2);
    });

    QUnit.test("two occurrences of invalid integer fields in form view", async function (assert) {
        serverData.models.partner.fields.trululu.required = true;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field" class="a"/>
                        <field name="int_field" class="b"/>
                    </group>
                </form>`,
        });

        await editInput(target, ".a input", "abc");

        assert.containsN(target, ".o_form_label.o_field_invalid", 2);
        assert.containsN(target, ".o_field_integer.o_field_invalid", 2);

        await editInput(target, ".b input", "10");

        assert.containsNone(target, ".o_form_label.o_field_invalid");
        assert.containsNone(target, ".o_field_integer.o_field_invalid");
    });

    QUnit.test("twice same field with different required attributes", async function (assert) {
        delete serverData.models.partner.fields.foo.default;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="bar"/>
                        <field name="int_field"/>
                        <field name="foo" required="not bar"/>
                        <field name="foo" required="int_field == 44"/>
                    </group>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.hasClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[0],
            "o_required_modifier"
        );
        assert.doesNotHaveClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[1],
            "o_required_modifier"
        );

        await click(target, ".o_field_widget[name=bar] input");
        assert.doesNotHaveClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[0],
            "o_required_modifier"
        );
        assert.doesNotHaveClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[1],
            "o_required_modifier"
        );

        await editInput(target, ".o_field_widget[name=int_field] input", "44");
        assert.doesNotHaveClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[0],
            "o_required_modifier"
        );
        assert.hasClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[1],
            "o_required_modifier"
        );

        await clickSave(target);
        assert.containsN(target, ".o_form_label.o_field_invalid", 2);
        assert.containsN(target, ".o_field_widget.o_field_invalid", 2);

        assert.verifySteps(["get_views", "onchange"]);
    });

    QUnit.test("twice same field with different readonly attributes", async function (assert) {
        delete serverData.models.partner.fields.foo.default;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="bar"/>
                        <field name="int_field"/>
                        <field name="foo" readonly="not bar"/>
                        <field name="foo" readonly="int_field == 0"/>
                    </group>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1], {
                        bar: true,
                        int_field: 0,
                        foo: "some value",
                    });
                }
            },
        });

        assert.hasClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[0],
            "o_readonly_modifier"
        );
        assert.hasClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[1],
            "o_readonly_modifier"
        );

        await click(target, ".o_field_widget[name=bar] input");
        assert.doesNotHaveClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[0],
            "o_readonly_modifier"
        );
        assert.hasClass(
            target.querySelectorAll(".o_field_widget[name=foo]")[1],
            "o_readonly_modifier"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "some value");

        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "some value"
        );
    });

    QUnit.test("twice same field with different invisible attributes", async function (assert) {
        delete serverData.models.partner.fields.foo.default;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="bar"/>
                        <field name="int_field"/>
                        <field name="foo" required="1" invisible="not bar"/>
                        <field name="foo" invisible="int_field == 0"/>
                    </group>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.containsNone(target, ".o_field_widget[name=foo]");

        await click(target, ".o_field_widget[name=bar] input");
        assert.containsOnce(target, ".o_field_widget[name=foo]");

        // foo is required, and as it isn't invisible (at least for one occurrence), it shouldn't
        // allow to save as it is not set
        await clickSave(target);
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_field_invalid");

        assert.verifySteps(["get_views", "onchange"]);
    });

    QUnit.test("required field computed by another field in a form view", async function (assert) {
        serverData.models.partner.fields.foo.default = false;
        serverData.models.partner.onchanges = {
            foo(record) {
                if (record.foo) {
                    record.display_name = "plop";
                }
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="display_name" required="1"/>
                        <field name="foo"/>
                    </form>
                    `,
        });
        await clickSave(target);
        assert.containsOnce(target, ".o_form_editable");
        assert.containsOnce(target, ".o_field_invalid");

        await editInput(target, "[name='foo'] input", "hello");
        assert.containsOnce(target, ".o_form_editable");
        assert.containsNone(target, ".o_field_invalid");
    });

    QUnit.test("required field computed by another field in a x2m", async function (assert) {
        serverData.models.partner.fields.foo.default = false;
        serverData.models.partner.onchanges = {
            foo(record) {
                if (record.foo) {
                    record.display_name = "plop";
                }
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="foo"/>
                                <field name="int_field"/>
                                <field name="display_name" required="1"/>
                            </tree>
                        </field>
                    </form>
                    `,
        });

        await addRow(target);
        await editInput(target, ".o_data_row [name='int_field'] input", 1);
        await click(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_editable");
        assert.containsOnce(target, ".o_selected_row");
        assert.containsOnce(target, ".o_field_invalid");

        await editInput(target, ".o_data_row [name='foo'] input", "hello");
        await click(target, ".o_form_view");
        assert.containsOnce(target, ".o_form_editable");
        assert.containsNone(target, ".o_selected_row");
        assert.containsNone(target, ".o_field_invalid");
    });

    QUnit.test("tooltips on multiple occurrences of fields and labels", async function (assert) {
        serverData.models.partner.fields.foo.help = "foo tooltip";
        serverData.models.partner.fields.bar.help = "bar tooltip";

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
        });

        await mouseEnter(target.querySelector(".o_form_label[for=foo_0] sup"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip .o-tooltip--help").textContent,
            "foo tooltip"
        );

        await mouseEnter(target.querySelector(".o_form_label[for=bar_0] sup"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip .o-tooltip--help").textContent,
            "bar tooltip"
        );

        await mouseEnter(target.querySelector(".o_form_label[for=foo_1] sup"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip .o-tooltip--help").textContent,
            "foo tooltip"
        );

        await mouseEnter(target.querySelector(".o_form_label[for=bar_1] sup"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip .o-tooltip--help").textContent,
            "bar tooltip"
        );
    });

    QUnit.test(
        "readonly attrs on fields are re-evaluated on field change",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="foo" readonly="bar"/>
                                <field name="bar"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(
                target,
                '.o_field_widget[name="foo"]',
                "the foo field widget should be readonly"
            );
            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                '.o_field_widget[name="foo"]',
                "the foo field widget should have been rerendered to now be editable"
            );
            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                '.o_field_widget[name="foo"]',
                "the foo field widget should have been rerendered to now be readonly again"
            );
            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                '.o_field_widget[name="foo"]',
                "the foo field widget should have been rerendered to now be editable again"
            );
        }
    );

    QUnit.test("field with readonly modifier depending on id", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field" readonly="id"/>
                </form>`,
        });

        assert.containsOnce(target, ".o_form_editable");
        assert.containsOnce(target, ".o_field_widget[name=int_field] input");
        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget[name=int_field]"),
            "o_readonly_modifier"
        );

        await editInput(target, ".o_field_widget[name=int_field] input", "34");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field]").textContent,
            "34"
        );

        assert.containsOnce(target, ".o_form_editable");
        assert.containsNone(target, ".o_field_widget[name=int_field] input");
        assert.hasClass(
            target.querySelector(".o_field_widget[name=int_field]"),
            "o_readonly_modifier"
        );
    });

    QUnit.test(
        "readonly attrs on lines are re-evaluated on field change 2",
        async function (assert) {
            serverData.models.partner.records[0].product_ids = [37];
            serverData.models.partner.records[0].trululu = false;
            let onchangeApplied = false;
            serverData.models.partner.onchanges = {
                trululu(record) {
                    // when trululu changes, push another record in product_ids.
                    // only push a second record once.
                    if (!onchangeApplied) {
                        record.product_ids = [[4, 41]];
                        onchangeApplied = true;
                    }
                },
            };

            serverData.models.product.records[0].name = "test";
            // This one is necessary to have a valid, rendered widget
            serverData.models.product.fields.int_field = { type: "integer", string: "intField" };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="trululu"/>
                        <field name="product_ids" readonly="not trululu">
                            <tree editable="top"><field name="int_field" widget="handle" /><field name="name"/></tree>
                        </field>
                    </form>
                    `,
                resId: 1,
            });

            let m2oName = "first record";
            for (const value of [true, false, true, false]) {
                if (value) {
                    await selectDropdownItem(target, "trululu", m2oName);
                    assert.notOk(
                        $('.o_field_one2many[name="product_ids"]').hasClass("o_readonly_modifier"),
                        "lines should not be readonly"
                    );
                    m2oName = "second record";
                } else {
                    await editInput(target, '.o_field_many2one[name="trululu"] input', "");
                    assert.ok(
                        $('.o_field_one2many[name="product_ids"]').hasClass("o_readonly_modifier"),
                        "lines should be readonly"
                    );
                }
            }
        }
    );

    QUnit.test("empty fields have o_form_empty class in readonly mode", async function (assert) {
        serverData.models.partner.fields.foo.default = false; // no default value for this test
        serverData.models.partner.records[1].foo = false; // 1 is record with id=2
        serverData.models.partner.records[1].trululu = false; // 1 is record with id=2
        serverData.models.partner.fields.int_field.readonly = true;
        serverData.models.partner.onchanges.foo = function (obj) {
            if (obj.foo === "hello") {
                obj.int_field = false;
            }
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo"/>
                            <field name="trululu" readonly="not foo"/>
                            <field name="int_field"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(
            target,
            ".o_field_empty",
            "in edit mode, only empty readonly fields should have the o_field_empty class"
        );
        assert.containsOnce(
            target,
            ".o_form_label_empty",
            "in edit mode, only labels associated to empty readonly fields should have the o_form_label_empty class"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "test");

        assert.containsNone(
            target,
            ".o_field_empty",
            "after readonly modifier change, the o_field_empty class should have been removed"
        );
        assert.containsNone(
            target,
            ".o_form_label_empty",
            "after readonly modifier change, the o_form_label_empty class should have been removed"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "hello");

        assert.containsOnce(
            target,
            ".o_field_empty",
            "after value changed to false for a readonly field, the o_field_empty class should have been added"
        );
        assert.containsOnce(
            target,
            ".o_form_label_empty",
            "after value changed to false for a readonly field, the o_form_label_empty class should have been added"
        );
    });

    QUnit.test(
        "empty fields' labels still get the empty class after widget rerender",
        async function (assert) {
            serverData.models.partner.fields.foo.default = false; // no default value for this test
            serverData.models.partner.records[1].foo = false; // 1 is record with id=2
            serverData.models.partner.records[1].display_name = false; // 1 is record with id=2

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="foo"/>
                            <field name="display_name" readonly="foo == 'readonly'"/>
                        </group>
                    </form>`,
                resId: 2,
            });

            assert.containsNone(
                target,
                ".o_field_empty",
                "in edit mode, only empty readonly fields should have the o_field_empty class"
            );
            assert.containsNone(
                target,
                ".o_form_label_empty",
                "in edit mode, only labels associated to empty readonly fields should have the o_form_label_empty class"
            );

            await editInput(target, ".o_field_widget[name=foo] input", "readonly");
            await editInput(target, ".o_field_widget[name=foo] input", "edit");
            await editInput(target, ".o_field_widget[name=display_name] input", "some name");
            await editInput(target, ".o_field_widget[name=foo] input", "readonly");

            assert.containsNone(
                target,
                ".o_field_empty",
                "there still should not be any empty class on fields as the readonly one is now set"
            );
            assert.containsNone(
                target,
                ".o_form_label_empty",
                "there still should not be any empty class on labels as the associated readonly field is now set"
            );
        }
    );

    QUnit.test(
        'empty inner readonly fields don\'t have o_form_empty class in "create" mode',
        async function (assert) {
            serverData.models.partner.fields.product_id.readonly = true;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <group>
                                    <field name="product_id"/>
                                </group>
                            </group>
                        </sheet>
                    </form>`,
            });
            assert.containsNone(target, ".o_form_label_empty");
            assert.containsNone(target, ".o_field_empty");
        }
    );

    QUnit.test(
        "label tag added for fields have o_form_empty class in readonly mode if field is empty",
        async function (assert) {
            serverData.models.partner.fields.foo.default = false; // no default value for this test
            serverData.models.partner.records[1].foo = false; // 1 is record with id=2
            serverData.models.partner.records[1].trululu = false; // 1 is record with id=2
            serverData.models.partner.fields.int_field.readonly = true;
            serverData.models.partner.onchanges.foo = function (obj) {
                if (obj.foo === "hello") {
                    obj.int_field = false;
                }
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <label for="foo" string="Foo"/>
                            <field name="foo"/>
                            <label for="trululu" string="Trululu" readonly="not foo"/>
                            <field name="trululu" readonly="not foo"/>
                            <label for="int_field" string="IntField" readonly="not int_field"/>
                            <field name="int_field"/>
                        </sheet>
                    </form>`,
                resId: 2,
            });

            assert.containsOnce(target, ".o_field_empty");
            assert.containsOnce(target, ".o_form_label_empty");

            await editInput(target, "div[name=foo] input", "test");

            assert.containsNone(target, ".o_field_empty");
            assert.containsNone(target, ".o_form_label_empty");

            await editInput(target, "div[name=foo] input", "hello");

            assert.containsOnce(target, ".o_field_empty");
            assert.containsOnce(target, ".o_form_label_empty");
        }
    );

    QUnit.test(
        "required attrs on fields are re-evaluated on field change",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="foo" required="bar"/>
                                <field name="bar"/>
                            </group>
                        </sheet>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(
                target,
                '.o_field_widget[name="foo"].o_required_modifier',
                "the foo field widget should be required"
            );
            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                '.o_field_widget[name="foo"]:not(.o_required_modifier)',
                "the foo field widget should now have been marked as non-required"
            );
            await click(target.querySelector(".o_field_boolean input"));
            assert.containsOnce(
                target,
                '.o_field_widget[name="foo"].o_required_modifier',
                "the foo field widget should now have been marked as required again"
            );
        }
    );

    QUnit.test("required fields should have o_required_modifier", async function (assert) {
        serverData.models.partner.fields.foo.required = true;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.containsOnce(target, ".o_field_widget.o_required_modifier");
    });

    QUnit.test("required float fields works as expected", async function (assert) {
        serverData.models.partner.fields.qux.required = true;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="qux"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.hasClass(target.querySelector('.o_field_widget[name="qux"]'), "o_required_modifier");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="qux"] input').value,
            "0.0",
            "qux input is 0 by default (float field)"
        );

        await clickSave(target);

        await editInput(target, ".o_field_widget[name=qux] input", "1");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector('.o_field_widget[name="qux"] input').value,
            "1.0",
            "qux input is properly formatted"
        );

        assert.verifySteps(["get_views", "onchange", "web_save", "web_save"]);
    });

    QUnit.test("separators", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                    <group>
                        <separator string="Geolocation"/>
                        <field name="foo"/>
                    </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, "div.o_horizontal_separator");
    });

    QUnit.test("invisible attrs on separators", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <separator string="Geolocation" invisible='bar'/>
                            <field name="bar"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsNone(target, "div.o_horizontal_separator");
    });

    QUnit.test("form views in dialogs do not have a control panel", async function (assert) {
        serverData.views = {
            "partner,false,form": `<form><field name="foo"/></form>`,
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                target: "new",
            },
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.containsNone(target, ".o_dialog .o_form_view .o_control_panel");
    });

    QUnit.test("form views in dialogs do not add display_name field", async function (assert) {
        assert.expect(3);

        serverData.views = {
            "partner,false,form": `<form><field name="foo"/></form>`,
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                target: "new",
            },
        };
        const mockRPC = function (route, args) {
            if (args.method === "onchange") {
                assert.deepEqual(args.args[3], { foo: {} });
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.containsNone(target, ".o_dialog .o_form_view .o_control_panel");
    });

    QUnit.test("form views in dialogs closes on save", async function (assert) {
        serverData.models.partner.records[0].foo = undefined;
        delete serverData.models.partner.fields.foo.default;
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="foo" required="1"/>
                </form>`,
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                target: "new",
            },
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_dialog .o_form_view", "the dialog has been opened");

        await click(target.querySelector(".o_dialog .o_form_button_save"));
        assert.containsOnce(
            target,
            ".o_dialog .o_form_view",
            "the dialog is still opened as save failed"
        );

        editInput(target, "[name='foo'] input", "Gizmo");
        await click(target.querySelector(".o_dialog .o_form_button_save"));
        assert.containsNone(target, ".o_dialog .o_form_view", "the dialog has been closed");
    });

    QUnit.test(
        "form views in dialogs closes on discard on existing record",
        async function (assert) {
            serverData.models.partner.records[0].foo = undefined;
            delete serverData.models.partner.fields.foo.default;
            serverData.views = {
                "partner,false,form": `
                <form>
                    <field name="foo" required="1"/>
                </form>`,
            };
            serverData.actions = {
                1: {
                    id: 1,
                    name: "Partner",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                    target: "new",
                    res_id: 1,
                },
            };
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);
            assert.containsOnce(target, ".o_dialog .o_form_view", "the dialog has been opened");

            await click(target.querySelector(".o_dialog .o_form_button_cancel"));
            assert.containsNone(target, ".o_dialog .o_form_view", "the dialog has been closed");
        }
    );

    QUnit.test("form views in dialogs do not have class o_xxl_form_view", async function (assert) {
        const bus = new EventBus();
        registry.category("services").add("ui", {
            start(env) {
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
            },
        });
        serverData.views = {
            "partner,false,form": `<form><field name="foo"/></form>`,
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                target: "new",
            },
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_dialog .o_form_view");
        assert.doesNotHaveClass(target.querySelector(".o_dialog .o_form_view"), "o_xxl_form_view");
    });

    QUnit.test("buttons in form view", async function (assert) {
        assert.expect(12);
        assert.expectErrors();

        const mockedActionService = {
            start() {
                return {
                    doActionButton(params) {
                        assert.step(params.name);
                        if (params.name === "post") {
                            assert.strictEqual(params.resId, 2);
                            params.onClose();
                        } else {
                            throw makeServerError();
                        }
                    },
                };
            },
        };
        serviceRegistry.add("action", mockedActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="state" invisible="1"/>
                    <header>
                        <button name="post" class="p" string="Confirm" type="object"/>
                        <button name="some_method" class="s" string="Do it" type="object"/>
                        <button name="some_other_method" invisible="state not in ['ab', 'ef']" string="Do not" type="object"/>
                    </header>
                    <sheet>
                        <group>
                            <button string="Geolocate" name="geo_localize" icon="fa-check" type="object"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });
        assert.containsOnce(target, "button.btn i.fa.fa-check");
        assert.containsN(target, ".o_form_statusbar button", 2);
        assert.containsOnce(target, 'button.p[name="post"]:contains(Confirm)');

        // click on p (will succeed and reload)
        await click(target.querySelector(".o_form_statusbar button.p"));
        assert.verifyErrors([]);

        // click on s (will fail)
        await click(target.querySelector(".o_form_statusbar button.s"));

        assert.verifySteps([
            "get_views",
            "web_read", // initial read
            "post",
            "web_read", // reload (successfully clicked on p)
            "some_method",
        ]);
        assert.verifyErrors(["Odoo Server Error"]);
    });

    QUnit.test("buttons classes in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
        });

        assert.strictEqual(target.querySelector('button[name="0"]').className, "btn btn-secondary");
        assert.strictEqual(target.querySelector('button[name="1"]').className, "btn btn-primary");
        assert.strictEqual(target.querySelector('button[name="2"]').className, "btn btn-primary");
        assert.strictEqual(target.querySelector('button[name="3"]').className, "btn btn-secondary");
        assert.strictEqual(target.querySelector('button[name="4"]').className, "btn btn-link");
        assert.strictEqual(target.querySelector('button[name="5"]').className, "btn btn-link");
        assert.strictEqual(target.querySelector('button[name="6"]').className, "btn btn-success");
        assert.strictEqual(
            target.querySelector('button[name="7"]').className,
            "btn o_this_is_a_button btn-secondary"
        );
        assert.strictEqual(target.querySelector('button[name="8"]').className, "btn btn-secondary");
        assert.strictEqual(target.querySelector('button[name="9"]').className, "btn btn-primary");
        assert.strictEqual(target.querySelector('button[name="10"]').className, "btn btn-primary");
        assert.strictEqual(
            target.querySelector('button[name="11"]').className,
            "btn btn-secondary"
        );
        assert.strictEqual(target.querySelector('button[name="12"]').className, "btn btn-link");
        assert.strictEqual(target.querySelector('button[name="13"]').className, "btn btn-link");
        assert.strictEqual(target.querySelector('button[name="14"]').className, "btn btn-success");
        assert.strictEqual(
            target.querySelector('button[name="15"]').className,
            "btn o_this_is_a_button"
        );
    });

    QUnit.test("nested buttons in form view header", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="0"/>
                        <button name="1"/>
                        <div>
                            <button name="2"/>
                            <button name="3"/>
                        </div>
                    </header>
                </form>`,
            resId: 2,
        });

        const buttons = target.querySelectorAll(".o_form_statusbar button");
        assert.strictEqual(buttons[0].attributes.name.textContent, "0");
        assert.strictEqual(buttons[1].attributes.name.textContent, "1");
        assert.strictEqual(buttons[2].attributes.name.textContent, "2");
        assert.strictEqual(buttons[3].attributes.name.textContent, "3");
    });

    QUnit.test("button in form view and long willStart", async function (assert) {
        const mockedActionService = {
            start() {
                return {
                    doActionButton(params) {
                        params.onClose();
                    },
                };
            },
        };
        serviceRegistry.add("action", mockedActionService, { force: true });

        let rpcCount = 0;
        class AsyncField extends CharField {
            setup() {
                onWillStart(async () => {
                    assert.step("willStart");
                });
                onWillUpdateProps(async () => {
                    assert.step("willUpdateProps");
                    if (rpcCount === 1) {
                        return new Promise(() => {});
                    }
                });
            }
        }
        fieldRegistry.add("asyncwidget", { component: AsyncField });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="state" invisible="1"/>
                    <header>
                        <button name="post" class="p" string="Confirm" type="object"/>
                    </header>
                    <sheet>
                        <group>
                            <field name="foo" widget="asyncwidget"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method !== "get_views") {
                    rpcCount++;
                    assert.step(args.method + rpcCount);
                }
            },
        });
        assert.verifySteps(["web_read1", "willStart"]);

        await click(target.querySelector(".o_form_statusbar button.p"));
        assert.verifySteps(["web_read2", "willUpdateProps"]);

        await click(target.querySelector(".o_form_statusbar button.p"));
        assert.verifySteps(["web_read3", "willUpdateProps"]);
    });

    QUnit.test("buttons in form view, new record", async function (assert) {
        // this test simulates a situation similar to the settings forms.
        assert.expect(8);

        serverData.models.partner.records = []; // such that we know the created record will be id 1
        const mockedActionService = {
            start() {
                return {
                    doActionButton(params) {
                        assert.step("execute_action");
                        assert.deepEqual(
                            params.resId,
                            1,
                            "execute action should be done on correct record id"
                        );
                        params.onClose();
                    },
                };
            },
        };
        serviceRegistry.add("action", mockedActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="post" class="p" string="Confirm" type="object"/>
                        <button name="some_method" class="s" string="Do it" type="object"/>
                    </header>
                    <sheet>
                        <group>
                            <button string="Geolocate" name="geo_localize" icon="fa-check" type="object"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.verifySteps(["get_views", "onchange"]);

        await click(target.querySelector(".o_form_statusbar button.p"));

        assert.verifySteps(["web_save", "execute_action", "web_read"]);
    });

    QUnit.test("buttons in form view, new record, with field id in view", async function (assert) {
        assert.expect(7);
        // buttons in form view are one of the rare example of situation when we
        // save a record without reloading it immediately, because we only care
        // about its id for the next step.  But at some point, if the field id
        // is in the view, it was registered in the changes, and caused invalid
        // values in the record (data.id was set to null)

        serverData.models.partner.records = []; // such that we know the created record will be id 1
        const mockedActionService = {
            start() {
                return {
                    doActionButton(params) {
                        assert.step("execute_action");
                        assert.deepEqual(
                            params.resId,
                            1,
                            "execute action should be done on correct record id"
                        );
                        params.onClose();
                    },
                };
            },
        };
        serviceRegistry.add("action", mockedActionService, { force: true });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="post" class="p" string="Confirm" type="object"/>
                    </header>
                    <sheet>
                        <group>
                            <field name="id" invisible="1"/>
                            <field name="foo"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        await click(target.querySelector(".o_form_statusbar button.p"));

        assert.verifySteps(["get_views", "onchange", "web_save", "execute_action", "web_read"]);
    });

    QUnit.test("buttons with data-hotkey attribute", async function (assert) {
        const mockedActionService = {
            start() {
                return {
                    doActionButton(params) {
                        assert.step(params.name);
                    },
                };
            },
        };
        serviceRegistry.add("action", mockedActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <button name="validate" string="Validate" type="object" data-hotkey="v"/>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, ".o_form_view button[data-hotkey=v]");
        triggerHotkey("alt+v");
        await nextTick();
        assert.verifySteps(["validate"]);
    });

    QUnit.test("change and save char", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><group><field name="foo"/></group></form>',
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.ok(true, "should call the web_save route");
                    assert.strictEqual(args.args[1].foo, "tralala");
                }
            },
            resId: 2,
        });

        assert.containsOnce(target, ".o_form_editable", "form view should be in edit mode");
        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        await clickSave(target);
    });

    QUnit.test("properly reload data from server", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><group><field name="foo"/></group></form>',
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    args.args[1].foo = "apple";
                }
            },
            resId: 2,
        });

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        await clickSave(target);
        assert.strictEqual(target.querySelector(".o_field_widget[name=foo] input").value, "apple");
    });

    QUnit.test("disable buttons until reload data from server", async function (assert) {
        let def = undefined;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><group><field name="foo"/></group></form>',
            async mockRPC(route, args) {
                if (args.method === "web_save") {
                    args.args[1].foo = "apple";
                    // Block the 'read' call
                    await Promise.resolve(def);
                }
            },
            resId: 2,
        });

        def = makeDeferred();
        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        await clickSave(target);

        // Save button should be disabled
        assert.hasAttrValue(target.querySelector(".o_form_button_save"), "disabled", "disabled");
        assert.hasAttrValue(target.querySelector(".o_form_button_cancel"), "disabled", "disabled");
        // Release the 'read' call
        def.resolve();
        await nextTick();

        // Save button should be enabled after the reload
        assert.hasAttrValue(target.querySelector(".o_form_button_save"), "disabled", undefined);
        assert.hasAttrValue(target.querySelector(".o_form_button_cancel"), "disabled", undefined);
    });

    QUnit.test("properly apply onchange in simple case", async function (assert) {
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/><field name="int_field"/></form>',
            resId: 2,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "9",
            "should contain input with initial value"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "1007",
            "should contain input with onchange applied"
        );
    });

    QUnit.test(
        "properly apply onchange when changed field is active field",
        async function (assert) {
            serverData.models.partner.onchanges = {
                int_field: function (obj) {
                    obj.int_field = 14;
                },
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="int_field"/></form>',
                resId: 2,
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=int_field] input").value,
                "9",
                "should contain input with initial value"
            );

            await editInput(target, ".o_field_widget[name=int_field] input", "666");

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=int_field] input").value,
                "14",
                "value should have been set to 14 by onchange"
            );

            await clickSave(target);

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=int_field] input").value,
                "14",
                "value should still be 14"
            );
        }
    );

    QUnit.test("onchange send only the present fields to the server", async function (assert) {
        assert.expect(1);
        serverData.models.partner.records[0].product_id = false;
        serverData.models.partner.onchanges.foo = (obj) => {
            obj.foo = obj.foo + " alligator";
        };
        serverData.views = {
            "partner_type,false,list": '<tree><field name="name"/></tree>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="p" widget="one2many">
                        <tree>
                            <field name="bar"/>
                            <field name="product_id"/>
                        </tree>
                    </field>
                    <field name="timmy"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(
                        args.args[3],
                        {
                            display_name: {},
                            foo: {},
                            p: {
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
                            timmy: {
                                fields: {
                                    name: {},
                                },
                                limit: 40,
                                order: "",
                            },
                        },
                        "should send only the fields used in the views"
                    );
                }
            },
        });

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
    });

    QUnit.test("onchange only send present fields value", async function (assert) {
        assert.expect(1);

        serverData.models.partner.onchanges.foo = () => {};

        let checkOnchange = false;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="display_name"/>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="qux"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "onchange" && checkOnchange) {
                    assert.deepEqual(
                        args.args[1],
                        {
                            foo: "tralala",
                            p: [
                                [
                                    0,
                                    args.args[1].p[0][1],
                                    { display_name: "valid line", qux: 12.4 },
                                ],
                            ],
                        },
                        "should send the values for the present fields"
                    );
                }
            },
        });

        // add a o2m row
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await editInput(
            target,
            ".o_field_one2many .o_field_widget[name=display_name] input",
            "valid line"
        );
        await editInput(target, ".o_field_one2many .o_field_widget[name=qux] input", "12.4");

        // trigger an onchange by modifying foo
        checkOnchange = true;
        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
    });

    QUnit.test("evaluate in python field options", async function (assert) {
        assert.expect(3);

        class MyField extends Component {
            setup() {
                assert.strictEqual(this.props.horizontal, true);
            }
        }
        MyField.template = xml`<div>ok</div>`;
        fieldRegistry.add("my_field", {
            component: MyField,
            extractProps: function ({ options }) {
                assert.deepEqual(options, { horizontal: true });
                return { horizontal: options.horizontal };
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" widget="my_field" options="{'horizontal': True}"/>
                </form>`,
            resId: 2,
        });

        assert.strictEqual(target.querySelector(".o_field_widget").textContent, "ok");
    });

    QUnit.test("can create a record with default values", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="bar"/>
                </form>`,
            resId: 1,
            context: { active_field: 2 },
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.strictEqual(
                        args.kwargs.context.active_field,
                        2,
                        "should have send the correct context"
                    );
                }
            },
        });

        const n = serverData.models.partner.records.length;

        await createRecord();
        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(
            target.querySelector(".o_field_char input").value,
            "My little Foo Value"
        );

        await clickSave(target);
        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(serverData.models.partner.records.length, n + 1);
    });

    QUnit.test(
        "default record with a one2many and an onchange on sub field",
        async function (assert) {
            serverData.models.partner.onchanges.foo = function () {};

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p" widget="one2many">
                            <tree><field name="foo"/></tree>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "onchange") {
                        assert.deepEqual(
                            args.args[3],
                            {
                                display_name: {},
                                p: {
                                    fields: {
                                        foo: {},
                                    },
                                    limit: 40,
                                    order: "",
                                },
                            },
                            "onchangeSpec should be correct (with sub fields)"
                        );
                    }
                },
            });
            assert.verifySteps(["get_views", "onchange"]);
        }
    );

    QUnit.test("remove default value in subviews", async function (assert) {
        assert.expect(2);

        serverData.models.product.onchanges = {};
        serverData.models.product.onchanges.name = function () {};
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            context: { default_state: "ab" },
            arch: `
                <form>
                    <field name="product_ids" context="{'default_product_uom_qty': 68}">
                        <tree editable="top">
                            <field name="name"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC: function (route, args) {
                if (route === "/web/dataset/call_kw/partner/onchange") {
                    assert.deepEqual(args.kwargs.context, {
                        default_state: "ab",
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                } else if (route === "/web/dataset/call_kw/product/onchange") {
                    assert.deepEqual(args.kwargs.context, {
                        default_product_uom_qty: 68,
                        lang: "en",
                        tz: "taht",
                        uid: 7,
                    });
                }
            },
        });
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
    });

    QUnit.test("form with one2many with dynamic context", async (assert) => {
        assert.expect(2);
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field"/>
                    <field name="p" editable="bottom" context="{'static': 4, 'dynamic': int_field * 2}">
                        <tree>
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_read") {
                    assert.deepEqual(args.kwargs.specification, {
                        display_name: {},
                        int_field: {},
                        p: {
                            fields: {
                                foo: {},
                            },
                            context: { static: 4 },
                            limit: 40,
                            order: "",
                        },
                    });
                }
                if (args.method === "onchange") {
                    assert.deepEqual(args.kwargs.context, {
                        dynamic: 20,
                        lang: "en",
                        static: 4,
                        tz: "taht",
                        uid: 7,
                    });
                }
            },
        });

        await addRow(target);
    });

    QUnit.test("reference field in one2many list", async function (assert) {
        serverData.models.partner.records[0].reference = "partner,2";
        serverData.views = {
            "partner,false,form": '<form><field name="display_name"/></form>',
        };

        await makeViewInDialog({
            type: "form",
            resModel: "user",
            serverData,
            arch: `
                <form>
                    <field name="name"/>
                    <field name="partner_ids">
                        <tree editable="bottom">
                            <field name="display_name"/>
                            <field name="reference"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
            },
            resId: 17,
        });
        // current form

        // open the modal form view of the record pointed by the reference field
        await click(target.querySelector('table td[data-tooltip="first record"]'));
        await click(target.querySelector("table td button.o_external_button"));

        // edit the record in the modal
        await editInput(
            target,
            '.o_dialog:not(.o_inactive_modal) .o_field_widget[name="display_name"] input',
            "New name"
        );
        await click(
            target.querySelector(".o_dialog:not(.o_inactive_modal) footer .o_form_button_save")
        );

        assert.containsOnce(
            target,
            '.o_field_cell[data-tooltip="New name"]',
            "should not crash and value must be edited"
        );
    });

    QUnit.test("there is an Actions menu when creating a new record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            actionMenus: {},
            resId: 1,
        });

        assert.containsOnce(target, ".o_cp_action_menus");

        await createRecord();

        assert.containsOnce(target, ".o_cp_action_menus");

        await clickSave(target);

        assert.containsOnce(target, ".o_cp_action_menus");
    });

    QUnit.test("basic default record", async function (assert) {
        serverData.models.partner.fields.foo.default = "default foo value";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.strictEqual(target.querySelector("input").value, "default foo value");
        assert.verifySteps(["get_views", "onchange"]);
    });

    QUnit.test("make default record with non empty one2many", async function (assert) {
        serverData.models.partner.fields.p.default = [
            [6, 0, []], // replace with zero ids
            [0, 0, { foo: "new foo1", product_id: 41, p: [] }], // create a new value
            [0, 0, { foo: "new foo2", product_id: 37, p: [] }], // create a new value
        ];

        let nameGetCount = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <field name="product_id"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (
                    args.method === "read" &&
                    args.args[1].length === 1 &&
                    args.args[1][0] === "display_name"
                ) {
                    nameGetCount++;
                }
            },
        });
        assert.containsOnce(
            target,
            "td:contains(new foo1)",
            "should have new foo1 value in one2many"
        );
        assert.containsOnce(
            target,
            "td:contains(new foo2)",
            "should have new foo2 value in one2many"
        );
        assert.containsOnce(
            target,
            "td:contains(xphone)",
            "should have a cell with the name field 'product_id', set to xphone"
        );
        assert.strictEqual(nameGetCount, 0, "should have done no nameget");
    });

    QUnit.test("make default record with non empty many2one", async function (assert) {
        serverData.models.partner.fields.trululu.default = 4;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="trululu"/></form>',
            mockRPC(route, args) {
                if (
                    args.method === "read" &&
                    args.args[1].length === 1 &&
                    args.args[1][0] === "display_name"
                ) {
                    throw new Error("Should not call display_name read");
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=trululu] input").value,
            "aaa",
            "default value should be correctly displayed"
        );
        assert.verifySteps([]);
    });

    QUnit.test("form view properly change its title", async function (assert) {
        serverData.views = {
            "partner,false,form": '<form><field name="foo"/></form>',
            "partner,false,search": "<search/>",
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                res_id: 1,
            },
        };

        const target = getFixture();
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "first record",
            "should have the display name of the record as title"
        );
        await createRecord();
        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "New",
            "should have the display name of the record as title"
        );
    });

    QUnit.test("archive/unarchive a record", async function (assert) {
        // add active field on partner model to have archive option
        serverData.models.partner.fields.active = { string: "Active", type: "char", default: true };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            actionMenus: {},
            arch: '<form><field name="active"/><field name="foo"/></form>',
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.containsOnce(target, ".o_cp_action_menus");

        await toggleActionMenu(target);
        assert.containsOnce(target, ".o_cp_action_menus span:contains(Archive)");

        await toggleMenuItem(target, "Archive");
        assert.containsOnce(document.body, ".modal");

        await click(document.body.querySelector(".modal-footer .btn-primary"));

        await toggleActionMenu(target);
        assert.containsOnce(target, ".o_cp_action_menus span:contains(Unarchive)");

        await toggleMenuItem(target, "UnArchive");

        await toggleActionMenu(target);
        assert.containsOnce(target, ".o_cp_action_menus span:contains(Archive)");

        assert.verifySteps([
            "get_views",
            "web_read",
            "action_archive",
            "web_read",
            "action_unarchive",
            "web_read",
        ]);
    });

    QUnit.test("apply custom standard action menu (archive)", async function (assert) {
        // add active field on partner model to have archive option
        serverData.models.partner.fields.active = { string: "Active", type: "char", default: true };

        const formView = registry.category("views").get("form");
        class CustomFormController extends formView.Controller {
            getStaticActionMenuItems() {
                const menuItems = super.getStaticActionMenuItems();
                menuItems.archive.callback = () => {
                    assert.step("customArchive");
                };
                return menuItems;
            }
        }
        registry.category("views").add("custom_form", {
            ...formView,
            Controller: CustomFormController,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            actionMenus: {},
            arch: `
                <form js_class="custom_form">
                        <field name="active"/>
                        <field name="foo"/>
                </form>`,
        });

        assert.containsOnce(target, ".o_cp_action_menus");

        await toggleActionMenu(target);
        assert.containsOnce(target, ".o_cp_action_menus span:contains(Archive)");

        await toggleMenuItem(target, "Archive");
        assert.verifySteps(["customArchive"]);
    });

    QUnit.test("add custom static action menu", async function (assert) {
        const formView = registry.category("views").get("form");
        class CustomFormController extends formView.Controller {
            getStaticActionMenuItems() {
                const menuItems = super.getStaticActionMenuItems();
                menuItems.customAvailable = {
                    isAvailable: () => true,
                    description: "Custom Available",
                    sequence: 35,
                    callback: () => {
                        assert.step("Custom Available");
                    },
                };
                menuItems.customNotAvailable = {
                    isAvailable: () => false,
                    description: "Custom Not Available",
                    callback: () => {
                        assert.step("Custom Not Available");
                    },
                };
                menuItems.customDefaultAvailable = {
                    description: "Custom Default Available",
                    callback: () => {
                        assert.step("Custom Default Available");
                    },
                };
                return menuItems;
            }
        }
        registry.category("views").add("custom_form", {
            ...formView,
            Controller: CustomFormController,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            actionMenus: {},
            arch: `
                <form js_class="custom_form">
                        <field name="foo"/>
                </form>`,
        });

        assert.containsOnce(target, ".o_cp_action_menus");

        await toggleActionMenu(target);
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_cp_action_menus .dropdown-item")),
            ["Custom Default Available", "Duplicate", "Custom Available", "Delete"]
        );

        await toggleMenuItem(target, "Custom Available");
        assert.verifySteps(["Custom Available"]);

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Custom Default Available");
        assert.verifySteps(["Custom Default Available"]);
    });

    QUnit.test("archive a record with intermediary action", async function (assert) {
        // add active field on partner model to have archive option
        serverData.models.partner.fields.active = { string: "Active", type: "char", default: true };

        serverData.views = {
            "product,false,search": `<search />`,
            "product,false,form": `
                <form>
                    <field name="display_name" />
                    <footer>
                        <button type="object" name="do_archive" class="myButton" />
                    </footer>
                </form>`,
            "partner,false,search": `<search />`,
            "partner,false,form": '<form><field name="active"/><field name="foo"/></form>',
        };

        let readPartner = 0;
        const webClient = await createWebClient({
            serverData,
            mockRPC(route, args) {
                assert.step(`${args.method || route}${args.method ? ": " + args.model : ""}`);
                if (args.method === "action_archive") {
                    return {
                        type: "ir.actions.act_window",
                        res_model: "product",
                        target: "new",
                        views: [[false, "form"]],
                    };
                }
                if (args.method === "do_archive") {
                    return false;
                }
                if (args.method === "web_read" && args.model === "partner") {
                    if (readPartner === 1) {
                        return [{ id: 1, active: "archived" }];
                    }
                    readPartner++;
                }
            },
        });

        await doAction(webClient, {
            type: "ir.actions.act_window",
            res_model: "partner",
            res_id: 1,
            views: [[false, "form"]],
        });

        assert.strictEqual(target.querySelector("[name='active'] input").value, "true");
        assert.verifySteps([
            "/web/webclient/load_menus",
            "get_views: partner",
            "web_read: partner",
        ]);
        await toggleActionMenu(target);
        assert.containsOnce(target, ".o_cp_action_menus span:contains(Archive)");

        await toggleMenuItem(target, "Archive");
        assert.containsOnce(document.body, ".modal");
        assert.verifySteps([]);
        await click(document.body.querySelector(".modal-footer .btn-primary"));
        assert.verifySteps(["action_archive: partner", "get_views: product", "onchange: product"]);
        await click(target, ".modal footer .myButton");
        assert.verifySteps(["web_save: product", "do_archive: product", "web_read: partner"]);
        assert.containsNone(target, ".modal");
        assert.strictEqual(target.querySelector("[name='active'] input").value, "archived");
    });

    QUnit.test("archive action with active field not in view", async function (assert) {
        // add active field on partner model, but do not put it in the view
        serverData.models.partner.fields.active = { string: "Active", type: "char", default: true };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            actionMenus: {},
            arch: '<form><field name="foo"/></form>',
        });

        assert.containsOnce(target, ".o_cp_action_menus");

        await toggleActionMenu(target);
        assert.containsNone(target, ".o_cp_action_menus span:contains(Archive)");
        assert.containsNone(target, ".o_cp_action_menus span:contains(Unarchive)");
    });

    QUnit.test("archive action not shown with readonly active field", async function (assert) {
        // add active field on partner model in readonly mode to do not have Archive option
        serverData.models.partner.fields.active = {
            string: "Active",
            type: "char",
            default: true,
            readonly: true,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="active"/><field name="foo"/></form>`,
            actionMenus: {},
        });
        await click(target, ".o_cp_action_menus .dropdown-toggle");
        assert.deepEqual(
            [...target.querySelectorAll(".o_menu_item")].map((el) => el.textContent),
            ["Duplicate", "Delete"],
            "Should not contain an Archive action"
        );
    });

    QUnit.test("can duplicate a record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            resId: 1,
            actionMenus: {},
        });

        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "first record",
            "should have the display name of the record as title"
        );

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Duplicate");

        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "first record (copy)",
            "should have duplicated the record"
        );
        assert.containsOnce(target, ".o_form_editable");
    });

    QUnit.test("duplicating a record preserves the context", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            resId: 1,
            actionMenus: {},
            context: { hey: "hoy" },
            mockRPC(route, args) {
                if (args.method === "web_read") {
                    assert.step(args.kwargs.context.hey);
                }
            },
        });

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Duplicate");

        // should have 2 read, one for initial load, second for read after duplicating
        assert.verifySteps(["hoy", "hoy"]);
    });

    QUnit.test("cannot duplicate a record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form duplicate="false"><field name="foo"/></form>',
            resId: 1,
            actionMenus: {},
        });

        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "first record",
            "should have the display name of the record as title"
        );
        assert.containsOnce(target, ".o_cp_action_menus");
        await toggleActionMenu(target);
        assert.containsNone(
            target,
            ".o_cp_action_menus span:contains(Duplicate)",
            "should not contains a 'Duplicate' action"
        );
    });

    QUnit.test("don't duplicate if save fail", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            actionMenus: {},
            async mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.step("web_save");
                    throw makeServerError();
                }
                if (args.method === "copy") {
                    assert.step("copy");
                }
            },
        });
        await editInput(target, "[name=foo] input", "new value");
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Duplicate");
        assert.containsOnce(target, ".modal .o_error_dialog");
        // Discard changes don't trigger Duplicate action
        await click(target, ".modal .btn-secondary");

        assert.verifySteps(["web_save"]);
    });

    QUnit.test(
        "editing a translatable field in a duplicate record overrides translations",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="display_name"/></form>',
                resId: 1,
                actionMenus: {},
                async mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.step("web_save");
                    }
                    if (args.method === "web_override_translations") {
                        assert.deepEqual(args.args[1], { display_name: "first record (test)" });
                        assert.step("web_override_translations");
                        return true;
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_control_panel .o_breadcrumb").textContent,
                "first record",
                "should have the display name of the record as title"
            );

            await toggleActionMenu(target);
            await toggleMenuItem(target, "Duplicate");

            assert.strictEqual(
                target.querySelector(".o_control_panel .o_breadcrumb").textContent,
                "first record (copy)",
                "should have duplicated the record"
            );
            assert.containsOnce(target, ".o_form_editable");
            await editInput(target, ".o_field_char input", "first record (test)");
            await click(target, ".o_form_button_save");
            assert.verifySteps(["web_save", "web_override_translations"]);
        }
    );

    QUnit.test("clicking on stat buttons in edit mode", async function (assert) {
        let count = 0;
        const fakeActionService = {
            start() {
                return {
                    doActionButton() {
                        count++;
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.strictEqual(
                        args.args[1].foo,
                        "tralala",
                        "should have saved the changes"
                    );
                }
                assert.step(args.method);
            },
        });

        await click(target.querySelector(".oe_stat_button"));
        assert.strictEqual(count, 1, "should have triggered a execute action");
        assert.containsOnce(target, ".o_form_editable", "form view should be in edit mode");

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        await click(target.querySelector(".oe_stat_button"));

        assert.containsOnce(target, ".o_form_editable", "form view should be in edit mode");
        assert.strictEqual(count, 2, "should have triggered a execute action");
        assert.verifySteps(["get_views", "web_read", "web_save"]);
    });

    QUnit.test("clicking on stat buttons save and reload in edit mode", async function (assert) {
        const fakeActionService = {
            start() {
                return {
                    doActionButton() {},
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    // simulate an override of the model...
                    args.args[1].display_name = "GOLDORAK";
                    args.args[1].name = "GOLDORAK";
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "second record",
            "should have correct display_name"
        );
        await editInput(target, ".o_field_widget[name=name] input", "some other name");
        await click(target.querySelector(".oe_stat_button"));
        assert.strictEqual(
            target.querySelector(".o_control_panel .o_breadcrumb").textContent,
            "GOLDORAK",
            "should have correct display_name"
        );
    });

    QUnit.test('buttons with attr "special" do not trigger a save', async function (assert) {
        let writeCount = 0;
        let doActionButtonCount = 0;
        const fakeActionService = {
            start() {
                return {
                    doActionButton() {
                        doActionButtonCount++;
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <button string="Do something" class="btn-primary" name="abc" type="object"/>
                    <button string="Or discard" class="btn-secondary" special="cancel"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    writeCount++;
                }
            },
        });

        // make the record dirty
        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        await click(target.querySelector(".o_content button.btn-primary"));

        assert.strictEqual(writeCount, 1, "should have triggered a write");
        assert.strictEqual(doActionButtonCount, 1, "should have triggered a execute action");

        await editInput(target, ".o_field_widget[name=foo] input", "abcdef");

        await click(target.querySelector(".o_content button.btn-secondary"));
        assert.strictEqual(writeCount, 1, "should not have triggered a write");
        assert.strictEqual(doActionButtonCount, 2, "should have triggered a execute action");
    });

    QUnit.test('buttons with attr "special=save" save', async function (assert) {
        const fakeActionService = {
            start() {
                return {
                    doActionButton() {
                        assert.step("execute_action");
                    },
                };
            },
        };
        serviceRegistry.add("action", fakeActionService, { force: true });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <button string="Save" class="btn-primary" special="save"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        await click(target.querySelector(".o_content button.btn-primary"));
        assert.verifySteps(["get_views", "web_read", "web_save", "execute_action"]);
    });

    QUnit.test('buttons with attr "special" in dialog close the dialog', async function (assert) {
        serverData.views = {
            "product,false,form": `
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

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `
                <form>
                    <sheet><group>
                    <field name="product_id"/>
                    </group></sheet>
                </form>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return false;
                }
                if (route === "/web/dataset/call_kw/product/web_save") {
                    assert.step("create RPC");
                }
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.step("write RPC");
                }
            },
        });

        await editInput(target, "[name=product_id] input", "ABC");
        await clickOpenM2ODropdown(target, "product_id");
        await clickOpenedDropdownItem(target, "product_id", "Create and edit...");
        assert.containsOnce(target, ".o_dialog", "dialog is present to create the product");

        await editInput(target, ".o_field_widget[name=name] input", "ABCDE");
        await click(target.querySelector("button[special=save]"));
        assert.containsNone(target, ".o_dialog", "dialog has been closed");
        assert.verifySteps(["create RPC"], "create RPC has been made");
        assert.strictEqual(
            target.querySelector("[name=product_id] input").value,
            "ABCDE",
            "value has been set correctly"
        );
        assert.containsOnce(
            target,
            ".o_form_status_indicator_buttons:not(.invisible)",
            "form view is dirty"
        );

        await click(target.querySelector(".o_form_button_save"));
        assert.verifySteps(["write RPC"], "write RPC has been made");

        await editInput(target, "[name=product_id] input", "XYZ");
        await clickOpenM2ODropdown(target, "product_id");
        await clickOpenedDropdownItem(target, "product_id", "Create and edit...");
        await click(target.querySelector("button[special=cancel]"));
        assert.containsNone(target, ".o_dialog", "dialog has been closed");
        assert.verifySteps([], "no create RPC has been made");
        assert.containsOnce(
            target,
            ".o_form_status_indicator_buttons.invisible",
            "form view is not dirty"
        );
    });

    QUnit.test("missing widgets do not crash", async function (assert) {
        serverData.models.partner.fields.foo.type = "new field type without widget";
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            resId: 1,
        });
        assert.containsOnce(target, ".o_field_widget");
    });

    QUnit.test("nolabel", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <group class="firstgroup">
                                <field name="foo" nolabel="1"/>
                            </group>
                            <group class="secondgroup">
                                <field name="product_id"/>
                                <field name="int_field" nolabel="1"/><field name="qux" nolabel="1"/>
                            </group>
                            <group>
                                <field name="bar"/>
                            </group>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsN(target, "label.o_form_label", 2);
        assert.strictEqual(
            target.querySelectorAll("label.o_form_label")[0].textContent,
            "Product",
            "one should be the one for the product field"
        );
        assert.strictEqual(
            target.querySelectorAll("label.o_form_label")[1].textContent,
            "Bar",
            "one should be the one for the bar field"
        );

        assert.hasAttrValue(
            target.querySelector(".firstgroup div"),
            "style",
            undefined,
            "foo div should have a default colspan (1)"
        );
        assert.containsN(
            target,
            ".secondgroup div.o_wrap_field",
            2,
            "int_field and qux should have same o_wrap_field"
        );

        assert.containsN(
            target,
            ".secondgroup div.o_wrap_field:first div.o_cell",
            2,
            "product_id field should be on its own o_wrap_field"
        );
    });

    QUnit.test("many2one in a one2many", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        serverData.models.partner.records[1].product_id = 37;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="product_id"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            "td:contains(xphone)",
            "should display the name of the many2one"
        );
    });

    QUnit.test("circular many2many's", async function (assert) {
        serverData.models.partner_type.fields.partner_ids = {
            string: "partners",
            type: "many2many",
            relation: "partner",
        };
        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records[0].partner_ids = [1];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy">
                        <tree><field name="display_name"/></tree>
                        <form>
                            <field name="partner_ids">
                                <tree><field name="display_name"/></tree>
                                <form><field name="display_name"/></form>
                            </field>
                        </form>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            "td:contains(gold)",
            "should display the name of the many2many on the original form"
        );
        await click(target.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".modal");
        assert.containsOnce(
            target,
            ".modal td:contains(first record)",
            "should display the name of the many2many on the modal form"
        );

        await click(target.querySelector(".modal .o_data_cell"));
        assert.containsN(
            target,
            ".modal",
            2,
            "there should be 2 modals (partner on top of partner_type) opened"
        );
    });

    QUnit.test("discard changes on a non dirty form view", async function (assert) {
        let nbWrite = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resId: 1,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    nbWrite++;
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "yop",
            "input should contain yop"
        );

        // click on discard
        await clickDiscard(target);
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "yop",
            "field should display yop"
        );

        assert.strictEqual(nbWrite, 0, "no write RPC should have been done");
    });

    QUnit.test("discard changes on a dirty form view", async function (assert) {
        let nbWrite = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resId: 1,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/partner/write") {
                    nbWrite++;
                }
            },
        });

        // edit the foo field
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "yop",
            "input should contain yop"
        );
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "new value",
            "input should contain new value"
        );

        // click on discard
        await clickDiscard(target);
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "yop",
            "field should display yop"
        );

        assert.strictEqual(nbWrite, 0, "no write RPC should have been done");
    });

    QUnit.test("discard changes on a dirty form view (for date field)", async function (assert) {
        // this test checks that the basic model properly handles date object
        // when they are discarded and saved.  This may be an issue because
        // dates are saved as luxon instances, and were at one point stringified,
        // then parsed into string, which is wrong.

        serverData.models.partner.fields.date.default = "2017-01-25";
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="date"></field></form>',
        });

        // focus the buttons before clicking on them to precisely reproduce what
        // really happens (mostly because the datepicker lib need that focus
        // event to properly focusout the input, otherwise it crashes later on
        // when the 'blur' event is triggered by the re-rendering)
        target.querySelector(".o_form_button_cancel").focus();
        await clickDiscard(target);

        target.querySelector(".o_form_button_save").focus();
        await clickSave(target);
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "01/25/2017");
    });

    QUnit.test("discard changes on relational data on new record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="product_id"/>
                        </tree>
                    </field>
                </form>`,
        });

        // edit the p field
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await selectDropdownItem(target, "product_id", "xphone");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=product_id] input").value,
            "xphone",
            "input should contain xphone"
        );

        // click on discard
        await clickDiscard(target);
        assert.containsNone(target, ".modal", "modal should not be displayed");
        assert.containsNone(target, ".o_data_row");
    });

    QUnit.test(
        "discard changes on a new (non dirty, except for defaults) form view",
        async function (assert) {
            serverData.models.partner.fields.foo.default = "ABC";

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="foo"></field></form>',
                config: {
                    historyBack() {
                        assert.step("history-back");
                    },
                },
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=foo] input").value,
                "ABC",
                "input should contain ABC"
            );

            await clickDiscard(target);

            assert.containsNone(document.body, ".modal", "there should not be a confirm modal");
            assert.verifySteps(["history-back"]);
        }
    );

    QUnit.test("discard changes on a new (dirty) form view", async function (assert) {
        serverData.models.partner.fields.foo.default = "ABC";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                </form>
            `,
            config: {
                historyBack() {
                    assert.step("history-back");
                },
            },
        });

        assert.doesNotHaveClass(
            target.querySelector(".o_form_editable"),
            "o_form_saved o_form_dirty"
        );
        // edit the foo field
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "ABC",
            "input should contain ABC"
        );
        await editInput(target, ".o_field_widget[name=foo] input", "DEF");

        assert.hasClass(target.querySelector(".o_form_editable"), "o_form_dirty");
        assert.doesNotHaveClass(target.querySelector(".o_form_editable"), "o_form_saved");

        // discard the changes and check it has properly been discarded
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "DEF",
            "input should be DEF"
        );
        await clickDiscard(target);
        assert.doesNotHaveClass(
            target.querySelector(".o_form_editable"),
            "o_form_saved o_form_dirty"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "ABC",
            "input should now be ABC"
        );
        assert.verifySteps(["history-back"]);

        // redirty and discard the field foo (to make sure initial changes haven't been lost)
        await editInput(target, ".o_field_widget[name=foo] input", "GHI");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "GHI",
            "input should be GHI"
        );
        await clickDiscard(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "ABC",
            "input should now be ABC"
        );
        assert.verifySteps(["history-back"]);
    });

    QUnit.test("save a new dirty record", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                </form>
            `,
        });
        assert.doesNotHaveClass(
            target.querySelector(".o_form_editable"),
            "o_form_saved o_form_dirty"
        );
        await editInput(target, ".o_field_widget[name=foo] input", "DEF");

        await clickSave(target);
        assert.hasClass(target.querySelector(".o_form_editable"), "o_form_saved");
        assert.doesNotHaveClass(target.querySelector(".o_form_editable"), "o_form_dirty");
    });

    QUnit.test("discard changes on a duplicated record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resId: 1,
            actionMenus: {},
        });
        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        await clickSave(target);

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Duplicate");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "tralala",
            "input should contain tralala"
        );

        await clickDiscard(target);

        assert.containsNone(document.body, ".modal", "there should not be a confirm modal");
    });

    QUnit.test("discard invalid value", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="int_field"></field></form>',
            resId: 1,
        });

        await editInput(target, ".o_field_widget[name=int_field] input", "tralala");
        await click(target, ".o_form_view");
        assert.containsOnce(target, ".o_field_invalid");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "tralala"
        );

        await clickDiscard(target);
        assert.containsNone(target, ".o_field_invalid");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "10"
        );
    });

    QUnit.test("Domain: allow empty domain on fieldInfo", async function (assert) {
        assert.expect(1);
        serverData.models.partner.fields.product_id.domain = "[('display_name', '=', name)]";
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "search_read") {
                    assert.strictEqual(JSON.stringify(args.kwargs.domain), "[]");
                }
            },
        });
    });

    QUnit.test("discard form with specialdata", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="product_id" domain="[('display_name', '=', name)]" widget="statusbar"></field>
                    </header>
                    <sheet>
                        <group>
                            <field name="name"></field>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });
        assert.containsOnce(
            target,
            ".o_statusbar_status button:not(.d-none)",
            "Must have only one statusbar button"
        );
        await editInput(target, "input#name_0.o_input", "xpad");
        assert.containsN(
            target,
            ".o_statusbar_status button:not(.d-none)",
            2,
            "Must have only two statusbar buttons"
        );
        await clickDiscard(target);
        assert.containsOnce(
            target,
            ".o_statusbar_status button:not(.d-none)",
            "Must have only one statusbar button"
        );
        const buttonText = target.querySelectorAll(".o_statusbar_status button:not(.d-none)")[0]
            .textContent;
        assert.strictEqual(buttonText, "xphone", "The statusbar button should be xphone");
    });

    QUnit.test("switching to another record from a dirty one", async function (assert) {
        let nbWrite = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resIds: [1, 2],
            resId: 1,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    nbWrite++;
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_pager_value").textContent,
            "1",
            "pager value should be 1"
        );
        assert.strictEqual(
            target.querySelector(".o_pager_limit").textContent,
            "2",
            "pager limit should be 2"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "yop",
            "input should contain yop"
        );

        // edit the foo field
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "new value",
            "input should contain new value"
        );

        // click on the pager to switch to the next record (will save record)
        await click(target.querySelector(".o_pager_next"));
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        assert.strictEqual(
            target.querySelector(".o_pager_value").textContent,
            "2",
            "pager value should be 2"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "blip",
            "input should contain blip"
        );

        await click(target.querySelector(".o_pager_previous"));
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        assert.strictEqual(
            target.querySelector(".o_pager_value").textContent,
            "1",
            "pager value should be 1"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "new value",
            "input should contain new value"
        );

        assert.strictEqual(nbWrite, 1, "one write RPC should have been done");
    });

    QUnit.test("do not reload after save when using pager", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resIds: [1, 2],
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1");
        assert.strictEqual(target.querySelector(".o_pager_limit").textContent, "2");
        assert.strictEqual(target.querySelector(".o_input").value, "yop");

        // edit the foo field
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        // click on the pager to switch to the next record (will save record)
        await click(target.querySelector(".o_pager_next"));

        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "2");
        assert.strictEqual(target.querySelector(".o_input").value, "blip");
        assert.verifySteps(["get_views", "web_read", "web_save"]);
    });

    QUnit.test("switching to another record from an invalid one", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" required="1"/>
                </form>`,
            resIds: [1, 2],
            resId: 1,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.step("web_save");
                }
            },
        });

        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "first record");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_required_modifier");
        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1");
        assert.strictEqual(target.querySelector(".o_pager_limit").textContent, "2");

        await editInput(target, ".o_field_widget[name=foo] input", "");
        await click(target.querySelector(".o_pager_next"));
        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "first record");
        assert.strictEqual(
            target.querySelector(".o_form_status_indicator .text-danger").dataset.tooltip,
            "Unable to save. Correct the issue or discard changes"
        );
        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1");
        assert.strictEqual(target.querySelector(".o_pager_limit").textContent, "2");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_field_invalid");
        assert.containsOnce(target, ".o_notification_manager .o_notification");
        assert.verifySteps([]);
    });

    QUnit.test("keynav: switching to another record from an invalid one", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo" required="1"/></form>',
            resIds: [1, 2],
            resId: 1,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    assert.step("web_save");
                }
            },
        });

        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "first record");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_required_modifier");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");

        await editInput(target, ".o_field_widget[name=foo] input", "");
        triggerHotkey("alt+n");
        await nextTick();
        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "first record");
        assert.strictEqual(
            target.querySelector(".o_form_status_indicator .text-danger").dataset.tooltip,
            "Unable to save. Correct the issue or discard changes"
        );
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_field_invalid");
        assert.containsOnce(target, ".o_notification_manager .o_notification");
        assert.verifySteps([]);
    });

    QUnit.test("switching to another record from an invalid one (2)", async function (assert) {
        // in this scenario, the record is already invalid in db, so we should be allowed to
        // leave it
        serverData.models.partner.records[0].foo = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" required="1"/>
                </form>`,
            resIds: [1, 2],
            resId: 1,
        });

        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "first record");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_required_modifier");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");

        await click(target.querySelector(".o_pager_next"));
        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "second record");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "2 / 2");

        await click(target.querySelector(".o_pager_previous"));
        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "first record");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_required_modifier");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");
    });

    QUnit.test("keynav: switching to another record from a dirty one", async function (assert) {
        let nbWrite = 0;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resIds: [1, 2],
            resId: 1,
            mockRPC(route) {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    nbWrite++;
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_pager_value").textContent,
            "1",
            "pager value should be 1"
        );
        assert.strictEqual(
            target.querySelector(".o_pager_limit").textContent,
            "2",
            "pager limit should be 2"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "yop",
            "input should contain yop"
        );

        // edit the foo field
        const input = target.querySelector(".o_field_widget[name=foo] input");
        input.value = "new value";
        await triggerEvent(input, null, "input");

        // trigger the pager hotkey to switch to the next record (will save record)
        triggerHotkey("alt+n");
        await nextTick();
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "2 / 2");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "blip",
            "input should contain blip"
        );

        triggerHotkey("alt+p");
        await nextTick();
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "new value",
            "input should contain new value"
        );

        assert.strictEqual(nbWrite, 1, "one write RPC should have been done");
    });

    QUnit.test("handling dirty state: switching to another record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"></field>
                    <field name="priority" widget="priority"></field>
                </form>`,
            resIds: [1, 2],
            resId: 1,
        });

        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "yop",
            "input should contain yop"
        );

        // edit the foo field
        await editInput(target, ".o_field_widget[name=foo] input", "new value");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "new value",
            "input should contain new value"
        );

        await clickSave(target);

        // click on the pager to switch to the next record and cancel the confirm request
        await click(target.querySelector(".o_pager_next"));
        assert.containsNone(
            document.body,
            ".modal:visible",
            "no confirm modal should be displayed"
        );
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "2 / 2");
        assert.containsN(
            target,
            ".o_priority .fa-star-o",
            2,
            "priority widget should have been rendered with correct value"
        );

        // edit the value in readonly
        await click(target.querySelector(".o_priority .fa-star-o")); // click on the first star
        assert.containsOnce(
            target,
            ".o_priority .fa-star",
            "priority widget should have been updated"
        );

        await click(target.querySelector(".o_pager_next"));
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "new value",
            "input should contain yop"
        );

        // edit the foo field
        await editInput(target, ".o_field_widget[name=foo] input", "wrong value");

        await clickDiscard(target);
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");
        await click(target.querySelector(".o_pager_next"));
        assert.strictEqual(
            target.querySelector(".o_pager_value").textContent,
            "2",
            "pager value should be 2"
        );
    });

    QUnit.test("restore local state when switching to another record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resIds: [1, 2],
            resId: 1,
        });

        // click on second page tab
        await click(target.querySelectorAll(".o_notebook .nav-link")[1]);

        assert.doesNotHaveClass(target.querySelector(".o_notebook .nav-link"), "active");
        assert.hasClass(target.querySelectorAll(".o_notebook .nav-link")[1], "active");

        // click on the pager to switch to the next record
        await click(target.querySelector(".o_pager_next"));

        assert.doesNotHaveClass(target.querySelector(".o_notebook .nav-link"), "active");
        assert.hasClass(target.querySelectorAll(".o_notebook .nav-link")[1], "active");
    });

    QUnit.test(
        "restore the open notebook page when switching to another view",
        async function (assert) {
            serverData.actions = {
                1: {
                    id: 1,
                    name: "test",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "list"]],
                },
                2: {
                    id: 2,
                    name: "test2",
                    res_model: "partner",
                    res_id: 1,
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
            };
            serverData.views = {
                "partner,false,list": `<tree><field name="foo"/></tree>`,
                "partner,false,search": `<search></search>`,
                "partner,false,form": `
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
                    </form>`,
            };

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 2);

            let notebooks = target.querySelectorAll(".o_notebook");
            assert.hasClass(notebooks[0].querySelector(".nav-link"), "active");
            assert.doesNotHaveClass(notebooks[0].querySelectorAll(".nav-link")[1], "active");

            assert.doesNotHaveClass(notebooks[1].querySelector(".nav-link"), "active");
            assert.hasClass(notebooks[1].querySelectorAll(".nav-link")[1], "active");
            assert.doesNotHaveClass(notebooks[1].querySelectorAll(".nav-link")[2], "active");

            // click on second page tab of the first notebook
            await click(notebooks[0].querySelectorAll(".nav-link")[1]);
            // click on third page tab of the second notebook
            await click(notebooks[1].querySelectorAll(".nav-link")[2]);
            notebooks = target.querySelectorAll(".o_notebook");
            assert.doesNotHaveClass(notebooks[0].querySelector(".nav-link"), "active");
            assert.hasClass(notebooks[0].querySelectorAll(".nav-link")[1], "active");

            assert.doesNotHaveClass(notebooks[1].querySelector(".nav-link"), "active");
            assert.doesNotHaveClass(notebooks[1].querySelectorAll(".nav-link")[1], "active");
            assert.hasClass(notebooks[1].querySelectorAll(".nav-link")[2], "active");

            // switch to a list view
            await doAction(webClient, 1);

            // back to the form view
            await click(target, ".o_back_button");
            notebooks = target.querySelectorAll(".o_notebook");
            assert.doesNotHaveClass(notebooks[0].querySelector(".nav-link"), "active");
            assert.hasClass(notebooks[0].querySelectorAll(".nav-link")[1], "active");

            assert.doesNotHaveClass(notebooks[1].querySelector(".nav-link"), "active");
            assert.doesNotHaveClass(notebooks[1].querySelectorAll(".nav-link")[1], "active");
            assert.hasClass(notebooks[1].querySelectorAll(".nav-link")[2], "active");
        }
    );

    QUnit.test(
        "don't restore the open notebook page when we create a new record",
        async function (assert) {
            serverData.actions = {
                1: {
                    id: 1,
                    name: "test",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                },
            };
            serverData.views = {
                "partner,false,list": `<tree><field name="foo"/></tree>`,
                "partner,false,search": `<search></search>`,
                "partner,false,form": `
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
                    </form>`,
            };

            const webClient = await createWebClient({ serverData });
            await doAction(webClient, 1);
            await click(target.querySelector(".o_data_cell"));

            let notebooks = target.querySelectorAll(".o_notebook");
            assert.hasClass(notebooks[0].querySelector(".nav-link"), "active");
            assert.doesNotHaveClass(notebooks[0].querySelectorAll(".nav-link")[1], "active");

            assert.doesNotHaveClass(notebooks[1].querySelector(".nav-link"), "active");
            assert.hasClass(notebooks[1].querySelectorAll(".nav-link")[1], "active");
            assert.doesNotHaveClass(notebooks[1].querySelectorAll(".nav-link")[2], "active");

            // click on second page tab of the first notebook
            await click(notebooks[0].querySelectorAll(".nav-link")[1]);
            // click on third page tab of the second notebook
            await click(notebooks[1].querySelectorAll(".nav-link")[2]);
            notebooks = target.querySelectorAll(".o_notebook");
            assert.doesNotHaveClass(notebooks[0].querySelector(".nav-link"), "active");
            assert.hasClass(notebooks[0].querySelectorAll(".nav-link")[1], "active");

            assert.doesNotHaveClass(notebooks[1].querySelector(".nav-link"), "active");
            assert.doesNotHaveClass(notebooks[1].querySelectorAll(".nav-link")[1], "active");
            assert.hasClass(notebooks[1].querySelectorAll(".nav-link")[2], "active");

            // back to the list view
            await click(target, ".o_back_button");

            // Create a new record
            await click(target, ".o_control_panel_main_buttons .d-none button.o_list_button_add");
            notebooks = target.querySelectorAll(".o_notebook");
            assert.hasClass(notebooks[0].querySelector(".nav-link"), "active");
            assert.doesNotHaveClass(notebooks[0].querySelectorAll(".nav-link")[1], "active");

            assert.doesNotHaveClass(notebooks[1].querySelector(".nav-link"), "active");
            assert.hasClass(notebooks[1].querySelectorAll(".nav-link")[1], "active");
            assert.doesNotHaveClass(notebooks[1].querySelectorAll(".nav-link")[2], "active");
        }
    );

    QUnit.test("pager is hidden in create mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            resId: 1,
            resIds: [1, 2],
        });

        assert.containsOnce(target, ".o_pager");
        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1");
        assert.strictEqual(target.querySelector(".o_pager_limit").textContent, "2");

        await createRecord();

        assert.containsNone(target, ".o_pager");

        await clickSave(target);

        assert.containsOnce(target, ".o_pager");
        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "3");
        assert.strictEqual(target.querySelector(".o_pager_limit").textContent, "3");
    });

    QUnit.test("switching to another record", async function (assert) {
        patchWithCleanup(browser, {
            setTimeout(fn) {
                return fn(); // update the router hash directly
            },
        });
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resId: 1,
            resIds: [1, 2],
        });

        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1");
        assert.strictEqual(form.env.services.router.current.hash.id, 1);

        await click(target.querySelector(".o_pager_next"));
        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "2");
        assert.strictEqual(form.env.services.router.current.hash.id, 2);
    });

    QUnit.test("modifiers are reevaluated when creating new record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" class="foo_field" invisible='bar'/>
                            <field name="bar"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsNone(target, ".foo_field");
        await createRecord();
        assert.containsOnce(target, ".foo_field");
    });

    QUnit.test("empty readonly fields are visible on new records", async function (assert) {
        serverData.models.partner.fields.foo.readonly = true;
        serverData.models.partner.fields.foo.default = undefined;
        serverData.models.partner.records[0].foo = undefined;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_field_empty");
        await createRecord();
        assert.containsNone(target, ".o_field_empty");
    });

    QUnit.test("all group children have correct layout classname", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });

        assert.hasClass(target.querySelector(".inner_group"), "col-lg-6");
        assert.hasClass(target.querySelector(".inner_div"), "col-lg-6");
    });

    QUnit.test("deleting a record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            actionMenus: {},
            resIds: [1, 2, 4],
            resId: 1,
        });

        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1");
        assert.strictEqual(target.querySelector(".o_pager_limit").textContent, "3");

        // open action menu and delete
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");

        assert.containsOnce(document.body, ".modal", "a confirm modal should be displayed");
        await click(document.body.querySelector(".modal-footer button.btn-primary"));

        assert.strictEqual(target.querySelector(".o_pager_value").textContent, "1");
        assert.strictEqual(target.querySelector(".o_pager_limit").textContent, "2");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "blip",
            "should have a field with foo value for record 2"
        );
    });

    QUnit.test("deleting the last record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"></field></form>',
            resIds: [1],
            resId: 1,
            actionMenus: {},
            mockRPC(route, args) {
                assert.step(args.method);
            },
            config: {
                historyBack() {
                    assert.step("history-back");
                },
            },
        });

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");

        assert.containsOnce(document.body, ".modal", "a confirm modal should be displayed");
        await click(document.body.querySelector(".modal-footer button.btn-primary"));
        assert.containsNone(document.body, ".modal", "no confirm modal should be displayed");

        assert.verifySteps(["get_views", "web_read", "unlink", "history-back"]);
    });

    QUnit.test("empty required fields cannot be saved", async function (assert) {
        serverData.models.partner.fields.foo.required = true;
        delete serverData.models.partner.fields.foo.default;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: "<form>" + '<group><field name="foo"/></group>' + "</form>",
        });

        await clickSave(target);
        assert.hasClass(target.querySelector("label.o_form_label"), "o_field_invalid");
        assert.hasClass(target.querySelector(".o_field_widget[name=foo]"), "o_field_invalid");
        assert.containsOnce(target, ".o_notification");
        assert.strictEqual(
            target.querySelector(".o_notification_title").textContent,
            "Invalid fields: "
        );
        assert.strictEqual(
            target.querySelector(".o_notification_content").innerHTML,
            "<ul><li>Foo</li></ul>"
        );
        assert.hasClass(target.querySelector(".o_notification"), "border-danger");

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");
        assert.containsNone(target, ".o_field_invalid");
    });

    QUnit.test("display a dialog if onchange result is a warning", async function (assert) {
        serverData.models.partner.onchanges = { foo: true };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/><field name="int_field"/></form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        value: { int_field: 10 },
                        warning: {
                            title: "Warning",
                            message: "You must first select a partner",
                            type: "dialog",
                        },
                    });
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "9"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "10"
        );
        assert.containsOnce(document.body, ".modal");
        assert.strictEqual(document.body.querySelector(".modal-title").textContent, "Warning");
        assert.strictEqual(
            document.body.querySelector(".modal-body").textContent,
            "You must first select a partner"
        );
    });

    QUnit.test(
        "display a notificaton if onchange result is a warning with type notification",
        async function (assert) {
            serverData.models.partner.onchanges = { foo: true };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="foo"/><field name="int_field"/></form>`,
                resId: 2,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        return Promise.resolve({
                            value: { int_field: 10 },
                            warning: {
                                title: "Warning",
                                message: "You must first select a partner",
                                type: "notification",
                                className: "abc",
                                sticky: true,
                            },
                        });
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=int_field] input").value,
                "9"
            );

            await editInput(target, ".o_field_widget[name=foo] input", "tralala");

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=int_field] input").value,
                "10"
            );

            assert.containsOnce(document.body, ".o_notification");
            assert.hasClass(document.body.querySelector(".o_notification"), "abc");
            assert.strictEqual(
                document.body.querySelector(".o_notification_title").textContent,
                "Warning"
            );
            assert.strictEqual(
                document.body.querySelector(".o_notification_content").textContent,
                "You must first select a partner"
            );
        }
    );

    QUnit.test("can create record even if onchange returns a warning", async function (assert) {
        serverData.models.partner.onchanges = { foo: true };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/><field name="int_field"/></form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        value: { int_field: 10 },
                        warning: {
                            title: "Warning",
                            message: "You must first select a partner",
                        },
                    });
                }
            },
        });
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="int_field"] input').value,
            "10",
            "record should have been created and rendered"
        );
        assert.containsOnce(document.body, ".o_notification");
    });

    QUnit.test("onchange returns an error", async function (assert) {
        registry.category("services").add("error", errorService);
        registry.category("error_dialogs").add("odoo.exceptions.UserError", WarningDialog);

        serverData.models.partner.onchanges = { int_field: () => {} };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="int_field"/></form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange" && args.args[1].int_field === 64) {
                    throw makeServerError({ message: "Some business message" });
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "9"
        );

        await editInput(target, ".o_field_widget[name=int_field] input", 64);
        await nextTick();

        assert.containsOnce(document.body, ".modal");
        assert.strictEqual(
            document.body.querySelector(".modal-body").textContent,
            "Some business message"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="int_field"] input').value,
            "9"
        );

        await click(target.querySelector(".modal .btn-close"));

        assert.containsNone(document.body, ".modal");

        await editInput(target, ".o_field_widget[name=int_field] input", 32);

        assert.containsNone(document.body, ".modal");
        assert.containsNone(target, ".o_field_invalid");
    });

    QUnit.test("button box is rendered in create mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div name="button_box" class="oe_button_box">
                        <button type="object" class="oe_stat_button" icon="fa-check-square">
                            <field name="bar"/>
                        </button>
                    </div>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(
            target,
            ".oe_stat_button",
            "button box should be displayed in edit on an existing record"
        );

        // create mode (leave edition first!)
        await clickDiscard(target);
        await createRecord();
        assert.containsOnce(
            target,
            ".oe_stat_button",
            "button box should be displayed when creating a new record as well"
        );
    });

    QUnit.test("properly apply onchange on one2many fields", async function (assert) {
        serverData.models.partner.records[0].p = [4];
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.p = [
                    [5],
                    [1, 4, { display_name: "updated record" }],
                    [0, null, { display_name: "created record" }],
                ];
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group><field name="foo"/></group>
                    <field name="p">
                        <tree><field name="display_name"/></tree>
                    </field>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_field_one2many .o_data_row",
            "there should be one one2many record linked at first"
        );
        assert.strictEqual(
            target.querySelector(".o_field_one2many .o_data_row td").textContent,
            "aaa",
            "the 'display_name' of the one2many record should be correct"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "let us trigger an onchange");
        assert.containsN(target, ".o_data_row", 2, "there should be two linked record");
        assert.strictEqual(
            target.querySelector(".o_data_row .o_data_cell").textContent,
            "updated record",
            "the 'display_name' of the first one2many record should have been updated"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell").textContent,
            "created record",
            "the 'display_name' of the second one2many record should be correct"
        );
    });

    QUnit.test("properly apply onchange on one2many fields direct click", async function (assert) {
        const def = makeDeferred();

        serverData.views = {
            "partner,false,form": `
                    <form>
                        <field name="display_name"/>
                        <field name="int_field"/>
                    </form>`,
        };
        serverData.models.partner.records[0].p = [2, 4];
        serverData.models.partner.onchanges = {
            int_field: function (obj) {
                obj.p = [
                    [1, 2, { display_name: "updated record 1", int_field: obj.int_field }],
                    [1, 4, { display_name: "updated record 2", int_field: obj.int_field * 2 }],
                ];
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="p">
                        <tree>
                            <field name="display_name"/>
                            <field name="int_field"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    await def;
                }
            },
        });

        // Trigger the onchange
        await editInput(target, ".o_field_widget[name=int_field] input", "2");
        // Open first record in one2many
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsNone(target, ".modal");

        def.resolve();
        await nextTick();

        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=int_field] input").value,
            "2"
        );
    });

    QUnit.test("update many2many value in one2many after onchange", async function (assert) {
        serverData.models.partner.records[1].p = [4];
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.p = [
                    [5],
                    [
                        1,
                        4,
                        {
                            display_name: "gold",
                            timmy: [[5]],
                        },
                    ],
                ];
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name" readonly="not timmy"/>
                            <field name="timmy"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
        });
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell")),
            ["aaa", "No records"],
            "should have proper initial content"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "tralala");

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell")),
            ["gold", "No records"],
            "should have proper initial content"
        );
    });

    QUnit.test("delete a line in a one2many while editing another line", async function (assert) {
        serverData.models.partner.records[0].p = [1, 2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="p">
                            <tree editable="bottom">
                                <field name="display_name" required="True"/>
                            </tree>
                        </field>
                    </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_data_cell"));
        await editInput(target, ".o_field_widget[name=display_name] input", "");
        await click(target.querySelectorAll(".fa-trash-o")[1]);

        assert.hasClass(
            target.querySelector(".o_data_cell"),
            "o_invalid_cell",
            "Cell should be invalidated."
        );
        assert.containsN(target, ".o_data_row", 2, "The other line should not have been deleted.");
    });

    QUnit.test("properly apply onchange on many2many fields", async function (assert) {
        assert.expect(10);

        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.timmy = [
                    [4, 12],
                    [4, 14],
                ];
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="timmy">
                        <tree><field name="display_name"/></tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.args[1].timmy,
                        [
                            [4, 12],
                            [4, 14],
                        ],
                        "should correctly save the changed m2m values"
                    );
                }
            },
            resId: 2,
        });

        assert.containsNone(
            target,
            ".o_field_many2many .o_data_row",
            "there should be no many2many record linked at first"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "let us trigger an onchange");
        assert.containsN(target, ".o_data_row", 2, "there should be two linked records");
        assert.strictEqual(
            target.querySelector(".o_data_row td").textContent,
            "gold",
            "the 'display_name' of the first m2m record should be correctly displayed"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_data_row")[1].querySelector("td").textContent,
            "silver",
            "the 'display_name' of the second m2m record should be correctly displayed"
        );

        await clickSave(target);

        assert.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
    });

    QUnit.test(
        "form with domain widget: opening a many2many form and save should not crash",
        async function (assert) {
            assert.expect(0);

            // We just test that there is no crash in this situation
            serverData.models.partner.records[0].timmy = [12];
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="foo" widget="domain"/>
                        </group>
                        <field name="timmy">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="name"/>
                                <field name="color"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });

            // open a form view and save many2many record
            await click(target.querySelector(".o_data_row .o_data_cell"));
            await click(target.querySelector(".modal-dialog footer .btn-primary"));
        }
    );

    QUnit.test("display_name not sent for onchanges if not in view", async function (assert) {
        assert.expect(6);

        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner.onchanges = {
            foo: function () {},
        };
        serverData.models.partner_type.onchanges = {
            name: function () {},
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="foo"/>
                        <field name="timmy">
                            <tree><field name="name"/></tree>
                            <form>
                                <field name="name"/>
                                <field name="color"/>
                            </form>
                        </field>
                    </group>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_read" && args.model === "partner") {
                    assert.deepEqual(
                        args.kwargs.specification,
                        {
                            display_name: {},
                            foo: {},
                            timmy: {
                                fields: {
                                    name: {},
                                    color: {},
                                },
                                limit: 40,
                                order: "",
                            },
                        },
                        "should read display_name even if not in the view"
                    );
                }
                if (args.method === "web_read" && args.model === "partner_type") {
                    assert.deepEqual(
                        args.kwargs.specification,
                        {
                            color: {},
                            name: {},
                        },
                        "should read display_name when opening the subrecord"
                    );
                }
                if (args.method === "onchange" && args.model === "partner") {
                    assert.deepEqual(
                        args.args[1],
                        {
                            foo: "coucou",
                        },
                        "should only send the changes"
                    );
                    assert.deepEqual(args.args[3], {
                        display_name: {},
                        foo: {},
                        timmy: {
                            fields: {
                                name: {},
                                color: {},
                            },
                            limit: 40,
                            order: "",
                        },
                    });
                }
                if (args.method === "onchange" && args.model === "partner_type") {
                    assert.deepEqual(
                        args.args[1],
                        {
                            name: "new name",
                        },
                        "should only send the changes"
                    );
                    assert.deepEqual(
                        args.args[3],
                        {
                            name: {},
                            color: {},
                        },
                        "only the fields in the view should be in the onchange spec"
                    );
                }
            },
            resId: 1,
        });

        // trigger the onchange
        await editInput(target, ".o_field_widget[name=foo] input", "coucou");

        // open a subrecord and trigger an onchange
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await editInput(target, ".modal .o_field_widget[name=name] input", "new name");
    });

    QUnit.test("onchanges on date(time) fields", async function (assert) {
        patchTimeZone(120);

        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.date = "2021-12-12";
                obj.datetime = "2021-12-12 10:55:05";
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="date"/>
                    <field name="datetime"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=date] input").value,
            "01/25/2017"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=datetime] input").value,
            "12/12/2016 12:55:05"
        );

        // trigger the onchange
        await editInput(target, '.o_field_widget[name="foo"] input', "coucou");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=date] input").value,
            "12/12/2021"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=datetime] input").value,
            "12/12/2021 12:55:05"
        );
    });

    QUnit.test("onchanges are not sent for invalid values", async function (assert) {
        serverData.models.partner.onchanges = {
            int_field: function (obj) {
                obj.foo = String(obj.int_field);
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/><field name="int_field"/></form>`,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        // edit int_field, and check that an onchange has been applied
        await editInput(target, '.o_field_widget[name="int_field"] input', "123");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "123",
            "the onchange has been applied"
        );

        // enter an invalid value in a float, and check that no onchange has
        // been applied
        await editInput(target, '.o_field_widget[name="int_field"] input', "123a");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "123",
            "the onchange has not been applied"
        );

        // save, and check that the int_field input is marked as invalid
        await clickSave(target);
        assert.hasClass(
            target.querySelector('.o_field_widget[name="int_field"]'),
            "o_field_invalid",
            "input int_field is marked as invalid"
        );

        assert.verifySteps(["get_views", "web_read", "onchange"]);
    });

    QUnit.test("rpc complete after destroying parent", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                <form>
                    <button name="update_module" type="object" class="o_form_button_update"/>
                </form>`,
            "partner,false,list": `<tree><field name="display_name"/></tree>`,
            "partner,false,search": "<search></search>",
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                res_id: 1,
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                target: "new",
            },
            2: {
                id: 2,
                name: "Partner 2",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
            },
        };
        const def = makeDeferred();
        const mockRPC = async (route, args) => {
            if (args.method === "update_module") {
                await def;
                return { type: "ir.actions.act_window_close" };
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_form_view");

        // should not crash when the call to "update_module" returns, as we should not
        // try to reload the form view, which will no longer be in the DOM
        await click(target.querySelector(".o_form_button_update"));

        // simulate that we executed another action before update_module returns
        await doAction(webClient, 2);
        assert.containsOnce(target, ".o_list_view");

        def.resolve(); // call to update_module finally returns
        await nextTick();
        assert.containsOnce(target, ".o_list_view");
    });

    QUnit.test("onchanges that complete after discarding", async function (assert) {
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };

        const def = makeDeferred();
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/><field name="int_field"/></form>`,
            resId: 2,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step("onchange is done");
                    await def;
                }
            },
        });

        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "blip",
            "field foo should be displayed to initial value"
        );

        // edit a field and discard
        await editInput(target, ".o_field_widget[name=foo] input", "1234");
        await clickDiscard(target);
        assert.containsNone(target, ".modal");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "1234",
            "field foo should still be displayed to changed value"
        );

        // complete the onchange
        def.resolve();
        await nextTick();
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "blip",
            "field foo should still be displayed to initial value"
        );
        assert.verifySteps(["onchange is done"]);
    });

    QUnit.test("discarding before save returns", async function (assert) {
        const def = makeDeferred();
        let form;
        patchWithCleanup(FormController.prototype, {
            setup() {
                super.setup(...arguments);
                form = this;
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            resId: 2,
            async mockRPC(route, args) {
                if (args.method === "web_save") {
                    await def;
                }
            },
        });

        assert.containsOnce(target, ".o_form_view .o_form_editable");
        await editInput(target, ".o_field_widget[name=foo] input", "1234");

        // save the value and discard directly
        await clickSave(target);
        assert.ok(target.querySelector(".o_form_button_cancel").disabled);
        // with form view extensions, it may happen that someone tries to discard
        // while there is a pending save, so we simulate this here
        form.discard();
        await nextTick();

        assert.containsOnce(target, ".o_form_view .o_form_editable");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "1234",
            "field foo should still contain new value"
        );
        assert.containsNone(target, ".modal", "Confirm dialog should not be displayed");

        // complete the write
        def.resolve();
        await nextTick();
        assert.containsNone(target, ".modal", "Confirm dialog should not be displayed");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').value,
            "1234",
            "value should have been saved and rerendered in readonly"
        );
    });

    QUnit.test("unchanged relational data is not sent for onchanges", async function (assert) {
        assert.expect(1);

        serverData.models.partner.records[1].p = [4];
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <field name="bar"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(args.args[1], { foo: "trigger an onchange" });
                }
            },
        });
        await editInput(target, ".o_field_widget[name=foo] input", "trigger an onchange");
    });

    QUnit.test("onchange value are not discarded on o2m edition", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[1].p = [4];
        serverData.models.partner.onchanges = {
            foo: function () {},
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <field name="bar"/>
                        </tree>
                        <form>
                            <field name="foo"/>
                            <field name="product_id"/>
                        </form>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        value: {
                            p: [[1, 4, { foo: "foo changed" }]],
                        },
                    });
                }
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.args[1].p,
                        [
                            [
                                1,
                                4,
                                {
                                    foo: "foo changed",
                                },
                            ],
                        ],
                        "should only write value of known fields"
                    );
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_data_row td").textContent,
            "My little Foo Value",
            "the initial value should be the default one"
        );

        await editInput(target, ".o_field_widget[name=foo] input", "trigger an onchange");

        assert.strictEqual(
            target.querySelector(".o_data_row td").textContent,
            "foo changed",
            "onchange should have been correctly applied on field in o2m list"
        );

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal .modal-title").textContent.trim(),
            "Open: one2many field",
            "the field string is displayed in the modal title"
        );
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget input").value,
            "foo changed",
            "the onchange value hasn't been discarded when opening the o2m"
        );
    });

    QUnit.test(
        "args of onchanges in o2m fields are correct (inline edition)",
        async function (assert) {
            serverData.models.partner.records[1].p = [4];
            serverData.models.partner.fields.int_field.default = 14;
            serverData.models.partner.onchanges = {
                int_field: function (obj) {
                    obj.foo = "[blip] " + obj.int_field;
                },
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p">
                            <tree editable="top">
                                <field name="foo"/>
                                <field name="int_field"/>
                            </tree>
                        </field>
                    </form>`,
                resId: 2,
            });

            assert.strictEqual(
                target.querySelector(".o_data_row td").textContent,
                "My little Foo Value",
                "the initial value should be the default one"
            );

            await click(target.querySelectorAll(".o_data_row td")[1]);
            await editInput(target, ".o_field_widget[name=int_field] input", 77);

            assert.strictEqual(
                target.querySelector(".o_data_row input").value,
                "[blip] 77",
                "onchange should have been correctly applied"
            );

            // create a new o2m record
            await click(target.querySelector(".o_field_x2many_list_row_add a"));
            assert.strictEqual(
                target.querySelector(".o_data_row input").value,
                "[blip] 14",
                "onchange should have been correctly applied after default get"
            );
        }
    );

    QUnit.test(
        "args of onchanges in o2m fields are correct (dialog edition)",
        async function (assert) {
            serverData.models.partner.records[1].p = [4];
            serverData.models.partner.fields.int_field.default = 14;
            serverData.models.partner.onchanges = {
                int_field: function (obj) {
                    obj.foo = "[blip] " + obj.int_field;
                },
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo"/>
                        <field name="p" string="custom label">
                            <tree>
                                <field name="foo"/>
                            </tree>
                            <form>
                                <field name="foo"/>
                                <field name="int_field"/>
                            </form>
                        </field>
                    </form>`,
                resId: 2,
            });

            assert.strictEqual(
                target.querySelector(".o_data_row td").textContent,
                "My little Foo Value",
                "the initial value should be the default one"
            );

            await click(target.querySelector(".o_data_row td"));
            await editInput(target, ".modal .o_field_widget[name=int_field] input", 77);
            assert.strictEqual(
                target.querySelector(".modal .o_field_widget[name=foo] input").value,
                "[blip] 77",
                "onchange should have been correctly applied"
            );
            await click(target.querySelector(".modal-footer .btn-primary"));
            assert.strictEqual(
                target.querySelector(".o_data_row td").textContent,
                "[blip] 77",
                "onchange should have been correctly applied"
            );

            // create a new o2m record
            await click(target.querySelector(".o_field_x2many_list_row_add a"));
            assert.strictEqual(
                target.querySelector(".modal .modal-title").textContent.trim(),
                "Create custom label",
                "the custom field label is applied in the modal title"
            );
            assert.strictEqual(
                target.querySelector(".modal .o_field_widget[name=foo] input").value,
                "[blip] 14",
                "onchange should have been correctly applied after default get"
            );
            await click(target.querySelector(".modal-footer .btn-primary"));
            assert.strictEqual(
                target.querySelectorAll(".o_data_row")[1].querySelector("td").textContent,
                "[blip] 14",
                "onchange should have been correctly applied after default get"
            );
        }
    );

    QUnit.test(
        "context of onchanges contains the context of changed fields",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.onchanges = {
                foo: function () {},
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="foo" context="{'test': 1}"/>
                        <field name="int_field" context="{'int_ctx': 1}"/>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "onchange") {
                        assert.strictEqual(
                            args.kwargs.context.test,
                            1,
                            "the context of the field triggering the onchange should be given"
                        );
                        assert.strictEqual(
                            args.kwargs.context.int_ctx,
                            undefined,
                            "the context of other fields should not be given"
                        );
                    }
                },
                resId: 2,
            });
            await editInput(target, ".o_field_widget[name=foo] input", "coucou");
        }
    );

    QUnit.test("clicking on a stat button with a context", async function (assert) {
        assert.expect(1);

        const actionService = {
            start() {
                return {
                    doActionButton(args) {
                        // button context should have been evaluated and given to the
                        // action, with magic keys but without previous context
                        assert.deepEqual(args.buttonContext, { test: 2 });
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button class="oe_stat_button" type="action" name="1" context="{'test': id}">
                                <field name="qux" widget="statinfo"/>
                            </button>
                        </div>
                    </sheet>
                </form>`,
            resId: 2,
            context: { some_context: true },
        });

        await click(target.querySelector(".oe_stat_button"));
    });

    QUnit.test("clicking on a stat button with x2many in context", async function (assert) {
        assert.expect(1);
        serverData.models.partner.records[1].timmy = [12];

        const actionService = {
            start() {
                return {
                    doActionButton(args) {
                        assert.equal(JSON.stringify(args.buttonContext), '{"test":[12]}');
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button class="oe_stat_button" type="action" name="1" context="{'test': timmy}">
                                <field name="qux" widget="statinfo"/>
                            </button>
                        </div>
                        <field name="timmy" invisible="1"/>
                    </sheet>
                </form>`,
            resId: 2,
            context: { some_context: true },
        });
        await click(target.querySelector(".oe_stat_button"));
    });

    QUnit.test("clicking on a stat button with no context", async function (assert) {
        assert.expect(1);

        const actionService = {
            start() {
                return {
                    doActionButton(args) {
                        // button context should have been evaluated and given to the
                        // action, with magic keys but without previous context
                        assert.deepEqual(args.buttonContext, {});
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button class="oe_stat_button" type="action" name="1">
                                <field name="qux" widget="statinfo"/>
                            </button>
                        </div>
                    </sheet>
                </form>`,
            resId: 2,
            context: { some_context: true },
        });

        await click(target.querySelector(".oe_stat_button"));
    });

    QUnit.test("diplay a stat button outside a buttonbox", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <button class="oe_stat_button" type="action" name="1">
                            <field name="int_field" widget="statinfo"/>
                        </button>
                    </sheet>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(
            target,
            "button .o_field_widget",
            "a field widget should be display inside the button"
        );
        assert.strictEqual(
            target.querySelector("button .o_field_widget").children.length,
            2,
            "the field widget should have 2 children, the text and the value"
        );
        assert.strictEqual(
            parseInt(target.querySelector("button .o_field_widget .o_stat_value").textContent),
            9,
            "the value rendered should be the same as the field value"
        );
    });

    QUnit.test("display something else than a button in a buttonbox", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div name="button_box" class="oe_button_box">
                        <button type="object" class="oe_stat_button" icon="fa-check-square">
                            <field name="bar"/>
                        </button>
                        <label/>
                    </div>
                </form>`,
            resId: 2,
        });

        assert.strictEqual(
            target.querySelector(".o-form-buttonbox").children.length,
            2,
            "button box should contain two children"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox > .oe_stat_button",
            "button box should only contain one button"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox > label",
            "button box should only contain one label"
        );
    });

    QUnit.test(
        "invisible fields are not considered as visible in a buttonbox",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <div name="button_box" class="oe_button_box">
                            <field name="foo" invisible="1"/>
                            <field name="bar" invisible="1"/>
                            <field name="int_field" invisible="1"/>
                            <field name="qux" invisible="1"/>
                            <field name="display_name" invisible="1"/>
                            <field name="state" invisible="1"/>
                            <field name="date" invisible="1"/>
                            <field name="datetime" invisible="1"/>
                            <button type="object" class="oe_stat_button" icon="fa-check-square"/>
                        </div>
                    </form>`,
                resId: 2,
            });

            assert.strictEqual(
                target.querySelector(".o-form-buttonbox").children.length,
                1,
                "button box should contain only one child"
            );
            assert.hasClass(
                target.querySelector(".o-form-buttonbox"),
                "o_not_full",
                "the buttonbox should not be full"
            );
        }
    );

    QUnit.test("display correctly buttonbox, in large size class", async function (assert) {
        const uiService = {
            start(env) {
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
            },
        };
        registry.category("services").add("ui", uiService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div name="button_box" class="oe_button_box">
                        <button type="object" class="oe_stat_button" icon="fa-check-square">
                            <field name="bar"/>
                        </button>
                        <button type="object" class="oe_stat_button" icon="fa-check-square">
                            <field name="foo"/>
                        </button>
                    </div>
                </form>`,
            resId: 2,
        });

        assert.strictEqual(
            target.querySelector(".o-form-buttonbox").children.length,
            2,
            "button box should contain two children"
        );
    });

    QUnit.test("empty button box", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div class="oe_button_box" name="button_box">
                    </div>
                </form>`,
            resId: 2,
        });

        assert.containsNone(target, ".o-form-buttonbox");
    });

    QUnit.test("button box accepts extra classes", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div class="oe_button_box my_class" name="button_box"><div/></div>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(target, ".o-form-buttonbox.my_class");
    });

    QUnit.test("many2manys inside one2manys are saved correctly", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top">
                            <field name="timmy" widget="many2many_tags"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    const command = args.args[1].p;
                    assert.deepEqual(
                        command,
                        [
                            [
                                0,
                                command[0][1],
                                {
                                    timmy: [[6, false, [12]]],
                                },
                            ],
                        ],
                        "the default partner_type_id should be equal to 12"
                    );
                }
            },
        });

        // add a o2m subrecord with a m2m tag
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await selectDropdownItem(target, "timmy", "gold");
        await clickSave(target);
    });

    QUnit.test(
        "one2manys (list editable) inside one2manys are saved correctly",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree><field name="p"/></tree>
                            <form>
                                <field name="p">
                                    <tree editable="top">
                                        <field name="display_name"/>
                                    </tree>
                                </field>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.deepEqual(
                            args.args[1].p,
                            [
                                [
                                    0,
                                    args.args[1].p[0][1],
                                    {
                                        p: [
                                            [
                                                0,
                                                args.args[1].p[0][2].p[0][1],
                                                { display_name: "xtv" },
                                            ],
                                        ],
                                    },
                                ],
                            ],
                            "create should be called with the correct arguments"
                        );
                    }
                },
            });

            // add a o2m subrecord
            await click(target.querySelector(".o_field_x2many_list_row_add a"));
            await click(target.querySelector(".modal .o_field_x2many_list_row_add a"));
            await editInput(target, ".modal .o_field_widget[name=display_name] input", "xtv");
            await click(target.querySelector(".modal-footer .btn-primary"));
            assert.containsNone(target, ".modal", "dialog should be closed");
            assert.strictEqual(
                target.querySelector(".o_data_cell").textContent,
                "1 record",
                "the cell should contains the number of record: 1"
            );

            await clickSave(target);
        }
    );

    QUnit.test("*_view_ref in context are passed correctly", async function (assert) {
        serverData.views = {
            "partner_type,module.tree_view_ref,list": "<tree/>",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="one2many" context="{'tree_view_ref':'module.tree_view_ref'}"/>
                </form>`,
            resId: 1,
            resIds: [1, 2],
            mockRPC(route, args) {
                assert.step(`${args.kwargs.context.some_context}`);
                if (args.method === "get_views" && args.model === "partner_type") {
                    // get_views for the x2many field
                    assert.step(args.kwargs.context.tree_view_ref);
                }
            },
            context: { some_context: 354 },
        });

        assert.verifySteps([
            "undefined", // main get_views
            "undefined", // x2many get_views
            "module.tree_view_ref", // x2many get_views
            "354", // read
        ]);

        // reload to check that the record's context hasn't been modified
        await click(target.querySelector(".o_pager_next"));
        assert.verifySteps(["354"]);
    });

    QUnit.test("non inline subview and create=0 in action context", async function (assert) {
        // the create=0 should apply on the main view (form), but not on subviews
        // this works because we pass the "base_model" in the context for the "get_views" call
        serverData.views = {
            "product,false,kanban": `
                <kanban>
                    <templates><t t-name="kanban-box">
                        <div><field name="name"/></div>
                    </t></templates>
                </kanban>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="product_ids" mode="kanban" widget="one2many"/></form>',
            resId: 1,
            context: { create: false },
        });

        assert.containsNone(target, ".o_form_button_create");
        assert.containsOnce(target, ".o-kanban-button-new");
    });

    QUnit.test("readonly fields with modifiers may be saved", async function (assert) {
        // the readonly property on the field description only applies on view,
        // this is not a DB constraint. It should be seen as a default value,
        // that may be overridden in views, for example with modifiers. So
        // basically, a field defined as readonly may be edited.
        assert.expect(3);

        serverData.models.partner.fields.foo.readonly = true;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" readonly="not bar"/>
                    <field name="bar"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1], { foo: "New foo value" });
                }
            },
        });

        // bar being set to true, foo shouldn't be readonly and thus its value
        // could be saved, even if in its field description it is readonly
        assert.containsOnce(
            target,
            '.o_field_widget[name="foo"] input',
            "foo field should be editable"
        );
        await editInput(target, '.o_field_widget[name="foo"] input', "New foo value");

        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "New foo value",
            "new value for foo field should have been saved"
        );
    });

    QUnit.test("readonly sub fields fields with force_save attribute", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.foo.readonly = true;
        serverData.models.partner.fields.int_field.readonly = true;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="foo" force_save="1"/>
                            <field name="int_field"/>
                            <field name="qux"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    // foo should be saved because of the "force_save" attribute
                    // qux should be saved because it isn't readonly
                    // int_field should not be saved as it is readonly
                    const commands = args.args[1].p;
                    assert.deepEqual(commands, [
                        [0, commands[0][1], { foo: "some value", qux: 6.5 }],
                    ]);
                }
                if (args.method === "onchange") {
                    return {
                        value: {
                            p: [[0, false, { foo: "some value", int_field: 44, qux: 6.5 }]],
                        },
                    };
                }
            },
        });

        await clickSave(target);
    });

    QUnit.test("readonly set by modifier do not break many2many_tags", async function (assert) {
        serverData.models.partner.onchanges = {
            bar: function (obj) {
                obj.timmy = [[4, 12]];
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar"/>
                    <field name="timmy" widget="many2many_tags" readonly="bar"/>
                </form>`,
            resId: 5,
        });

        assert.containsNone(target, ".o_field_widget[name=timmy] .o_tag");
        await click(target.querySelector(".o_field_widget[name=bar] input"));
        assert.containsOnce(target, ".o_field_widget[name=timmy] .o_tag");
    });

    QUnit.test("check if id is available in evaluation context", async function (assert) {
        assert.expect(1);

        let checkOnchange = false;
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" context="{'current_id': id}">
                        <tree><field name="trululu"/></tree>
                        <form><field name="trululu"/></form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange" && checkOnchange) {
                    assert.strictEqual(
                        args.kwargs.context.current_id,
                        false,
                        "current_id should be false"
                    );
                }
            },
        });

        checkOnchange = true;
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
    });

    QUnit.test("modifiers are considered on multiple <footer/> tags", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="bar"/>
                    <footer invisible="not bar">
                        <button>Hello</button>
                        <button>World</button>
                    </footer>
                    <footer invisible="bar">
                        <button>Foo</button>
                    </footer>
                </form>`,
            "partner,false,search": "<search></search>",
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                res_id: 1,
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                target: "new",
            },
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        assert.deepEqual(
            getVisibleButtonTexts(),
            ["Hello", "World"],
            "only the first button section should be visible"
        );

        await click(target.querySelector(".o_field_boolean input"));

        assert.deepEqual(
            getVisibleButtonTexts(),
            ["Foo"],
            "only the second button section should be visible"
        );

        function getVisibleButtonTexts() {
            return [...target.querySelectorAll(".modal-footer button:not(.d-none)")].map((x) =>
                x.textContent.trim()
            );
        }
    });

    QUnit.test("buttons in footer are moved to $buttons if necessary", async function (assert) {
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="foo"/>
                    <footer>
                        <button string="Create" type="object" class="infooter"/>
                    </footer>
                </form>`,
            "partner,false,search": "<search></search>",
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                target: "new",
            },
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        await nextTick();

        assert.containsOnce(target.querySelector(".modal-footer"), "button.infooter");
        assert.containsNone(target.querySelector(".o_form_view"), "button.infooter");
    });

    QUnit.test("open new record even with warning message", async function (assert) {
        serverData.models.partner.onchanges = { foo: true };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><group><field name="foo"/></group></form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    return Promise.resolve({
                        warning: {
                            title: "Warning",
                            message: "Any warning.",
                        },
                        value: {},
                    });
                }
            },
        });
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "blip",
            "input should contain record value"
        );
        await editInput(target, '.o_field_widget[name="foo"] input', "tralala");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "tralala",
            "input should contain new value"
        );

        await clickDiscard(target);
        await createRecord();
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "",
            "input should have no value after reload"
        );
    });

    QUnit.test("render stat button with string inline", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button string="Inventory Moves" class="oe_stat_button" icon="oi-arrows-v"/>
                        </div>
                    </sheet>
                </form>`,
        });
        const button = target.querySelector(".o_form_view .o-form-buttonbox .oe_stat_button");
        assert.strictEqual(
            button.textContent,
            "Inventory Moves",
            "the stat button should contain a span with the string attribute value"
        );
    });

    QUnit.test("open one2many form containing one2many", async function (assert) {
        serverData.models.partner.records[0].product_ids = [37];
        serverData.models.product.fields.partner_type_ids = {
            string: "one2many partner",
            type: "one2many",
            relation: "partner_type",
        };
        serverData.models.product.records[0].partner_type_ids = [12];

        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="partner_type_ids">
                        <tree create="0">
                            <field name="display_name"/>
                            <field name="color"/>
                        </tree>
                    </field>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="product_ids" widget="one2many">
                        <tree create="0">
                            <field name="display_name"/>
                            <field name="partner_type_ids"/>
                        </tree>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.strictEqual(
            target.querySelectorAll(".o_data_row .o_data_cell")[1].textContent,
            "1 record",
            "the cell should contains the number of record: 1"
        );
        await click(target.querySelector(".o_data_cell"));
        assert.containsN(
            target,
            ".modal .o_data_row .o_data_cell",
            2,
            "the row should contains the 2 fields defined in the form view"
        );
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".modal .o_data_cell")),
            ["gold", "2"],
            "the value of the fields should be fetched and displayed"
        );
        assert.verifySteps(
            ["get_views", "web_read", "get_views", "web_read"],
            "there should be 4 read rpcs"
        );
    });

    QUnit.test("no field should be focused", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/><field name="bar"/></form>',
            resId: 1,
        });

        assert.strictEqual(document.activeElement, document.body);
    });

    QUnit.test("in create mode, first field is focused", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/><field name="bar"/></form>',
        });

        assert.strictEqual(
            document.activeElement,
            target.querySelector('.o_field_widget[name="foo"] input')
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="foo"] input').selectionStart,
            target.querySelector('.o_field_widget[name="foo"] input').value.length,
            "cursor should be at the end"
        );
    });

    QUnit.test("autofocus fields are focused", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="int_field"/><field name="foo" default_focus="1"/></form>',
        });
        assert.strictEqual(
            document.activeElement,
            target.querySelector('.o_field_widget[name="foo"] input')
        );
    });

    QUnit.test("in create mode, autofocus fields are focused", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="int_field"/><field name="foo" default_focus="1"/></form>',
        });
        assert.strictEqual(
            document.activeElement,
            target.querySelector('.o_field_widget[name="foo"] input')
        );
    });

    QUnit.test("autofocus first visible field", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="int_field" invisible="1"/><field name="foo"/></form>',
        });
        assert.strictEqual(
            document.activeElement,
            target.querySelector('.o_field_widget[name="foo"] input')
        );
    });

    QUnit.test(
        "no autofocus with disable_autofocus option [REQUIRE FOCUS]",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form disable_autofocus="1"><field name="int_field"/></form>',
            });

            assert.notStrictEqual(
                document.activeElement,
                target.querySelector('.o_field_widget[name="int_field"] input')
            );
            await clickSave(target);
            assert.notStrictEqual(
                document.activeElement,
                target.querySelector('.o_field_widget[name="int_field"] input')
            );
        }
    );

    QUnit.test("In READ mode, focus the first primary button of the form", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form edit="0">
                        <field name="state" invisible="1"/>
                        <header>
                            <button name="post" class="btn-primary firstButton" string="Confirm" type="object"/>
                            <button name="post" class="btn-primary secondButton" string="Confirm2" type="object"/>
                        </header>
                        <sheet>
                            <group>
                                <div class="oe_title">
                                    <field name="display_name"/>
                                </div>
                            </group>
                        </sheet>
                    </form>`,
            resId: 2,
        });
        assert.strictEqual(target.querySelector("button.firstButton"), document.activeElement);
    });

    QUnit.test("check scroll on small height screens", async function (assert) {
        serverData.views = {
            "partner,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,list": '<tree><field name="name"/></tree>',
            "product,false,list": '<tree><field name="name"/></tree>',
            "partner,false,form": '<form><field name="trululu"/></form>',
        };

        await makeViewInDialog({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: `
                <form>
                    <sheet><group>
                    <field name="display_name"/>
                    <field name="foo"/>
                    <field name="bar"/>
                    <field name="p"/>
                    <field name="timmy"/>
                    <field name="product_ids"/>
                    <field name="trululu"/>
                    </group></sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "get_formview_id") {
                    return false;
                }
            },
        });

        // we make the content height very small so we can test scrolling.
        $(".o_content").css({ overflow: "auto", "max-height": "300px" });

        assert.containsOnce(target, ".modal-dialog");
        // Open many2one modal, lastActivatedFieldIndex will not set as we directly click on external button
        assert.strictEqual($(".o_content").scrollTop(), 0, "scroll position should be 0");
        // simply triggerEvent focus doesn't do the trick (doesn't scroll).
        target.querySelector("[name='trululu'] input").focus();
        assert.notStrictEqual($(".o_content").scrollTop(), 0, "scroll position should not be 0");

        await click(target.querySelector(".o_external_button"));

        // Close modal
        await click(target, '.o_dialog:not(.o_inactive_modal) button[class="btn-close"]');
        assert.notStrictEqual(
            $(".o_content").scrollTop(),
            0,
            "scroll position should not be 0 after closing modal"
        );

        assert.containsOnce(target, ".modal-dialog");
    });

    QUnit.test("correct amount of buttons", async function (assert) {
        let screenSize = 7;
        const uiService = {
            start(env) {
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
            },
        };
        registry.category("services").add("ui", uiService, { force: true });

        const buttons = Array(8).join(`
            <button type="object" class="oe_stat_button" icon="fa-check-square">
                <field name="bar"/>
            </button>`);

        const statButtonSelector = ".o-form-buttonbox .oe_stat_button:not(.o-dropdown)";

        const formView = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div name="button_box" class="oe_button_box">
                        ${buttons}
                    </div>
                </form>`,
            resId: 2,
        });

        const assertFormContainsNButtonsWithSizeClass = async function (size_class, n) {
            screenSize = size_class;
            formView.render(true); // deep rendering
            await nextTick();
            assert.containsN(
                target,
                statButtonSelector,
                n,
                "The form has the expected amount of buttons"
            );
        };

        await assertFormContainsNButtonsWithSizeClass(0, 3);
        await assertFormContainsNButtonsWithSizeClass(1, 3);
        await assertFormContainsNButtonsWithSizeClass(2, 3);
        await assertFormContainsNButtonsWithSizeClass(3, 7);
        await assertFormContainsNButtonsWithSizeClass(4, 3);
        await assertFormContainsNButtonsWithSizeClass(5, 4);
        await assertFormContainsNButtonsWithSizeClass(6, 7);
    });

    QUnit.test("can set bin_size to false in context", async function (assert) {
        assert.expect(1);
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            resId: 1,
            context: {
                bin_size: false,
            },
            mockRPC(route, args) {
                if (args.method === "web_read") {
                    assert.strictEqual(
                        args.kwargs.context.bin_size,
                        false,
                        "bin_size should always be in the context and should be false"
                    );
                }
            },
        });
    });

    QUnit.test("create with false values", async function (assert) {
        assert.expect(1);
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="bar"/></form>`,
            mockRPC(route, { method, args }) {
                if (method === "web_save") {
                    assert.deepEqual(args[1].bar, false);
                }
            },
        });

        await clickSave(target);
    });

    QUnit.test("open one2many form containing many2many_tags", async function (assert) {
        serverData.models.partner.records[0].product_ids = [37];
        serverData.models.product.fields.partner_type_ids = {
            string: "many2many partner_type",
            type: "many2many",
            relation: "partner_type",
        };
        serverData.models.product.records[0].partner_type_ids = [12, 14];

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="product_ids">
                        <tree create="0">
                            <field name="display_name"/>
                            <field name="partner_type_ids" widget="many2many_tags"/>
                        </tree>
                        <form>
                            <group>
                                <label for="partner_type_ids"/>
                                <div>
                                    <field name="partner_type_ids" widget="many2many_tags"/>
                                </div>
                            </group>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        await click(target.querySelector(".o_data_cell"));
        assert.verifySteps(["get_views", "web_read", "web_read"]);
    });

    QUnit.test("onchanges are applied before checking if it can be saved", async function (assert) {
        serverData.models.partner.onchanges.foo = function (obj) {};
        serverData.models.partner.fields.foo.required = true;

        const notificationService = makeFakeNotificationService((msg, options) => {
            assert.step(options.type);
        });
        registry.category("services").add("notification", notificationService, { force: true });

        const def = makeDeferred();
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: "<form><field name='foo'/></form>",
            resId: 2,
            async mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "onchange") {
                    await def;
                }
            },
        });

        await editInput(target, ".o_field_widget[name=foo] input", "");
        await clickSave(target);

        def.resolve();
        await nextTick();

        assert.verifySteps(["get_views", "web_read", "onchange", "danger"]);
    });

    QUnit.test("display toolbar", async function (assert) {
        assert.expect(6);

        const actionService = {
            start() {
                return {
                    doAction(action, options) {
                        assert.strictEqual(action, 29);
                        assert.strictEqual(options.additionalContext.active_id, 1);
                        assert.deepEqual(options.additionalContext.active_ids, [1]);
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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

        await toggleActionMenu(target);
        assert.containsNone(target, ".o_cp_action_menus .dropdown-menu_group:contains(Print)");
        assert.containsN(
            target,
            ".o_cp_action_menus .dropdown-item",
            3,
            "there should be 3 actions"
        );
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_cp_action_menus .dropdown-item")),
            ["Duplicate", "Delete", "Action partner"]
        );

        await toggleMenuItem(target, "Action partner");
    });

    QUnit.test("execute ActionMenus actions", async function (assert) {
        const actionService = {
            start() {
                return {
                    doAction(id, { additionalContext, onClose }) {
                        assert.step(JSON.stringify({ action_id: id, context: additionalContext }));
                        onClose(); // simulate closing of target new action's dialog
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.containsOnce(target, ".o_cp_action_menus .dropdown-toggle");

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Action Partner");

        assert.verifySteps([
            "get_views",
            "web_read",
            `{"action_id":29,"context":{"lang":"en","uid":7,"tz":"taht","active_id":1,"active_ids":[1],"active_model":"partner","active_domain":[]}}`,
            "web_read",
        ]);
    });

    QUnit.test("execute ActionMenus actions (create)", async function (assert) {
        const actionService = {
            start() {
                return {
                    doAction(id, { additionalContext, onClose }) {
                        assert.step(JSON.stringify({ action_id: id, context: additionalContext }));
                        onClose(); // simulate closing of target new action's dialog
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='foo'] input").value,
            "My little Foo Value"
        );
        await editInput(target, ".o_field_widget[name='foo'] input", "test");
        assert.containsOnce(target, ".o_cp_action_menus .dropdown-toggle");

        await toggleActionMenu(target);
        await toggleMenuItem(target, "Action Partner");

        assert.verifySteps([
            "get_views",
            "onchange",
            "web_save",
            `{"action_id":29,"context":{"lang":"en","uid":7,"tz":"taht","active_id":6,"active_ids":[6],"active_model":"partner","active_domain":[]}}`,
            "web_read",
        ]);

        assert.strictEqual(target.querySelector(".o_field_widget[name='foo'] input").value, "test");
    });

    QUnit.test("control panel is not present in FormViewDialogs", async function (assert) {
        serverData.models.partner.records[0].product_id = 37;
        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="display_name"/>
                </form>`,
            "product,false,list": '<tree><field name="display_name"/></tree>',
        };

        await makeViewInDialog({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="product_id"/></form>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return false;
                }
            },
        });

        assert.containsOnce(target, ".modal");
        assert.containsNone(target, ".o_control_panel");
        await click(target.querySelector(".o_external_button"));
        assert.containsN(target, ".modal", 2);
        assert.containsNone(target, ".o_control_panel");
    });

    QUnit.test("check interactions between multiple FormViewDialogs", async function (assert) {
        assert.expect(9);

        serverData.models.product.fields.product_ids = {
            string: "one2many product",
            type: "one2many",
            relation: "product",
        };

        serverData.models.partner.records[0].product_id = 37;
        serverData.views = {
            "product,false,form": `
                <form>
                    <field name="display_name"/>
                    <field name="product_ids"/>
                </form>`,
            "product,false,list": '<tree><field name="display_name"/></tree>',
        };

        await makeViewInDialog({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="product_id"/></form>`,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/product/get_formview_id") {
                    return false;
                } else if (args.method === "web_save") {
                    assert.strictEqual(args.model, "product");
                    assert.strictEqual(args.args[1].product_ids[0][2].display_name, "xtv");
                }
            },
        });

        assert.containsOnce(target, ".modal");

        // Open first dialog
        await click(target.querySelector(".o_external_button"));
        assert.containsN(target, ".modal", 2);
        assert.strictEqual(
            target
                .querySelector(".o_dialog:not(.o_inactive_modal) .modal-title")
                .textContent.trim(),
            "Open: Product"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_dialog:not(.o_inactive_modal) .o_field_widget[name=display_name] input"
            ).value,
            "xphone"
        );

        // Open third dialog
        await click(
            target.querySelector(".o_dialog:not(.o_inactive_modal) .o_field_x2many_list_row_add a")
        );
        assert.containsN(target, ".modal", 3);
        // Add new value
        const thirdModal = target.querySelectorAll(".modal")[2];
        await editInput(thirdModal, ".o_field_widget[name=display_name] input", "xtv");
        await click(thirdModal.querySelector(".modal-footer .btn-primary"));
        assert.containsN(target, ".modal", 2);

        // Check that data in first dialog is correctly updated
        assert.strictEqual(
            target.querySelector(".o_dialog:not(.o_inactive_modal) .o_data_row .o_data_cell")
                .textContent,
            "xtv"
        );
        await click(
            target.querySelector(
                ".o_dialog:not(.o_inactive_modal) .modal-footer .btn-primary:not(.d-none"
            )
        );
    });

    QUnit.test(
        "do not activate an hidden tab when switching between records",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
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
                    </form>`,
                resIds: [1, 2],
                resId: 1,
            });

            assert.containsN(target, ".o_notebook .nav-item", 2, "both tabs should be visible");
            assert.hasClass(
                target.querySelector(".o_notebook .nav-link"),
                "active",
                "first tab should be active"
            );

            // click on the pager to switch to the next record
            await click(target.querySelector(".o_pager_next"));

            assert.containsOnce(target, ".o_notebook .nav-item");
            assert.hasClass(
                target.querySelector(".o_notebook .nav-link"),
                "active",
                "the visible tab should be active"
            );

            // click on the pager to switch back to the previous record
            await click(target.querySelector(".o_pager_previous"));

            assert.containsN(target, ".o_notebook .nav-item", 2, "both tabs should be visible");
            assert.hasClass(
                target.querySelectorAll(".o_notebook .nav-link")[1],
                "active",
                "second tab should be active"
            );
        }
    );

    QUnit.test("support anchor tags with action type", async function (assert) {
        assert.expect(2);

        const actionService = {
            start() {
                return { doActionButton: (action) => assert.strictEqual(action.name, "42") };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <a type="action" name="42" class="btn-primary"><i class="oi oi-arrow-right"/> Click me !</a>
                </form>`,
            resId: 1,
        });
        await click(target.querySelector("a[type='action']"));
        assert.hasClass(
            target.querySelector("a[type='action']"),
            "btn-primary",
            "classname is given if set on the <a> element"
        );
    });

    QUnit.test(
        "do not perform extra RPC to read invisible many2one fields",
        async function (assert) {
            // WOWL TODO: use this test to check the unity spec:
            // an invisible manyone should only requests the id, not the display_name
            // -> invisible: { trululu: 1/{} }, visible: { trululu: { fields: { display_name }}}
            serverData.models.partner.fields.trululu.default = 2;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="trululu" invisible="1"/></form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });
            assert.verifySteps(["get_views", "onchange"]);
        }
    );

    QUnit.test("do not perform extra RPC to read invisible x2many fields", async function (assert) {
        serverData.models.partner.records[0].p = [2]; // one2many
        serverData.models.partner.records[0].product_ids = [37]; // one2many
        serverData.models.partner.records[0].timmy = [12]; // many2many

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <field name="p" widget="one2many" invisible="1"/>
                        <field name="product_ids" widget="one2many" invisible="1">
                            <tree><field name="display_name"/></tree>
                        </field>
                        <field name="timmy" invisible="1" widget="many2many_tags"/>
                    </form>`,
            mockRPC(route, { method, kwargs }) {
                assert.step(method);
                if (method === "web_read") {
                    assert.deepEqual(kwargs.specification, {
                        p: {},
                        product_ids: {},
                        timmy: {},
                        display_name: {},
                    });
                }
            },
            resId: 1,
        });

        assert.verifySteps(["get_views", "web_read"]);
    });

    QUnit.test("default_order on x2many embedded view", async function (assert) {
        serverData.models.partner.fields.display_name.sortable = true;
        serverData.models.partner.records[0].p = [1, 4];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree default_order="foo desc">
                            <field name="display_name"/>
                            <field name="foo"/>
                        </tree>
                        <form><field name="foo"/></form>,
                    </field>
                </form>`,
            resId: 1,
        });

        function getFooValues(row) {
            const rows = target.querySelectorAll(".o_data_row");
            return [...rows].map((r) => r.querySelectorAll(".o_data_cell")[1].textContent);
        }

        assert.deepEqual(getFooValues(), ["yop", "My little Foo Value"]);

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.containsOnce(target, ".modal");
        await editInput(target, ".modal .o_field_widget[name=foo] input", "xop");
        await click(target.querySelector(".modal-footer .o_form_button_save_new"));
        await editInput(target, ".modal .o_field_widget[name=foo] input", "zop");
        await click(target.querySelector(".modal-footer .o_form_button_save"));

        // client-side sort
        assert.deepEqual(getFooValues(), ["zop", "yop", "xop", "My little Foo Value"]);

        // server-side sort
        await clickSave(target);
        assert.deepEqual(getFooValues(), ["zop", "yop", "xop", "My little Foo Value"]);

        // client-side sort on edit
        await click(target.querySelectorAll(".o_data_row")[1].querySelector(".o_data_cell"));
        await editInput(target, ".modal .o_field_widget[name=foo] input", "zzz");
        await click(target.querySelector(".modal-footer .o_form_button_save"));
        assert.deepEqual(getFooValues(), ["zzz", "zop", "xop", "My little Foo Value"]);
    });

    QUnit.test("action context is used when evaluating domains", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" domain="[('id', 'in', context.get('product_ids', []))]"/>
                </form>`,
            resId: 1,
            context: { product_ids: [45, 46, 47] },
            mockRPC(route, args) {
                if (args.method === "name_search") {
                    assert.deepEqual(
                        args.kwargs.args[0],
                        ["id", "in", [45, 46, 47]],
                        "domain should be properly evaluated"
                    );
                }
            },
        });
        await click(target.querySelector('.o_field_widget[name="trululu"] input'));
    });

    QUnit.test("form rendering with groups with col/colspan", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                                    <field name="qux"/>
                                    <field name="int_field" colspan="3" nolabel="1"/>
                                    <span/>
                                    <field name="product_id"/>
                                </group>
                            </group>
                        </group>
                        <group>
                            <field name="p">
                                <tree>
                                    <field name="display_name"/>
                                    <field name="foo"/>
                                    <field name="int_field"/>
                                </tree>
                            </field>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        var $parentGroup = $(target.querySelector(".parent_group"));
        var $group4 = $(target.querySelector(".group_4"));
        var $group3 = $(target.querySelector(".group_3"));
        var $group1 = $(target.querySelector(".group_1"));
        var $fieldGroup = $(target.querySelector(".field_group"));

        // Verify outergroup/innergroup
        assert.strictEqual($parentGroup[0].tagName, "DIV", ".parent_group should be an outergroup");
        assert.strictEqual($group4[0].tagName, "DIV", ".group_4 should be an innergroup");
        assert.strictEqual($group3[0].tagName, "DIV", ".group_3 should be an outergroup");
        assert.strictEqual($group1[0].tagName, "DIV", ".group_1 should be an innergroup");
        assert.strictEqual($fieldGroup[0].tagName, "DIV", ".field_group should be an innergroup");

        // Verify .parent_group content
        var $parentGroupChildren = $parentGroup.children();
        assert.strictEqual(
            $parentGroupChildren.length,
            2,
            "there should be 2 groups in .parent_group"
        );
        assert.ok(
            $parentGroupChildren.eq(0).is(".col-lg-6"),
            "first .parent_group group should be 1/2 parent width"
        );
        assert.ok(
            $parentGroupChildren.eq(1).is(".col-lg-8"),
            "second .parent_group group should be 3/4 parent width"
        );

        // Verify .group_4 content
        var $group4rows = $group4.find("> div.o_wrap_field");
        assert.strictEqual($group4rows.length, 3, "there should be 3 rows in .group_4");
        var $group4firstRowTd = $group4rows.eq(0).children("div.o_cell");
        assert.strictEqual($group4firstRowTd.length, 1, "there should be 1 cell in first row");
        assert.strictEqual(
            $group4firstRowTd.attr("style").substr(0, 19),
            "grid-column: span 3",
            "the first cell column span should be 3"
        );
        assert.strictEqual(
            $group4firstRowTd.attr("style").substr(0, 19),
            "grid-column: span 3",
            "the first cell should be 75% width"
        );
        assert.strictEqual(
            $group4firstRowTd.children()[0].tagName,
            "DIV",
            "the first cell should contain a div"
        );
        var $group4secondRowTds = $group4rows.eq(1).children("div.o_cell");
        assert.strictEqual($group4secondRowTds.length, 2, "there should be 2 cells in second row");
        assert.strictEqual(
            $group4secondRowTds.attr("style").substr(0, 29),
            "grid-column: span 2;width: 50",
            "the first cell colspan should be 2 and be 50% width"
        );
        assert.strictEqual(
            $group4secondRowTds.eq(1).attr("style").substr(0, 9),
            "width: 25",
            "the second cell colspan should be default one (no style) and be 25% width"
        );
        var $group4thirdRowTd = $group4rows.eq(2).children(".o_cell");
        assert.strictEqual($group4thirdRowTd.length, 1, "there should be 1 cell in third row");
        assert.strictEqual(
            $group4thirdRowTd.attr("style").substr(0, 30),
            "grid-column: span 4;width: 100",
            "the first cell colspan should be 4 and be 100% width"
        );

        // Verify .group_3 content
        assert.strictEqual($group3.children().length, 3, ".group_3 should have 3 children");
        assert.strictEqual(
            $group3.children(".col-lg-4").length,
            3,
            ".group_3 should have 3 children of 1/3 width"
        );

        // Verify .group_1 content
        assert.strictEqual(
            $group1.find("> .o_wrap_field").length,
            3,
            "there should be 3 rows in .group_1"
        );

        // Verify .field_group content
        var $fieldGroupRows = $fieldGroup.find("> .o_wrap_field");
        assert.strictEqual($fieldGroupRows.length, 5, "there should be 5 rows in .o_wrap_field");
        var $fieldGroupFirstRowTds = $fieldGroupRows.eq(0).find(".o_cell");
        assert.strictEqual(
            $fieldGroupFirstRowTds.length,
            2,
            "there should be 2 cells in first row"
        );
        assert.hasClass(
            $fieldGroupFirstRowTds.eq(0),
            "o_wrap_label",
            "first cell should be a label cell"
        );
        assert.strictEqual(
            $fieldGroupFirstRowTds.eq(1).attr("style").substr(0, 30),
            "grid-column: span 2;width: 100",
            "second cell colspan should be given colspan (3) - 1 (label) and be 100%"
        );
        var $fieldGroupSecondRowTds = $fieldGroupRows.eq(1).children(".o_cell");
        assert.strictEqual(
            $fieldGroupSecondRowTds.length,
            2,
            "there should be 2 cells in second row"
        );
        assert.strictEqual(
            $fieldGroupSecondRowTds.eq(0).attr("style").substr(0, 9),
            "width: 33",
            "first cell colspan should be default one (no style) and be 33.3333%"
        );
        assert.strictEqual(
            $fieldGroupSecondRowTds.eq(1).attr("style").substr(0, 9),
            "width: 33",
            "second cell colspan should be default one (no style) and be 33.3333%"
        );
        var $fieldGroupThirdRowTds = $fieldGroupRows.eq(2).find(".o_cell"); // new row as label/field pair colspan is greater than remaining space
        assert.strictEqual(
            $fieldGroupThirdRowTds.length,
            2,
            "there should be 2 cells in third row"
        );
        assert.hasClass(
            $fieldGroupThirdRowTds.eq(0),
            "o_wrap_label",
            "first cell should be a label cell"
        );
        assert.strictEqual(
            $fieldGroupThirdRowTds.eq(1).attr("style").substr(0, 9),
            "width: 50",
            "second cell colspan should be default one (no style) and be 50% width"
        );
        var $fieldGroupFourthRowTds = $fieldGroupRows.eq(3).children(".o_cell");
        assert.strictEqual(
            $fieldGroupFourthRowTds.length,
            1,
            "there should be 1 cell in fourth row"
        );
        assert.strictEqual(
            $fieldGroupFourthRowTds.attr("style").substr(0, 30),
            "grid-column: span 3;width: 100",
            "the cell should have a colspan equal to 3 and have 100% width"
        );
        var $fieldGroupFifthRowTds = $fieldGroupRows.eq(4).find(".o_cell"); // label/field pair can be put after the 1-colspan span
        assert.strictEqual(
            $fieldGroupFifthRowTds.length,
            3,
            "there should be 3 cells in fourth row"
        );
        assert.strictEqual(
            $fieldGroupFifthRowTds.eq(0).attr("style").substr(0, 9),
            "width: 50",
            "the first cell should 50% width"
        );
        assert.hasClass(
            $fieldGroupFifthRowTds.eq(1),
            "o_wrap_label",
            "the second cell should be a label cell"
        );
        assert.strictEqual(
            $fieldGroupFifthRowTds.eq(2).attr("style").substr(0, 9),
            "width: 50",
            "the third cell should 50% width"
        );
    });

    QUnit.test(
        "form rendering innergroup: separator should take one line",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
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
                </form>`,
                resId: 1,
            });

            const rows = document.querySelectorAll(".o_inner_group > div");
            assert.containsOnce(rows[0], "> .o_cell", "Should only contain one cell");
            assert.containsOnce(rows[0], ".o_horizontal_separator");
            assert.containsN(rows[1], "> .o_cell", 2, "Should contain 2 cells");
            assert.containsOnce(rows[1], "label[for=display_name_0]");
            assert.containsOnce(rows[1], "div[name=display_name]");
        }
    );

    QUnit.test("outer and inner groups string attribute", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                </form>`,
            resId: 1,
        });

        var $parentGroup = $(target.querySelector(".parent_group"));
        var $group1 = $(target.querySelector(".group_1"));
        var $group2 = $(target.querySelector(".group_2"));
        assert.containsN(target, "div.o_inner_group", 2, "should contain two inner groups");
        assert.strictEqual(
            $group1.find(".o_horizontal_separator").length,
            1,
            "inner group should contain one string separator"
        );
        assert.strictEqual(
            $group1.find(".o_horizontal_separator:contains(child group 1)").length,
            1,
            "first inner group should contain 'child group 1' string"
        );
        assert.strictEqual(
            $group2.find(".o_horizontal_separator:contains(child group 2)").length,
            1,
            "second inner group should contain 'child group 2' string"
        );
        assert.strictEqual(
            $parentGroup.find("> div.o_horizontal_separator:contains(parent group)").length,
            1,
            "outer group should contain 'parent group' string"
        );
    });

    QUnit.test("inner group with invisible cells", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
            <form>
                <field name="foo" />
                <group>
                    <div class="cell1" invisible='foo == "1"' />
                    <div class="cell2" invisible='foo == "2"' />
                </group>
            </form>`,
        });

        await editInput(target, "[name='foo'] input", 1);
        assert.containsOnce(target, ".o_wrap_field");
        assert.containsNone(target, ".o_wrap_field .cell1");
        assert.containsOnce(target, ".o_wrap_field .cell2");

        await editInput(target, "[name='foo'] input", 2);
        assert.containsOnce(target, ".o_wrap_field");
        assert.containsOnce(target, ".o_wrap_field .cell1");
        assert.containsNone(target, ".o_wrap_field .cell2");

        await editInput(target, "[name='foo'] input", 3);
        assert.containsOnce(target, ".o_wrap_field");
        assert.containsOnce(target, ".o_wrap_field .cell1");
        assert.containsOnce(target, ".o_wrap_field .cell2");
    });

    QUnit.test("form group with newline tag inside", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
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
                            <field name="qux"/>
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
                </form>`,
            resId: 1,
        });

        // Inner group
        assert.containsN(
            target,
            ".main_inner_group > .o_wrap_field",
            2,
            "there should be 2 rows in the group"
        );
        assert.containsOnce(
            target,
            ".main_inner_group > .o_wrap_field:first > .o_wrap_label",
            "there should be only one label in the first row"
        );
        assert.containsOnce(
            target,
            ".main_inner_group > .o_wrap_field:first .o_field_widget",
            "there should be only one widget in the first row"
        );
        assert.containsN(
            target,
            ".main_inner_group > .o_wrap_field:last .o_wrap_label",
            2,
            "there should be two labels in the second row"
        );
        assert.containsN(
            target,
            ".main_inner_group > .o_wrap_field:last .o_field_widget",
            2,
            "there should be two widgets in the second row"
        );

        // Outer group
        const bottomGroupRect = target.querySelector(".bottom_group").getBoundingClientRect();
        const topGroupRect = target.querySelector(".top_group").getBoundingClientRect();

        assert.ok(
            bottomGroupRect.top - topGroupRect.top >= 200,
            "outergroup children should not be on the same line"
        );
    });

    QUnit.test("custom open record dialog title", async function (assert) {
        serverData.models.partner.records[0].p = [2];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" widget="many2many" string="custom label">
                        <tree><field name="display_name"/></tree>
                        <form><field name="display_name"/></form>
                    </field>
                </form>`,
            resId: 1,
        });

        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal .modal-title").textContent,
            "Open: custom label"
        );
    });

    QUnit.test("can save without any dirty translatable fields", async function (assert) {
        serverData.models.partner.fields.foo.translate = true;

        patchWithCleanup(localization, {
            multiLang: true,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        assert.verifySteps(["get_views", "web_read"]);
        assert.containsOnce(target, ".o_form_editable");
        // o_field_translate is on the input and on the translate button
        assert.containsN(target, "div[name='foo'] > .o_field_translate", 2);
        await clickSave(target);
        assert.containsNone(
            target,
            ".alert .o_field_translate",
            "should not have a translation alert"
        );
        assert.containsOnce(target, ".o_form_saved");
        assert.verifySteps([]);
    });

    QUnit.test("translation dialog with right context and domain", async function (assert) {
        serverData.models.partner.fields.foo.translate = true;

        patchWithCleanup(localization, {
            multiLang: true,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "get_installed") {
                    return [
                        ["CUST", "custom lang"],
                        ["CUST2", "second custom"],
                    ];
                }
                if (route === "/web/dataset/call_kw/partner/get_field_translations") {
                    assert.step(`translate args ${JSON.stringify(args.args)}`);
                    assert.step(`translate context ${JSON.stringify(args.kwargs.context)}`);
                    return Promise.resolve([
                        [
                            { lang: "CUST", source: "yop", value: "yop" },
                            { lang: "CUST2", source: "yop", value: "valeur français" },
                        ],
                        { translation_type: "char", translation_show_source: false },
                    ]);
                }
            },
        });

        await click(target, ".o_field_translate.btn-link");
        assert.verifySteps([
            `translate args [[1],"foo"]`,
            `translate context {"lang":"en","uid":7,"tz":"taht"}`,
        ]);

        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal-title").textContent, "Translate: foo");
    });

    QUnit.test("save new record before opening translate dialog", async function (assert) {
        serverData.models.partner.fields.foo.translate = true;

        patchWithCleanup(localization, {
            multiLang: true,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
                if (route === "/web/dataset/call_button") {
                    return { context: {}, domain: [] };
                }
                if (args.method === "get_installed") {
                    return [
                        ["CUST", "custom lang"],
                        ["CUST2", "second custom"],
                    ];
                }
                if (route === "/web/dataset/call_kw/partner/get_field_translations") {
                    return Promise.resolve([
                        [
                            { lang: "CUST", source: "yop", value: "yop" },
                            { lang: "CUST2", source: "yop", value: "valeur français" },
                        ],
                        { translation_type: "char", translation_show_source: false },
                    ]);
                }
            },
        });

        assert.verifySteps(["get_views", "onchange"]);
        assert.containsOnce(target, ".o_form_editable");
        await click(target, ".o_field_translate.btn-link");
        assert.verifySteps(["web_save", "get_installed", "get_field_translations"]);
        assert.containsOnce(target, ".modal");
        assert.strictEqual(target.querySelector(".modal-title").textContent, "Translate: foo");
    });

    QUnit.test(
        "translate event correctly handled with multiple controllers",
        async function (assert) {
            assert.expect(3);

            serverData.models.product.fields.name.translate = true;
            serverData.models.partner.records[0].product_id = 37;
            let nbTranslateCalls = 0;

            patchWithCleanup(localization, {
                multiLang: true,
            });

            serverData.views = {
                "product,false,form": `
                    <form>
                        <sheet>
                            <group>
                                <field name="name"/>
                                <field name="partner_type_id"/>
                            </group>
                        </sheet>
                    </form>`,
            };

            await makeViewInDialog({
                type: "form",
                serverData,
                resModel: "partner",
                resId: 1,
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="product_id"/>
                            </group>
                        </sheet>
                    </form>`,

                mockRPC(route, args) {
                    if (route === "/web/dataset/call_kw/product/get_formview_id") {
                        return false;
                    }
                    if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                        return [
                            ["en_US", "English"],
                            ["fr_BE", "French (Belgium)"],
                        ];
                    }
                    if (route === "/web/dataset/call_kw/product/get_field_translations") {
                        nbTranslateCalls++;
                        return Promise.resolve([
                            [
                                { lang: "en_US", source: "yop", value: "yop" },
                                { lang: "fr_BE", source: "yop", value: "valeur français" },
                            ],
                            { translation_type: "char", translation_show_source: false },
                        ]);
                    }
                },
            });

            assert.containsOnce(target, ".o_dialog");

            await click(target.querySelector('[name="product_id"] .o_external_button'));
            assert.containsOnce(
                target.querySelector(".o_dialog:not(.o_inactive_modal)"),
                "span.o_field_translate",
                "there should be a translate button in the modal"
            );

            await click(
                target.querySelector(".o_dialog:not(.o_inactive_modal) span.o_field_translate")
            );
            assert.strictEqual(nbTranslateCalls, 1, "should call_button translate once");
        }
    );

    QUnit.test("buttons are disabled until status bar action is resolved", async function (assert) {
        const def = makeDeferred();
        const actionService = {
            start() {
                return {
                    async doActionButton(args) {
                        await def;
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="post" class="p" string="Confirm" type="object"/>
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
                </form>`,
            resId: 1,
        });
        // Contains invisible buttons that are only displayed under xl screens
        assert.containsN(
            target,
            ".o_control_panel_breadcrumbs button:not(.fa):not(:disabled)",
            5,
            "control panel buttons should be enabled"
        );
        assert.containsN(
            target,
            ".o_form_statusbar button:not(:disabled)",
            2,
            "status bar buttons should be enabled"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox button:not(:disabled)",
            "stat buttons should be enabled"
        );

        await click(target.querySelector(".o_form_statusbar button"));
        await nextTick();

        // The unresolved promise lets us check the state of the buttons
        assert.containsN(
            target,
            ".o_control_panel_breadcrumbs button:not(.fa):disabled",
            5,
            "control panel buttons should be disabled"
        );
        assert.containsN(
            target,
            ".o_form_statusbar button:disabled",
            2,
            "status bar buttons should be disabled"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox button:disabled",
            "stat buttons should be disabled"
        );

        def.resolve();
        await nextTick();
        assert.containsN(
            target,
            ".o_control_panel_breadcrumbs button:not(.fa):not(:disabled)",
            5,
            "control panel buttons should be enabled"
        );
        assert.containsN(
            target,
            ".o_form_statusbar button:not(:disabled)",
            2,
            "status bar buttons should be enabled"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox button:not(:disabled)",
            "stat buttons should be enabled"
        );
    });

    QUnit.test("buttons are disabled until button box action is resolved", async function (assert) {
        const def = makeDeferred();
        const actionService = {
            start() {
                return {
                    async doActionButton(args) {
                        await def;
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="post" class="p" string="Confirm" type="object"/>
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
                </form>`,
            resId: 1,
        });

        assert.containsN(
            target,
            ".o_control_panel_breadcrumbs button:not(.fa):not(:disabled)",
            5,
            "control panel buttons should be enabled"
        );
        assert.containsN(
            target,
            ".o_form_statusbar button:not(:disabled)",
            2,
            "status bar buttons should be enabled"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox button:not(:disabled)",
            "stat buttons should be enabled"
        );

        await click(target.querySelector(".o-form-buttonbox button"));

        // The unresolved promise lets us check the state of the buttons
        assert.containsN(
            target,
            ".o_control_panel_breadcrumbs button:not(.fa):disabled",
            5,
            "control panel buttons should be disabled"
        );
        assert.containsN(
            target,
            ".o_form_statusbar button:disabled",
            2,
            "status bar buttons should be disabled"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox button:disabled",
            "stat buttons should be disabled"
        );
        def.resolve();

        await nextTick();
        assert.containsN(
            target,
            ".o_control_panel_breadcrumbs button:not(.fa):not(:disabled)",
            5,
            "control panel buttons should be enabled"
        );
        assert.containsN(
            target,
            ".o_form_statusbar button:not(:disabled)",
            2,
            "status bar buttons should be enabled"
        );
        assert.containsOnce(
            target,
            ".o-form-buttonbox button:not(:disabled)",
            "stat buttons should be enabled"
        );
    });

    QUnit.test(
        'buttons with "confirm" attribute save before calling the method',
        async function (assert) {
            const actionService = {
                start() {
                    return {
                        async doActionButton(args) {
                            assert.step("execute_action");
                        },
                    };
                },
            };
            registry.category("services").add("action", actionService, { force: true });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <button name="post" class="p" string="Confirm" type="object" confirm="Very dangerous. U sure?"/>
                        </header>
                        <sheet>
                            <field name="foo"/>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            // click on button, and cancel in confirm dialog
            await click(target.querySelector(".o_statusbar_buttons button"));
            assert.ok(
                target.querySelector(".o_statusbar_buttons button").disabled,
                "button should be disabled"
            );
            await click(target.querySelector(".modal-footer button.btn-secondary"));
            assert.notOk(
                target.querySelector(".o_statusbar_buttons button").disabled,
                "button should no longer be disabled"
            );

            assert.verifySteps(["get_views", "onchange"]);

            // click on button, and click on ok in confirm dialog
            await click(target.querySelector(".o_statusbar_buttons button"));
            assert.verifySteps([]);
            await click(target.querySelector(".modal-footer button.btn-primary"));
            assert.verifySteps(["web_save", "execute_action"]);
        }
    );

    QUnit.test(
        'buttons with "confirm-title" and "confirm-label" attributes',
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <button name="post" class="p" string="Confirm" type="object" confirm="Very dangerous. U sure?"
                                confirm-title="Confirm Title" confirm-label="Confirm Label"/>
                        </header>
                        <sheet>
                            <field name="foo"/>
                        </sheet>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            await click(target.querySelector(".o_statusbar_buttons button"));
            assert.strictEqual(
                target.querySelector(".modal-title").textContent,
                "Confirm Title",
                "confirmation dialog should have correct title"
            );
            assert.strictEqual(
                target.querySelector(".modal-footer button.btn-primary").textContent,
                "Confirm Label",
                "confirmation dialog should have correct confirmation label"
            );

            assert.verifySteps(["get_views", "onchange"]);
        }
    );

    QUnit.test('buttons with "confirm" attribute: click twice on "Ok"', async function (assert) {
        const actionService = {
            start() {
                return {
                    async doActionButton(args) {
                        assert.step("execute_action"); // should be called only once
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="post" class="p" string="Confirm" type="object" confirm="U sure?"/>
                    </header>
                </form>`,
            mockRPC: function (route, args) {
                assert.step(args.method);
            },
        });

        assert.verifySteps(["get_views", "onchange"]);

        await click(target.querySelector(".o_statusbar_buttons button"));
        assert.verifySteps([]);

        click(target.querySelector(".modal-footer button.btn-primary"));
        await Promise.resolve();
        assert.ok(target.querySelector(".modal-footer button.btn-primary").disabled);
        await nextTick();
        assert.verifySteps(["web_save", "execute_action"]);
    });

    QUnit.test(
        "buttons are disabled until action is resolved (in dialogs)",
        async function (assert) {
            const def = makeDeferred();
            const actionService = {
                start() {
                    return {
                        doActionButton(args) {
                            return def;
                        },
                    };
                },
            };
            registry.category("services").add("action", actionService, { force: true });

            serverData.views = {
                "partner,false,form": `
                    <form>
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
                    </form>`,
            };
            await makeViewInDialog({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="trululu"/></form>`,
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "get_formview_id") {
                        return Promise.resolve(false);
                    }
                },
            });

            await click(target.querySelector(".o_external_button"));
            assert.notOk(target.querySelector(".modal .o-form-buttonbox button").disabled);

            await click(target.querySelector(".modal .o-form-buttonbox button"));
            assert.ok(target.querySelector(".modal .o-form-buttonbox button").disabled);

            def.resolve();
            await nextTick();
            assert.notOk(target.querySelector(".modal .o-form-buttonbox button").disabled);
        }
    );

    QUnit.test("multiple clicks on save should reload only once", async function (assert) {
        const def = makeDeferred();

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_save") {
                    return def;
                }
            },
        });

        await editInput(target, '.o_field_widget[name="foo"] input', "test");
        await clickSave(target);
        assert.ok(target.querySelector(".o_form_button_save").disabled); // Save button is disabled, it can't be clicked

        def.resolve();
        await nextTick();
        assert.verifySteps([
            "get_views",
            "web_read", // initial read to render the view
            "web_save", // write on save
        ]);
    });

    QUnit.test("form view is not broken if save operation fails", async function (assert) {
        registry.category("services").add("error", errorService);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            resId: 1,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_save" && args.args[1].foo === "incorrect value") {
                    throw makeServerError();
                }
            },
        });

        await editInput(target, ".o_field_widget[name=foo] input", "incorrect value");
        await clickSave(target);
        await nextTick();
        assert.containsOnce(target, ".o_dialog", "should display an error dialog");
        await click(target.querySelector(".o_dialog .modal-footer .btn-primary")); // close it
        await editInput(target, ".o_field_widget[name=foo] input", "correct value");
        await clickSave(target);

        assert.verifySteps([
            "get_views",
            "web_read", // initial read to render the view
            "web_save", // write on save (it fails, does not trigger a read)
            "web_save", // write on save (it works)
        ]);
    });

    QUnit.test(
        "form view is not broken if save failed in readonly mode on field changed",
        async function (assert) {
            registry.category("services").add("error", errorService);
            let failFlag = false;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <header>
                            <field name="trululu" widget="statusbar" options="{'clickable': '1'}"/>
                        </header>
                    </form>`,
                mode: "readonly",
                resId: 1,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.step("web_save");
                        if (failFlag) {
                            throw makeServerError();
                        }
                    } else if (args.method === "web_read") {
                        assert.step("web_read");
                    }
                },
            });

            assert.hasClass(
                target.querySelector('button[data-value="4"]'),
                "o_arrow_button_current"
            );
            assert.ok(target.querySelector('button[data-value="4"]').disabled);

            failFlag = true;
            await click(target.querySelector('button[data-value="1"]'));
            assert.hasClass(
                target.querySelector('button[data-value="4"]'),
                "o_arrow_button_current",
                "initial status should still be active as save failed"
            );

            failFlag = false;
            await click(target.querySelector('button[data-value="1"]'));
            assert.hasClass(
                target.querySelector('button[data-value="1"]'),
                "o_arrow_button_current",
                "last clicked status should be active"
            );

            assert.verifySteps([
                "web_read",
                "web_save", // fails
                "web_read", // must reload when saving fails
                "web_save", // works
            ]);
        }
    );

    QUnit.test(
        "context is correctly passed after save & new in FormViewDialog",
        async function (assert) {
            assert.expect(3);

            serverData.views = {
                "product,false,form": `
                    <form>
                        <field name="partner_type_id" context="{'color': parent.id}"/>
                    </form>`,
                "product,false,list": '<tree><field name="display_name"/></tree>',
            };
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 4,
                serverData,
                arch: `<form><field name="product_ids"/></form>`,
                mockRPC(route, args) {
                    if (args.method === "name_search") {
                        assert.strictEqual(args.kwargs.context.color, 4);
                    }
                },
            });
            await click(target.querySelector(".o_field_x2many_list_row_add a"));
            assert.containsOnce(target, ".modal");

            // set a value on the m2o and click save & new
            await selectDropdownItem(target, "partner_type_id", "gold");
            await click(target.querySelector(".modal-footer .o_form_button_save_new"));

            // set a value on the m2o
            await selectDropdownItem(target, "partner_type_id", "silver");
            await click(target.querySelector(".modal-footer .o_form_button_save"));
        }
    );

    QUnit.test("readonly fields are not sent when saving", async function (assert) {
        assert.expect(6);

        // define an onchange on display_name to check that the value of readonly
        // fields is correctly sent for onchanges
        serverData.models.partner.onchanges = {
            display_name: function () {},
            p: function () {},
        };
        let checkOnchange = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree><field name="display_name"/></tree>
                        <form>
                            <field name="display_name"/>
                            <field name="foo" readonly="display_name == 'readonly'"/>
                        </form>
                    </field>
                </form>`,
            mockRPC(route, args) {
                if (checkOnchange && args.method === "onchange") {
                    if (args.args[2][0] === "display_name") {
                        // onchange on field display_name
                        assert.strictEqual(
                            args.args[1].foo,
                            "foo value",
                            "readonly fields value should be sent for onchanges"
                        );
                    } else {
                        // onchange on field p
                        assert.deepEqual(
                            args.args[1].p,
                            [
                                [
                                    0,
                                    args.args[1].p[0][1],
                                    { display_name: "readonly", foo: "foo value" },
                                ],
                            ],
                            "readonly fields value should be sent for onchanges"
                        );
                    }
                }
                if (args.method === "web_save") {
                    assert.deepEqual(
                        args.args[1],
                        {
                            p: [[0, args.args[1].p[0][1], { display_name: "readonly" }]],
                        },
                        "should not have sent the value of the readonly field"
                    );
                }
            },
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.containsOnce(
            target,
            ".modal .o_field_widget[name=foo] input",
            "foo should be editable"
        );
        checkOnchange = true;
        await editInput(target, ".modal .o_field_widget[name=foo] input", "foo value");
        await editInput(target, ".modal .o_field_widget[name=display_name] input", "readonly");
        assert.containsNone(
            target,
            ".modal .o_field_widget[name=foo] input",
            "foo should be readonly"
        );
        await click(target.querySelector(".modal-footer .btn-primary"));

        checkOnchange = false;
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=foo]").textContent,
            "foo value",
            "the edited value should have been kept"
        );
        await click(target.querySelector(".modal-footer .btn-primary"));

        await clickSave(target);
    });

    QUnit.test("id is False in evalContext for new records", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="id"/>
                    <field name="foo" readonly="not id"/>
                </form>`,
        });

        assert.hasClass(
            target.querySelector(".o_field_widget[name=foo]"),
            "o_readonly_modifier",
            "foo should be readonly in 'Create' mode"
        );

        await clickSave(target);

        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget[name=foo]"),
            "o_readonly_modifier",
            "foo should not be readonly anymore"
        );
    });

    QUnit.test("delete a duplicated record", async function (assert) {
        assert.expect(5);

        const newRecordID = 6; // ids from 1 to 5 are already taken so the new record will have id 6
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="display_name"/></form>`,
            resId: 1,
            actionMenus: {},
            mockRPC(route, args) {
                if (args.method === "unlink") {
                    assert.deepEqual(args.args[0], [newRecordID]);
                }
            },
        });

        // duplicate record 1
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Duplicate");

        assert.containsOnce(target, ".o_form_editable", "form should be in edit mode");
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "first record (copy)",
            "duplicated record should have correct name"
        );
        await clickSave(target); // save duplicated record

        // delete duplicated record
        await toggleActionMenu(target);
        await toggleMenuItem(target, "Delete");

        assert.containsOnce(target, ".modal", "should have opened a confirm dialog");
        await click(target.querySelector(".modal-footer .btn-primary"));

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "first record",
            "should have come back to previous record"
        );
    });

    QUnit.test("display tooltips for buttons (debug = false)", async function (assert) {
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="some_method" class="oe_highlight" string="Button" type="object" title="This is title"/>
                        <button name="empty_method" string="Empty Button" type="object"/>
                    </header>
                    <button name="other_method" class="oe_highlight" string="Button2" type="object" help="help Button2"/>
                </form>`,
        });

        await mouseEnter(target.querySelector("button[name='empty_method']"));
        await nextTick();
        assert.containsNone(target, ".o-tooltip", "not help, or not title, not tooltip");

        await mouseEnter(target.querySelector("button[name='some_method']"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip").textContent,
            "This is title",
            "title on default tooltip"
        );

        await mouseEnter(target.querySelector("button[name='other_method']"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip").textContent,
            "Button2help Button2",
            "help create veiw button tooltip with the name of the button as title and the help as description"
        );
    });

    QUnit.test("display tooltips for buttons (debug = true)", async function (assert) {
        patchWithCleanup(odoo, {
            debug: true,
        });

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                        <button name="some_method" class="oe_highlight" string="Button" type="object" title="This is title" readonly="display_name == 'readonly'"/>
                        <button name="empty_method" string="Empty Button" type="object"/>
                    </header>
                    <button name="other_method" class="oe_highlight" string="Button2" type="object" help="help Button2"/>
                </form>`,
        });

        await mouseEnter(target.querySelector("button[name='empty_method']"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip").textContent,
            ` Button : Empty ButtonObject:partnerButton Type:objectMethod:empty_method`
        );

        await mouseEnter(target.querySelector("button[name='some_method']"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip").textContent,
            ` Button : ButtonThis is titleObject:partnerReadonly:display_name == 'readonly'Button Type:objectMethod:some_method`
        );

        await mouseEnter(target.querySelector("button[name='other_method']"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip").textContent,
            ` Button : Button2help Button2Object:partnerButton Type:objectMethod:other_method`
        );
    });

    QUnit.test("reload event is handled only once", async function (assert) {
        // In this test, several form controllers are nested (all of them are
        // opened in dialogs). When the users clicks on save in the last
        // opened dialog, a 'reload' event is triggered up to reload the (direct)
        // parent view. If this event isn't stopPropagated by the first controller
        // catching it, it will crash when the other one will try to handle it,
        // as this one doesn't know at all the dataPointID to reload.
        const arch = `<form><field name="display_name"/><field name="trululu"/></form>`;
        serverData.views = {
            "partner,false,form": arch,
        };
        await makeViewInDialog({
            type: "form",
            resModel: "partner",
            serverData,
            arch: arch,
            resId: 2,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });

        assert.containsOnce(target, ".o_dialog");
        await click(target.querySelector(".o_external_button"));
        assert.containsN(target, ".o_dialog", 2);
        await click(target.querySelector(".o_dialog:not(.o_inactive_modal) .o_external_button"));
        assert.containsN(target, ".o_dialog", 3);

        await editInput(
            target.querySelectorAll(".modal")[2],
            ".o_field_widget[name=display_name] input",
            "new name"
        );
        await click(
            target.querySelectorAll(".modal")[2].querySelector("footer .o_form_button_save")
        );

        assert.strictEqual(
            target
                .querySelectorAll(".modal")[1]
                .querySelector(".o_field_widget[name=trululu] input").value,
            "new name",
            "record should have been reloaded"
        );
        assert.verifySteps([
            "get_views",
            "web_read", // main record
            "get_formview_id", // id of first form view opened in a dialog
            "get_views", // arch of first form view opened in a dialog
            "web_read", // first dialog
            "get_formview_id", // id of second form view opened in a dialog
            "web_read", // second dialog
            "web_save", // save second dialog
            "read", // reload the display_name (first dialog)
        ]);
    });

    QUnit.test("process the context for inline subview", async function (assert) {
        serverData.models.partner.records[0].p = [2];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree>
                            <field name="foo"/>
                            <field name="bar" column_invisible="context.get('hide_bar', False)"/>
                            <field name="int_field" column_invisible="True"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            context: { hide_bar: true },
        });
        assert.containsOnce(
            target,
            ".o_list_renderer thead tr th:not(.o_list_actions_header)",
            "there should be only one column"
        );
    });

    QUnit.test("process the context for subview not inline", async function (assert) {
        serverData.models.partner.records[0].p = [2];

        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="foo"/>
                    <field name="bar" column_invisible="context.get('hide_bar', False)"/>
                </tree>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="p" widget="one2many"/></form>`,
            resId: 1,
            context: { hide_bar: true },
        });
        assert.containsOnce(
            target,
            ".o_list_renderer thead tr th:not(.o_list_actions_header)",
            "there should be only one column"
        );
    });

    QUnit.test("Can switch to form view on inline tree", async function (assert) {
        const id = 2;
        const actionService = {
            start() {
                return {
                    doAction(action, options) {
                        assert.step("doAction");
                        assert.deepEqual(action, {
                            res_id: id,
                            res_model: "partner",
                            type: "ir.actions.act_window",
                            views: [[false, "form"]],
                        });
                        assert.deepEqual(options.props, {
                            resIds: [id],
                        });
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        serverData.models.partner.records[0].p = [id];
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p">
                        <tree editable="top" open_form_view="1">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
        });
        assert.containsOnce(
            target,
            "td.o_list_record_open_form_view",
            "button to open form view should be present"
        );
        await click(target.querySelector("td.o_list_record_open_form_view"));
        assert.verifySteps(["doAction"]);
    });

    QUnit.test("can toggle column in x2many in sub form view", async function (assert) {
        serverData.models.partner.records[2].p = [1, 2];
        serverData.models.partner.fields.foo.sortable = true;
        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="p">
                        <tree><field name="foo"/></tree>
                    </field>
                </form>`,
        };
        await makeViewInDialog({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="trululu"/></form>`,
            resId: 1,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/partner/get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });
        await click(target.querySelector(".o_external_button"));
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".o_dialog:not(.o_inactive_modal) .o_data_cell")
            ),
            ["yop", "blip"]
        );

        await click(target.querySelector(".o_dialog:not(.o_inactive_modal) th.o_column_sortable"));
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(".o_dialog:not(.o_inactive_modal) .o_data_cell")
            ),
            ["blip", "yop"]
        );
    });

    QUnit.test("rainbowman attributes correctly passed on button click", async function (assert) {
        assert.expect(1);
        const actionService = {
            start() {
                return {
                    doActionButton(params) {
                        assert.strictEqual(params.effect, "{'message': 'Congrats!'}");
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <header>
                    <button name="action_won" string="Won" type="object" effect="{'message': 'Congrats!'}"/>
                    </header>
                </form>`,
        });

        await click(target.querySelector(".o_form_statusbar .btn-secondary"));
    });

    QUnit.test("basic support for widgets", async function (assert) {
        class MyComponent extends Component {
            static template = xml`<div t-esc="value"/>`;
            get value() {
                return JSON.stringify(this.props.record.data);
            }
        }
        const myComponent = {
            component: MyComponent,
        };
        widgetRegistry.add("test_widget", myComponent);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="bar"/>
                    <widget name="test_widget"/>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_widget").textContent,
            '{"foo":"My little Foo Value","bar":false,"display_name":""}'
        );
    });

    QUnit.test("widget with class attribute", async function (assert) {
        class MyComponent extends Component {
            static template = xml`<span>Hello</span>`;
        }
        const myComponent = {
            component: MyComponent,
        };
        widgetRegistry.add("test_widget", myComponent);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            arch: `
                <form>
                    <widget name="test_widget" class="my_classname"/>
                </form>`,
        });

        assert.containsOnce(target, ".o_widget.my_classname");
    });

    QUnit.test("widget with readonly attribute", async function (assert) {
        class MyComponent extends Component {
            static template = xml`<span t-esc="value"/>`;
            get value() {
                return this.props.readonly ? "readonly" : "not readonly";
            }
        }
        const myComponent = {
            component: MyComponent,
            extractProps(widgetInfo, dynamicInfo) {
                return { readonly: dynamicInfo.readonly };
            },
        };
        widgetRegistry.add("test_widget", myComponent);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            arch: `
                <form>
                    <field name="bar"/>
                    <widget name="test_widget" readonly="bar"/>
                </form>`,
        });

        assert.strictEqual(target.querySelector(".o_widget").textContent, "not readonly");
        await click(target.querySelector(".o_field_widget[name=bar] input"));
        assert.strictEqual(target.querySelector(".o_widget").textContent, "readonly");
    });

    QUnit.test("support header button as widgets on form statusbar", async function (assert) {
        serviceRegistry.add("http", {
            start: () => ({}),
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><header><widget name="attach_document" string="Attach document"/></header></form>`,
        });

        assert.containsOnce(target, "button.o_attachment_button");
        assert.strictEqual(
            target.querySelector("span.o_attach_document").textContent,
            "Attach document"
        );
    });

    QUnit.test("basic support for widgets: onchange update", async function (assert) {
        class MyWidget extends Component {
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
        const myWidget = {
            component: MyWidget,
        };
        widgetRegistry.add("test_widget", myWidget);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/><widget name="test_widget"/></form>`,
        });

        await editInput(target, '.o_field_widget[name="foo"] input', "I am alive");
        await nextTick();

        assert.strictEqual(
            target.querySelector(".o_widget").textContent,
            "I am alive!",
            "widget should have been updated"
        );

        widgetRegistry.remove("test_widget");
    });

    QUnit.test("proper stringification in debug mode tooltip", async function (assert) {
        patchWithCleanup(odoo, { debug: true });

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <field name="product_id" context="{'lang': 'en_US'}" invisible="product_id == 33" widget="many2one"/>
                    </sheet>
                </form>`,
        });

        await mouseEnter(target.querySelector("[name='product_id']"));
        await nextTick();
        assert.containsOnce(
            target,
            ".o-tooltip--technical > li[data-item='context']",
            "context should be present for this field"
        );
        assert.strictEqual(
            target.querySelector('.o-tooltip--technical > li[data-item="context"]').lastChild
                .textContent,
            "{'lang': 'en_US'}",
            "context should be properly stringified"
        );
        assert.containsOnce(
            target,
            ".o-tooltip--technical > li[data-item='invisible']",
            "invisible should be present for this field"
        );
        assert.strictEqual(
            target.querySelector('.o-tooltip--technical > li[data-item="invisible"]').lastChild
                .textContent,
            "product_id == 33",
            "invisible should be properly stringified"
        );

        assert.containsOnce(
            target,
            ".o-tooltip--technical > li[data-item='widget']",
            "widget should be present for this field"
        );
        assert.strictEqual(
            target.querySelector(".o-tooltip--technical > li[data-item=widget]").textContent.trim(),
            "Widget:Many2one (many2one)",
            "widget description should be correct"
        );
    });

    QUnit.test("do not change pager when discarding current record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            resIds: [1, 2],
            resId: 2,
        });

        assert.strictEqual(
            target.querySelector(".o_pager_value").textContent,
            "2",
            "pager should indicate that we are on second record"
        );
        assert.strictEqual(
            target.querySelector(".o_pager_limit").textContent,
            "2",
            "pager should indicate that we are on second record"
        );

        await clickDiscard(target);

        assert.strictEqual(
            target.querySelector(".o_pager_value").textContent,
            "2",
            "pager value should not have changed"
        );
        assert.strictEqual(
            target.querySelector(".o_pager_limit").textContent,
            "2",
            "pager limit should not have changed"
        );
    });

    QUnit.test("coming to a form view from a grouped and sorted list", async function (assert) {
        assert.expect(20);
        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        };
        serverData.views = {
            "partner,false,list": `<tree><field name="foo"/></tree>`,
            "partner,false,search": `
                <search>
                    <filter string="bar" name="Bar" context="{'group_by': 'bar'}"/>
                </search>`,
            "partner,false,form": `
                <form>
                    <field name="foo"/>
                    <field name="timmy"/>
                </form>`,
            "partner_type,false,list": `<tree><field name="display_name"/></tree>`,
        };
        serverData.models.partner.fields.foo.sortable = true;
        serverData.models.partner.records[0].timmy = [12, 14];

        const mockRPC = (route, args) => {
            assert.step(args.model ? args.model + ":" + args.method : route);
            if (args.method === "web_read" && args.model === "partner") {
                assert.deepEqual(args.kwargs.context, {
                    bin_size: true,
                    lang: "en",
                    tz: "taht",
                    uid: 7,
                });
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        assert.containsOnce(target, ".o_list_view");
        assert.containsN(target, ".o_data_row", 4);
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "yop",
            "blip",
            "My little Foo Value",
            "",
        ]);
        await click(target.querySelector("th.o_column_sortable"));

        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "",
            "My little Foo Value",
            "blip",
            "yop",
        ]);

        await toggleSearchBarMenu(target);
        await toggleMenuItem(target, "bar");
        assert.containsN(target, ".o_group_header", 2);
        assert.containsNone(target, ".o_data_row");

        await click(target.querySelectorAll(".o_group_header")[1]);
        assert.containsN(target, ".o_group_header", 2);
        assert.containsN(target, ".o_data_row", 2);

        const secondDataRow = target.querySelectorAll(".o_data_row")[1];
        await click(secondDataRow.querySelector(".o_data_cell"));
        assert.containsOnce(target, ".o_form_view");
        assert.deepEqual(getNodesTextContent(target.querySelectorAll(".o_data_cell")), [
            "gold",
            "silver",
        ]);
        assert.verifySteps([
            "/web/webclient/load_menus",
            "/web/action/load",
            "partner:get_views",
            "partner:web_search_read",
            "partner:web_search_read",
            "partner:web_read_group",
            "partner:web_search_read",
            "partner:web_read",
        ]);
    });

    QUnit.test("keep editing after call_button fail", async function (assert) {
        assert.expect(5);
        assert.expectErrors();

        let values;
        const mockedActionService = {
            start() {
                return {
                    doActionButton(params) {
                        assert.deepEqual(
                            [params.name, params.type],
                            ["post", "object"],
                            "the action should be correctly executed"
                        );
                        throw makeServerError();
                    },
                };
            },
        };
        serviceRegistry.add("action", mockedActionService, { force: true });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <button name="post" class="p" string="Raise Error" type="object"/>
                    <field name="p">
                        <tree editable="top">
                            <field name="display_name"/>
                            <field name="product_id"/>
                        </tree>
                    </field>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1].p[0][2], values);
                }
            },
        });

        // add a row and partially fill it
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await editInput(target, ".o_field_widget[name=display_name] input", "abc");

        // click button which will trigger_up 'execute_action' (this will save)
        values = {
            display_name: "abc",
            product_id: false,
        };
        await click(target.querySelector("button.p"));

        assert.verifyErrors(["Odoo Server Error"]);

        // edit the new row again and set a many2one value
        await click(
            target.querySelectorAll(".o_form_view .o_field_one2many .o_data_row .o_data_cell")[1]
        );
        await nextTick();
        await selectDropdownItem(target, "product_id", "xphone");

        assert.strictEqual(
            target.querySelector(".o_field_many2one input").value,
            "xphone",
            "value of the m2o should have been correctly updated"
        );

        values = {
            product_id: 37,
        };
        await clickSave(target);
    });

    QUnit.test("no deadlock when saving with uncommitted changes", async function (assert) {
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
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/></form>',
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        await editInput(target, ".o_field_widget[name=foo] input", "some foo value");
        await clickSave(target);

        assert.containsOnce(target, ".o_form_editable", "form view should be in edit");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "some foo value",
            "foo field should have correct value"
        );
        assert.verifySteps(["get_views", "onchange", "web_save"]);
    });

    QUnit.test("saving with invalid uncommitted changes", async function (assert) {
        patchWithCleanup(browser, { setTimeout: () => 1 });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="qux"/></form>',
            mockRPC(route, args) {
                assert.step(args.method);
            },
        });

        await editInput(target, ".o_field_widget[name=qux] input", "some qux value");

        await clickSave(target);

        assert.containsOnce(target, ".o_form_editable", "form view should stay in edit mode");
        assert.strictEqual(
            target.querySelector(".o_form_view .o_form_editable input").value,
            "some qux value",
            "qux field should have the invalid value"
        );
        assert.hasClass(target.querySelector("[name=qux]"), "o_field_invalid");
        assert.containsOnce(target, ".o_notification .text-danger");
        assert.containsOnce(target, ".o_form_editable .o_field_invalid[name=qux]");
        assert.verifySteps(["get_views", "onchange"]);
    });

    QUnit.test(
        "save record with onchange on one2many with required field",
        async function (assert) {
            // in this test, we have a one2many with a required field, whose value is
            // set by an onchange on another field ; we manually set the value of that
            // first field, and directly click on Save (before the onchange RPC returns
            // and sets the value of the required field)
            assert.expect(6);

            serverData.models.partner.fields.foo.default = undefined;
            serverData.models.partner.onchanges = {
                display_name: function (obj) {
                    obj.foo = obj.display_name ? "foo value" : undefined;
                },
            };

            let onchangeDef = undefined;
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree editable="top">
                                <field name="display_name"/>
                                <field name="foo" required="1"/>
                            </tree>
                        </field>
                    </form>`,
                async mockRPC(route, args) {
                    if (args.method === "onchange") {
                        await onchangeDef;
                    }
                    if (args.method === "web_save") {
                        assert.step("web_save");
                        assert.strictEqual(
                            args.args[1].p[0][2].foo,
                            "foo value",
                            "should have wait for the onchange to return before saving"
                        );
                    }
                },
            });

            await click(target.querySelector(".o_field_x2many_list_row_add a"));

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=display_name] input").value,
                "",
                "display_name should be the empty string by default"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name=foo] input").value,
                "",
                "foo should be the empty string by default"
            );

            onchangeDef = makeDeferred(); // delay the onchange

            await editInput(target, ".o_field_widget[name=display_name] input", "some value");

            await clickSave(target);

            assert.step("resolve");
            onchangeDef.resolve();
            await nextTick();

            assert.verifySteps(["resolve", "web_save"]);
        }
    );

    QUnit.test("leave the form view while saving", async function (assert) {
        serverData.models.partner.onchanges = {
            foo: function (obj) {
                obj.display_name = obj.foo === "trigger onchange" ? "changed" : "default";
            },
        };

        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        };
        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>`,
            "partner,false,form": `
                <form>
                    <field name="display_name"/>
                    <field name="foo"/>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        let onchangeDef = undefined;
        const createDef = makeDeferred();

        const mockRPC = async (route, args) => {
            if (args.method === "onchange") {
                await onchangeDef;
            }
            if (args.method === "web_save") {
                await createDef;
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);

        await click(target, ".o_control_panel_main_buttons .d-none button.o_list_button_add");

        // edit foo to trigger a delayed onchange
        onchangeDef = makeDeferred();
        await editInput(target, ".o_field_widget[name=foo] input", "trigger onchange");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=display_name] input").value,
            "default"
        );

        // save (will wait for the onchange to return), and will be delayed as well
        await clickSave(target);

        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=display_name] input").value,
            "default"
        );

        // click on the breadcrumbs to leave the form view
        await click(target, ".breadcrumb-item.o_back_button a");
        await nextTick();

        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=display_name] input").value,
            "default"
        );

        // unlock the onchange
        onchangeDef.resolve();
        await nextTick();
        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name=display_name] input").value,
            "changed"
        );

        // unlock the create
        createDef.resolve();
        await nextTick();

        assert.containsOnce(target, ".o_list_view");
        assert.strictEqual(
            target.querySelector(".o_list_table .o_data_row:last-child td.o_data_cell").textContent,
            "changed"
        );
        assert.containsNone(
            document.body,
            ".modal",
            "should not display the 'Changes will be discarded' dialog"
        );
    });

    QUnit.test(
        "leave the form twice (clicking on the breadcrumb) should save only once",
        async function (assert) {
            let writeCalls = 0;
            serverData.actions = {
                1: {
                    id: 1,
                    name: "test",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                },
            };
            serverData.views = {
                "partner,false,list": `<tree><field name="foo"/></tree>`,
                "partner,false,search": `<search></search>`,
                "partner,false,form": `
                    <form>
                        <field name="display_name"/>
                        <field name="foo"/>
                    </form>`,
            };

            const writeDef = makeDeferred();

            const mockRPC = async (route, args) => {
                if (args.method === "web_save") {
                    writeCalls += 1;
                    await writeDef;
                }
            };

            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 1);

            // switch to form view
            await click(target.querySelector(".o_list_table .o_data_row .o_data_cell"));

            assert.containsOnce(target, ".o_form_editable");
            await editInput(target, ".o_field_widget[name=foo] input", "some value");

            await click(target, ".breadcrumb-item.o_back_button a");
            assert.containsNone(document.body, ".modal");

            await click(target, ".breadcrumb-item.o_back_button a");
            assert.containsNone(document.body, ".modal");

            // unlock the create
            writeDef.resolve();
            await nextTick();

            assert.strictEqual(writeCalls, 1, "should save once");
        }
    );

    QUnit.test("discard after a failed save (and close notifications)", async function (assert) {
        patchWithCleanup(browser, { setTimeout: () => 1 });

        serverData.views = {
            "partner,false,form": `
                <form>
                    <field name="date" required="true"/>
                    <field name="foo" required="true"/>
                </form>`,
            "partner,false,kanban": `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            "partner,false,search": "<search></search>",
        };

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        await click(
            target.querySelector(".o_control_panel_main_buttons .d-none button.o-kanban-button-new")
        );

        //cannot save because there is a required field
        await click(target.querySelector(".o_control_panel .o_form_button_save"));
        assert.containsOnce(target, ".o_notification");
        await click(target.querySelector(".o_control_panel .o_form_button_cancel"));
        assert.containsNone(target, ".o_form_view");
        assert.containsOnce(target, ".o_kanban_view");
        assert.containsNone(target, ".o_notification");
    });

    QUnit.test(
        "one2many create record dialog shouldn't have a 'remove' button",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <kanban>
                                <templates>
                                    <t t-name="kanban-box">
                                        <field name="foo"/>
                                    </t>
                                </templates>
                            </kanban>
                            <form>
                                <field name="foo"/>
                            </form>
                        </field>
                    </form>`,
                resId: 1,
            });

            await createRecord();
            await click(target.querySelector(".o-kanban-button-new"));

            assert.containsOnce(target, ".modal");
            assert.containsNone(target, ".modal .modal-footer .o_btn_remove");
        }
    );

    QUnit.test(
        '"bare" buttons in template should not trigger button click',
        async function (assert) {
            assert.expect(4);

            const actionService = {
                start() {
                    return {
                        doActionButton(args) {
                            assert.step("doActionButton");
                            delete args.onClose;
                            assert.deepEqual(args, {
                                buttonContext: {},
                                context: {
                                    lang: "en",
                                    tz: "taht",
                                    uid: 7,
                                },
                                resId: 2,
                                resIds: [2],
                                resModel: "partner",
                                special: "save",
                            });
                        },
                    };
                },
            };

            registry.category("services").add("action", actionService, { force: true });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch:
                    "<form>" +
                    '<button string="Save" class="btn-primary" special="save"/>' +
                    '<button class="mybutton">westvleteren</button>' +
                    "</form>",
                resId: 2,
            });

            assert.ok(target.querySelector(".o_form_view button.mybutton").disabled);
            await click(target.querySelector(".o_form_view .o_content button.btn-primary"));
            assert.verifySteps(["doActionButton"]);
        }
    );

    QUnit.test(
        "form view with inline tree view with optional fields and local storage mock",
        async function (assert) {
            patchWithCleanup(browser.localStorage, {
                getItem(key) {
                    assert.step("getItem " + key);
                    return super.getItem(key);
                },
                setItem(key, value) {
                    assert.step("setItem " + key + " to " + value);
                    return super.setItem(key, value);
                },
            });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="qux"/>
                        <field name="p">
                            <tree>
                                <field name="foo"/>
                                <field name="bar" optional="hide"/>
                            </tree>
                        </field>
                    </form>`,
            });

            const localStorageKey = "optional_fields,partner,form,100000001,p,list,bar,foo";

            assert.containsN(
                target,
                ".o_list_table th",
                2,
                "should have 2 th, 1 for selector, 1 for foo column"
            );

            assert.ok(
                target.querySelector(`th[data-name="foo"]`),
                "should have a visible foo field"
            );

            assert.notOk(
                target.querySelector(`th[data-name="bar"]`),
                "should not have a visible bar field"
            );

            // optional fields
            await click(target.querySelector(".o_optional_columns_dropdown .dropdown-toggle"));
            assert.containsN(
                target,
                ".o_optional_columns_dropdown .dropdown-item",
                1,
                "dropdown have 1 optional field"
            );

            // enable optional field
            await click(target.querySelector(`.o_optional_columns_dropdown input[name="bar"]`));
            assert.verifySteps([
                "getItem " + localStorageKey,
                "setItem " + localStorageKey + " to bar",
            ]);

            assert.containsN(
                target,
                ".o_list_table th",
                3,
                "should have 3 th, 1 for selector, 2 for columns"
            );

            assert.ok(
                target.querySelector(`th[data-name="foo"]`),
                "should have a visible foo field"
            );

            assert.ok(
                target.querySelector(`th[data-name="bar"]`),
                "should have a visible bar field"
            );
        }
    );

    QUnit.test(
        "form view with tree_view_ref with optional fields and local storage mock",
        async function (assert) {
            patchWithCleanup(browser.localStorage, {
                getItem(key) {
                    assert.step("getItem " + key);
                    return super.getItem(key);
                },
                setItem(key, value) {
                    assert.step("setItem " + key + " to " + value);
                    return super.setItem(key, value);
                },
            });

            serverData.views = {
                "partner,nope_not_this_one,list":
                    '<tree><field name="foo"/><field name="bar"/></tree>',
                "partner,34,list": `
                    <tree>
                        <field name="foo" optional="hide"/>
                        <field name="bar"/>
                    </tree>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                // we add a widget= as a bit of a hack. Without widget, the views are inlined by the server.
                // the mock server doesn't replicate fully this behavior.
                // Putting a widget prevent the inlining.
                arch: `
                    <form>
                        <field name="qux"/>
                        <field name="p" widget="one2many" context="{'tree_view_ref': '34'}"/>
                    </form>`,
            });

            const localStorageKey = "optional_fields,partner,form,100000001,p,list,bar,foo";

            assert.containsN(
                target,
                ".o_list_table th",
                2,
                "should have 2 th, 1 bar selector, 1 for foo column"
            );

            assert.notOk(
                target.querySelector(`th[data-name="foo"]`),
                "should not have a visible foo field"
            );

            assert.ok(
                target.querySelector(`th[data-name="bar"]`),
                "should have a visible bar field"
            );

            // optional fields
            await click(target.querySelector(".o_optional_columns_dropdown .dropdown-toggle"));
            assert.containsN(
                target,
                ".o_optional_columns_dropdown .dropdown-item",
                1,
                "dropdown have 1 optional field"
            );

            // enable optional field
            await click(target.querySelector(`.o_optional_columns_dropdown input[name="foo"]`));
            assert.verifySteps([
                "getItem " + localStorageKey,
                "setItem " + localStorageKey + " to foo",
            ]);

            assert.containsN(
                target,
                ".o_list_table th",
                3,
                "should have 3 th, 1 for selector, 2 for columns"
            );

            assert.ok(
                target.querySelector(`th[data-name="foo"]`),
                "should have a visible foo field"
            );

            assert.ok(
                target.querySelector(`th[data-name="bar"]`),
                "should have a visible bar field"
            );
        }
    );

    QUnit.test("resequence list lines when discardable lines are present", async function (assert) {
        var onchangeNum = 0;
        serverData.models.partner.onchanges = {
            p: function (obj) {
                onchangeNum++;
                obj.foo = obj.p ? obj.p.length.toString() : "0";
            },
        };

        serverData.views = {
            "partner,false,list": `
                <tree editable="bottom">
                    <field name="int_field" widget="handle"/>
                    <field name="display_name" required="1"/>
                </tree>`,
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/><field name="p"/></form>`,
        });

        assert.strictEqual(onchangeNum, 1, "one onchange happens when form is opened");
        assert.strictEqual(
            target.querySelector('[name="foo"] input').value,
            "0",
            "onchange worked there is 0 line"
        );

        // Add one line
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await editInput(target, `.o_field_cell [name="display_name"] input`, "first line");
        assert.strictEqual(onchangeNum, 2, "one onchange happens when a line is added");
        assert.strictEqual(
            target.querySelector('[name="foo"] input').value,
            "1",
            "onchange worked there is 1 line"
        );

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await nextTick();
        // Drag and drop second line before first one (with 1 draft and invalid line)
        await dragAndDrop(
            "tbody.ui-sortable tr:nth-child(1) .o_handle_cell",
            "tbody.ui-sortable tr:nth-child(2)"
        );
        assert.strictEqual(onchangeNum, 3, "one onchange happens when lines are resequenced");
        assert.strictEqual(
            target.querySelector('[name="foo"] input').value,
            "1",
            "onchange worked there is 1 line"
        );
        // Add a second line
        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        await editInput(target, ".o_selected_row input", "second line");

        assert.strictEqual(onchangeNum, 4, "one onchange happens when a line is added");
        assert.strictEqual(
            target.querySelector('[name="foo"] input').value,
            "2",
            "onchange worked there is 2 lines"
        );
    });

    QUnit.test(
        "reload company when creating records of model res.company",
        async function (assert) {
            const fakeActionService = {
                start(env, { actionMain }) {
                    return Object.assign({}, actionMain, {
                        doAction: (actionRequest) => {
                            if (actionRequest === "reload_context") {
                                assert.step("reload company");
                                return Promise.resolve();
                            }
                        },
                    });
                },
            };
            serviceRegistry.add("company", companyService, { force: true });
            serviceRegistry.add("action", fakeActionService, { force: true });

            await makeView({
                type: "form",
                resModel: "res.company",
                serverData,
                arch: `
                    <form>
                        <field name="name"/>
                    </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            await editInput(target, '.o_field_widget[name="name"] input', "Test Company");
            await clickSave(target);

            assert.verifySteps(["get_views", "onchange", "web_save", "reload company"]);
        }
    );

    QUnit.test(
        "reload company when writing on records of model res.company",
        async function (assert) {
            const fakeActionService = {
                start(env, { actionMain }) {
                    return Object.assign({}, actionMain, {
                        doAction: (actionRequest) => {
                            if (actionRequest === "reload_context") {
                                assert.step("reload company");
                                return Promise.resolve();
                            }
                        },
                    });
                },
            };
            serviceRegistry.add("company", companyService, { force: true });
            serviceRegistry.add("action", fakeActionService, { force: true });

            serverData.models["res.company"].records = [
                {
                    id: 1,
                    name: "Test Company",
                },
            ];

            await makeView({
                type: "form",
                resModel: "res.company",
                serverData,
                arch: `
                    <form>
                        <field name="name"/>
                    </form>`,
                resId: 1,
                mockRPC(route, args) {
                    assert.step(args.method);
                },
            });

            await editInput(target, '.o_field_widget[name="name"] input', "Test Company2");
            await clickSave(target);

            assert.verifySteps(["get_views", "web_read", "web_save", "reload company"]);
        }
    );

    QUnit.test(
        "company_dependent field in form view, in multi company group",
        async function (assert) {
            serverData.models.partner.fields.product_id.company_dependent = true;
            serverData.models.partner.fields.product_id.help = "this is a tooltip";
            serverData.models.partner.fields.foo.company_dependent = true;

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
                clearTimeout: () => {},
            });

            patchWithCleanup(session, {
                display_switch_company_menu: true,
            });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="foo"/>
                            <field name="product_id"/>
                        </group>
                    </form>`,
            });

            await mouseEnter(target.querySelector(".o_form_label[for=product_id_0] sup"));
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o-tooltip .o-tooltip--help").textContent,
                "this is a tooltip\n\nValues set here are company-specific."
            );

            await mouseEnter(target.querySelector(".o_form_label[for=foo_0] sup"));
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o-tooltip .o-tooltip--help").textContent,
                "Values set here are company-specific."
            );
        }
    );

    QUnit.test(
        "company_dependent field in form view, not in multi company group",
        async function (assert) {
            serverData.models.partner.fields.product_id.company_dependent = true;
            serverData.models.partner.fields.product_id.help = "this is a tooltip";

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
                clearTimeout: () => {},
            });

            patchWithCleanup(session, {
                display_switch_company_menu: false,
            });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="product_id"/>
                        </group>
                    </form>`,
            });

            await mouseEnter(target.querySelector(".o_form_label sup"));
            await nextTick();
            assert.strictEqual(
                target.querySelector(".o-tooltip .o-tooltip--help").textContent,
                "this is a tooltip"
            );
        }
    );

    QUnit.test("Auto save: save when page changed", async function (assert) {
        assert.expect(10);

        serverData.actions[1] = {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };

        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="name"/>
                </tree>`,
            "partner,false,form": `
                <form>
                    <group>
                        <field name="name"/>
                    </group>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            if (args.method === "web_save") {
                assert.deepEqual(args.args, [[1], { name: "aaa" }]);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 1);

        await click(target.querySelector(".o_data_row td.o_data_cell"));
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnerfirst record"
        );

        await editInput(target, ".o_field_widget[name='name'] input", "aaa");

        await click(target.querySelector(`.o_pager button.o_pager_next`));
        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnersecond record"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="name"] input').value,
            "name"
        );

        await clickDiscard(target);
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnersecond record"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="name"] input').value,
            "name"
        );

        await click(target.querySelector(`.o_pager button.o_pager_previous`));
        assert.containsOnce(target, ".o_form_saved");
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnerfirst record"
        );
        assert.strictEqual(target.querySelector('.o_field_widget[name="name"] input').value, "aaa");
    });

    QUnit.test("Auto save: save when breadcrumb clicked", async function (assert) {
        assert.expect(7);

        serverData.actions[1] = {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };

        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="name"/>
                </tree>`,
            "partner,false,form": `
                <form>
                    <group>
                        <field name="name"/>
                    </group>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            if (args.method === "web_save") {
                assert.deepEqual(args.args, [[1], { name: "aaa" }]);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 1);

        await click(target.querySelector(".o_data_row td.o_data_cell"));
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnerfirst record"
        );

        await editInput(target, ".o_field_widget[name='name'] input", "aaa");

        await click(target.querySelector(".breadcrumb-item.o_back_button"));

        assert.strictEqual(target.querySelector(".o_breadcrumb").textContent, "Partner");
        assert.strictEqual(target.querySelector(".o_field_cell").textContent, "aaa");

        await click(target.querySelector(".o_data_row td.o_data_cell"));
        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnerfirst record"
        );
        assert.strictEqual(target.querySelector('.o_field_widget[name="name"] input').value, "aaa");
    });

    QUnit.test("Auto save: error on save when breadcrumb clicked", async function (assert) {
        assert.expect(3);

        registry.category("services").add("error", errorService);

        serverData.actions[1] = {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };

        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="name"/>
                </tree>`,
            "partner,false,form": `
                <form>
                    <group>
                        <field name="name"/>
                    </group>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        const webClient = await createWebClient({
            serverData,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                    throw makeServerError();
                }
            },
        });
        await doAction(webClient, 1);
        await click(target.querySelector(".o_data_row td.o_data_cell"));

        await editInput(target, ".o_field_widget[name='name'] input", "aaa");
        await click(target.querySelector(".breadcrumb-item.o_back_button"));
        assert.verifySteps(["web_save"]);
        await nextTick();
        assert.containsOnce(target, ".o_error_dialog");
    });

    QUnit.test("Auto save: save when action changed", async function (assert) {
        assert.expect(6);

        serverData.actions[1] = {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };

        serverData.actions[2] = {
            id: 2,
            name: "Other action",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "kanban"]],
        };

        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="name"/>
                </tree>`,
            "partner,false,form": `
                <form>
                    <group>
                        <field name="name"/>
                    </group>
                </form>`,
            "partner,false,search": "<search></search>",
            "partner,false,kanban": `
                <kanban>
                    <field name="name"/>
                    <templates>
                        <t t-name="kanban-box">
                            <div></div>
                        </t>
                    </templates>
                </kanban>`,
        };

        const mockRPC = (route, args) => {
            if (args.method === "web_save") {
                assert.deepEqual(args.args, [[1], { name: "aaa" }]);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 1);

        await click(target.querySelector(".o_data_row td.o_data_cell"));
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnerfirst record"
        );

        await editInput(target, ".o_field_widget[name='name'] input", "aaa");

        await doAction(webClient, 2, { clearBreadcrumbs: true });

        assert.strictEqual(target.querySelector(".o_breadcrumb").textContent, "Other action");

        await doAction(webClient, 1, { clearBreadcrumbs: true });

        await click(target.querySelector(".o_data_row td.o_data_cell"));
        assert.containsOnce(target, ".o_form_editable");
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnerfirst record"
        );
        assert.strictEqual(target.querySelector('.o_field_widget[name="name"] input').value, "aaa");
    });

    QUnit.test("Auto save: save on closing tab/browser", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="display_name"/>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, { args, method, model }) {
                if (method === "web_save" && model === "partner") {
                    assert.step("save"); // should be called
                    assert.deepEqual(args, [[1], { display_name: "test" }]);
                }
            },
        });

        assert.notStrictEqual(
            target.querySelector('.o_field_widget[name="display_name"]').value,
            "test"
        );

        await editInput(target, '.o_field_widget[name="display_name"] input', "test");
        const evnt = new Event("beforeunload");
        evnt.preventDefault = () => assert.step("prevented");
        window.dispatchEvent(evnt);
        await nextTick();
        assert.verifySteps(["save"], "should not prevent unload");
    });

    QUnit.test("Auto save: save on closing tab/browser (invalid field)", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="display_name" required="1"/>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, { args, method, model }) {
                if (method === "web_save" && model === "partner") {
                    assert.step("save"); // should not be called
                }
            },
        });

        await editInput(target, '.o_field_widget[name="display_name"] input', "");
        const evnt = new Event("beforeunload");
        evnt.preventDefault = () => assert.step("prevented");
        window.dispatchEvent(evnt);
        await nextTick();

        assert.verifySteps(["prevented"], "should not save because of invalid field");
    });

    QUnit.test("Auto save: save on closing tab/browser (not dirty)", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="display_name"/>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, { args, method, model }) {
                if (method === "web_save" && model === "partner") {
                    assert.step("save"); // should not be called
                }
            },
        });

        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();

        assert.verifySteps([], "should not save because we do not change anything");
    });

    QUnit.test(
        "Auto save: save on closing tab/browser (not dirty but trailing spaces)",
        async function (assert) {
            serverData.models.partner.fields.foo.trim = true;
            serverData.models.partner.records[0].foo = "name with trailing spaces   ";

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="foo"/></form>`,
                resId: 1,
                mockRPC(route, { args, method, model }) {
                    assert.step(method);
                },
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=foo] input").value,
                "name with trailing spaces   "
            );

            window.dispatchEvent(new Event("beforeunload"));
            await nextTick();

            assert.verifySteps(["get_views", "web_read"]);
        }
    );

    QUnit.test(
        "Auto save: save on closing tab/browser (not dirty) with text field",
        async function (assert) {
            serverData.models.partner.fields.bloup = {
                string: "Bloup",
                type: "text",
                default: false,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <group>
                        <field name="bloup"/>
                    </group>
                </form>`,
                resId: 1,
                mockRPC(route, { args, method, model }) {
                    if (method === "web_save" && model === "partner") {
                        assert.step("save"); // should not be called
                    }
                },
            });

            assert.strictEqual(
                target.querySelector(".o_field_widget[name=bloup] textarea").value,
                "",
                "should contain the default value"
            );

            window.dispatchEvent(new Event("beforeunload"));
            await nextTick();

            assert.verifySteps([], "should not save because we do not change anything");
        }
    );

    QUnit.test("Auto save: save on closing tab/browser (detached form)", async function (assert) {
        serverData.actions[1] = {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };

        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="display_name"/>
                </tree>`,
            "partner,false,form": `
                <form>
                    <group>
                        <field name="display_name"/>
                    </group>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        const mockRPC = (route, args) => {
            if (args.method === "web_save") {
                assert.step("save");
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });

        await doAction(webClient, 1);

        // Click on a row to open a record
        await click(target.querySelector(".o_data_row td.o_data_cell"));
        assert.strictEqual(
            target.querySelector(".o_breadcrumb").textContent,
            "Partnerfirst record"
        );

        // Return in the list view to detach the form view
        await click(target.querySelector(".o_back_button"));
        assert.strictEqual(target.querySelector(".o_breadcrumb").textContent, "Partner");

        // Simulate tab/browser close in the list
        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();

        // write rpc should not trigger because form view has been detached
        // and list has nothing to save
        assert.verifySteps([]);
    });

    QUnit.test("Auto save: save on closing tab/browser (onchanges)", async function (assert) {
        assert.expect(1);

        serverData.models.partner.onchanges = {
            display_name: function (obj) {
                obj.name = `copy: ${obj.display_name}`;
            },
        };

        const def = makeDeferred();
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="display_name"/>
                        <field name="name"/>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, { args, method, model }) {
                if (method === "onchange" && model === "partner") {
                    return def;
                }
                if (method === "web_save" && model === "partner") {
                    assert.deepEqual(args, [[1], { display_name: "test" }]);
                }
            },
        });

        await editInput(target, '.o_field_widget[name="display_name"] input', "test");

        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();
    });

    QUnit.test("Auto save: save on closing tab/browser (onchanges 2)", async function (assert) {
        assert.expect(1);

        serverData.models.partner.onchanges = {
            display_name: function () {},
        };

        const def = makeDeferred();
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="display_name"/>
                        <field name="name"/>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, { args, method }) {
                if (method === "onchange") {
                    return def;
                }
                if (method === "web_save") {
                    assert.deepEqual(args, [[1], { display_name: "test1", name: "test2" }]);
                }
            },
        });

        await editInput(target, '.o_field_widget[name="display_name"] input', "test1");
        await editInput(target, '.o_field_widget[name="name"] input', "test2");

        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();
    });

    QUnit.test("Auto save: save on closing tab/browser (pending change)", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            resId: 1,
            mockRPC(route, { args, method }) {
                assert.step(method);
                if (method === "web_save") {
                    assert.deepEqual(args, [[1], { foo: "test" }]);
                }
            },
        });

        // edit 'foo' but do not focusout -> the model isn't aware of the change
        // until the 'beforeunload' event is triggered
        const input = target.querySelector(".o_field_widget[name='foo'] input");
        input.value = "test";
        await triggerEvent(input, null, "input");

        window.dispatchEvent(new Event("beforeunload"));
        await nextTick();

        assert.verifySteps(["get_views", "web_read", "web_save"]);
    });

    QUnit.test(
        "Auto save: save on closing tab/browser (onchanges + pending change)",
        async function (assert) {
            assert.expect(6);

            serverData.models.partner.onchanges = {
                display_name: function (obj) {
                    obj.name = `copy: ${obj.display_name}`;
                },
            };

            const def = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="name"/>
                        <field name="foo"/>
                    </form>`,
                resId: 1,
                mockRPC(route, { args, method }) {
                    assert.step(method);
                    if (method === "onchange") {
                        return def;
                    }
                    if (method === "web_save") {
                        assert.deepEqual(args, [
                            [1],
                            { display_name: "test", name: "test", foo: "test" },
                        ]);
                    }
                },
            });

            // edit 'display_name' and simulate a focusout (trigger the 'change' event)
            await editInput(target, '.o_field_widget[name="display_name"] input', "test");

            // edit 'name' and simulate a focusout (trigger the 'change' event)
            await editInput(target, '.o_field_widget[name="name"] input', "test");

            // edit 'foo' but do not focusout -> the model isn't aware of the change
            // until the 'beforeunload' event is triggered
            const input = target.querySelector('.o_field_widget[name="foo"] input');
            input.value = "test";
            await triggerEvent(input, null, "input");

            // trigger the 'beforeunload' event -> notifies the model directly and saves
            window.dispatchEvent(new Event("beforeunload"));
            await nextTick();

            assert.verifySteps(["get_views", "web_read", "onchange", "web_save"]);
        }
    );

    QUnit.test(
        "Auto save: save on closing tab/browser (invalid pending change)",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form><field name="qux"/></form>`,
                resId: 1,
                mockRPC(route, { method }) {
                    assert.step(method);
                    if (method === "web_save") {
                        assert.notOk(true, "should not call the /write route");
                    }
                },
            });

            // edit 'foo' but do not focusout -> the model isn't aware of the change
            // until the 'beforeunload' event is triggered
            const input = target.querySelector(".o_field_widget[name='qux'] input");
            input.value = "test";
            await triggerEvent(input, null, "input");

            window.dispatchEvent(new Event("beforeunload"));
            await nextTick();

            assert.verifySteps(["get_views", "web_read"]);
        }
    );

    QUnit.test(
        "Auto save: save on closing tab/browser (onchanges + invalid field)",
        async function (assert) {
            serverData.models.partner.onchanges = {
                display_name: function (obj) {
                    obj.name = `copy: ${obj.display_name}`;
                },
            };

            const def = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="display_name"/>
                            <field name="name" required="1"/>
                        </group>
                    </form>`,
                resId: 1,
                mockRPC(route, { method }) {
                    assert.step(method);
                    if (method === "onchange") {
                        return def;
                    }
                },
            });

            await editInput(target, '.o_field_widget[name="display_name"] input', "test");
            await editInput(target, '.o_field_widget[name="name"] input', "");

            window.dispatchEvent(new Event("beforeunload"));
            await nextTick();

            assert.verifySteps(["get_views", "web_read", "onchange"]);
        }
    );

    QUnit.test("Auto save: save when action button clicked", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            actionMenus: {},
            resId: 1,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                }
            },
        });

        assert.strictEqual(target.querySelector(".o_field_widget[name='foo'] input").value, "yop");
        await editInput(target, ".o_field_widget[name='foo'] input", "test");

        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 1");
        assert.strictEqual(target.querySelector(".o_field_widget[name='foo'] input").value, "test");
        await click(target, ".o_cp_action_menus button");
        await click(target.querySelector(".o_cp_action_menus .dropdown-menu .dropdown-item"));

        assert.verifySteps(["web_save"]);
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "2 / 2");
        assert.strictEqual(target.querySelector(".o_field_widget[name='foo'] input").value, "test");

        await click(target, ".o_pager_previous");
        assert.strictEqual(target.querySelector(".o_pager_counter").textContent, "1 / 2");
        assert.strictEqual(target.querySelector(".o_field_widget[name='foo'] input").value, "test");
    });

    QUnit.test("Auto save: error on save when action button clicked", async function (assert) {
        assert.expect(3);

        registry.category("services").add("error", errorService);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            actionMenus: {},
            resId: 1,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                    throw makeServerError();
                }
            },
        });

        await editInput(target, ".o_field_widget[name='foo'] input", "test");
        await click(target, ".o_cp_action_menus button");
        await click(target.querySelector(".o_cp_action_menus .dropdown-menu .dropdown-item"));
        assert.verifySteps(["web_save"]);
        await nextTick();
        assert.containsOnce(target, ".o_error_dialog");
    });

    QUnit.test("Auto save: save when create button clicked", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            resId: 1,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                }
            },
        });

        assert.strictEqual(target.querySelector(".o_field_widget[name='foo'] input").value, "yop");
        await editInput(target, ".o_field_widget[name='foo'] input", "test");

        await click(
            target,
            ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_form_button_create"
        );
        assert.verifySteps(["web_save"]);
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='foo'] input").value,
            "My little Foo Value"
        );
        assert.strictEqual(target.querySelector(".o_breadcrumb .active").textContent, "New");
    });

    QUnit.test("Auto save: error on save when create button clicked", async function (assert) {
        assert.expect(3);

        registry.category("services").add("error", errorService);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            actionMenus: {},
            resId: 1,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                    throw makeServerError();
                }
            },
        });

        await editInput(target, ".o_field_widget[name='foo'] input", "test");
        await createRecord();
        assert.verifySteps(["web_save"]);
        await nextTick();
        assert.containsOnce(target, ".o_error_dialog");
    });

    QUnit.test("no 'oh snap' error when clicking on a view button", async (assert) => {
        registry.category("services").add("error", errorService);
        registry.category("error_dialogs").add("odoo.exceptions.UserError", WarningDialog);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <button name="do_it" type="object" string="Do it"/>
                    <field name="name"/>
                </form>`,
            mockRPC(route, { method }) {
                assert.step(method);
                if (method === "web_save") {
                    throw makeServerError({ message: "Some business message" });
                }
            },
        });

        await click(target, "button[name=do_it]");
        await nextTick();
        assert.containsNone(target, ".o_form_error_dialog");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal .modal-body").textContent,
            "Some business message"
        );
        assert.verifySteps(["get_views", "onchange", "web_save"]);
    });

    QUnit.test("no 'oh snap' error in form view in dialog", async (assert) => {
        assert.expect(5);

        registry.category("services").add("error", errorService);
        registry.category("error_dialogs").add("odoo.exceptions.UserError", WarningDialog);

        serverData.views = {
            "partner,false,form": `<form><field name="foo"/><footer><button type="object" name="some_method" class="myButton"/></footer></form>`,
        };

        const webClient = await createWebClient({
            serverData,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                    throw makeServerError({ message: "Some business message" });
                }
            },
        });

        await doAction(webClient, {
            type: "ir.actions.act_window",
            target: "new",
            res_model: "partner",
            view_mode: "form",
            views: [[false, "form"]],
        });

        await editInput(target, ".o_field_widget[name='foo'] input", "test");
        await click(target.querySelector(".modal  footer .myButton"));
        assert.verifySteps(["web_save"]);
        await nextTick();
        assert.containsOnce(target, ".o_error_dialog");
        assert.containsN(target, ".modal", 2);
        assert.strictEqual(
            target.querySelectorAll(".modal .modal-body")[1].textContent,
            "Some business message"
        );
    });

    QUnit.test('field "length" with value 0: can apply onchange', async function (assert) {
        serverData.models.partner.fields.length = { string: "Length", type: "float", default: 0 };
        serverData.models.partner.fields.foo.default = "foo default";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="foo"/><field name="length"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=foo] input").value,
            "foo default",
            "should contain input with initial value"
        );
    });

    QUnit.test(
        'field "length" with value 0: readonly fields are not sent when saving',
        async function (assert) {
            assert.expect(3);

            serverData.models.partner.fields.length = {
                string: "Length",
                type: "float",
                default: 0,
            };
            serverData.models.partner.fields.foo.default = "foo default";

            // define an onchange on display_name to check that the value of readonly
            // fields is correctly sent for onchanges
            serverData.models.partner.onchanges = {
                display_name: function () {},
                p: function () {},
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="p">
                            <tree>
                                <field name="display_name"/>
                            </tree>
                            <form>
                                <field name="length"/>
                                <field name="display_name"/>
                                <field name="foo" readonly="display_name =='readonly'"/>
                            </form>
                        </field>
                    </form>`,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.deepEqual(
                            args.args[1],
                            {
                                p: [
                                    [
                                        0,
                                        args.args[1].p[0][1],
                                        { length: 0, display_name: "readonly" },
                                    ],
                                ],
                            },
                            "should not have sent the value of the readonly field"
                        );
                    }
                },
            });

            await click(target.querySelector(".o_field_x2many_list_row_add a"));
            assert.containsOnce(
                target,
                ".modal .o_field_widget[name=foo] input",
                "foo should be editable"
            );
            await editInput(target, ".modal .o_field_widget[name=foo] input", "foo value");
            await editInput(target, ".modal .o_field_widget[name=display_name] input", "readonly");
            assert.containsOnce(
                target,
                ".modal .o_field_widget[name=foo] span",
                "foo should be readonly"
            );
            await clickSave(target.querySelector(".modal"));

            await clickSave(target); // save the record
        }
    );

    QUnit.test("fieldDependencies support for fields", async (assert) => {
        serverData.models.partner.records = [{ id: 1, int_field: 2 }];

        const customField = {
            component: class CustomField extends Component {
                static template = xml`<span t-esc="props.record.data.int_field"/>`;
            },
            fieldDependencies: [{ name: "int_field", type: "integer" }],
        };
        registry.category("fields").add("custom_field", customField);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="foo" widget="custom_field"/>
                </form>
            `,
            serverData,
        });

        assert.strictEqual(target.querySelector("[name=foo] span").innerText, "2");
    });

    QUnit.test(
        "fieldDependencies support for fields: dependence on a relational field",
        async (assert) => {
            serverData.models.partner.records[0].product_id = 37;

            const customField = {
                component: class CustomField extends Component {
                    static template = xml`<span t-esc="props.record.data.product_id[1]"/>`;
                },
                fieldDependencies: [{ name: "product_id", type: "many2one", relation: "product" }],
            };
            registry.category("fields").add("custom_field", customField);

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                arch: `
                    <form>
                        <field name="foo" widget="custom_field"/>
                    </form>
                `,
                serverData,
                mockRPC: (route, args) => {
                    assert.step(args.method);
                },
            });

            assert.strictEqual(target.querySelector("[name=foo] span").innerText, "xphone");
            assert.verifySteps(["get_views", "web_read"]);
        }
    );

    QUnit.test("Action Button clicked with failing action", async function (assert) {
        assert.expectErrors();

        class MyComponent extends Component {
            setup() {
                throw new Error("test");
            }
        }
        MyComponent.template = xml`<div/>`;
        registry.category("actions").add("someaction", MyComponent);

        serverData.views = {
            "partner,false,form": `
                <form>
                    <sheet>
                        <div name="button_box" class="oe_button_box test">
                            <button class="oe_stat_button" type="action" name="someaction">
                                Test
                            </button>
                        </div>
                    </sheet>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            res_id: 1,
            type: "ir.actions.act_window",
            target: "current",
            res_model: "partner",
            view_mode: "form",
            views: [[false, "form"]],
        });
        assert.containsOnce(target, ".o_form_view .test");

        await click(target.querySelector(".oe_stat_button"));
        assert.containsOnce(target, ".o_form_view .test");
        assert.verifyErrors(["test"]);
    });

    QUnit.test("form view with edit='0' but create='1', existing record", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form edit="0"><field name="foo"/></form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_form_readonly");
        await createRecord();
        assert.containsOnce(target, ".o_form_editable");
    });

    QUnit.test("form view with edit='0' but create='1', new record", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form edit="0"><field name="foo"/></form>`,
        });

        assert.containsOnce(target, ".o_form_editable");
    });

    QUnit.test("save a form view with an invisible required field", async function (assert) {
        serverData.models.partner.fields.text = { string: "Text", type: "char", required: 1 };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                    <form>
                        <sheet>
                            <field name="text" invisible="1"/>
                            <field name="int_field"/>
                        </sheet>
                    </form>`,
            mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1], {
                        int_field: 0,
                        text: false,
                    });
                }
            },
        });

        await clickSave(target);
        assert.verifySteps(["get_views", "onchange", "web_save"]);
    });

    QUnit.test(
        "save a form view with a duplicated invisible required field",
        async function (assert) {
            serverData.models.partner.fields.text = { string: "Text", type: "char", required: 1 };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <group>
                        <field name="text"/>
                        <field name="text" invisible="1"/>
                    </group>
                </form>`,
            });

            await clickSave(target);

            assert.containsOnce(target, ".o_form_label.o_field_invalid");
            assert.containsOnce(target, ".o_field_char.o_field_invalid");
        }
    );

    QUnit.test(
        "save a form view with an invisible required field in a x2many",
        async function (assert) {
            serverData.models.partner.fields.text = { string: "Text", type: "char", required: 1 };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <sheet>
                        <field name="p">
                            <tree editable="top">
                                <field name="text" invisible="1"/>
                                <field name="int_field"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
                mockRPC(route, args) {
                    assert.step(args.method);
                    if (args.method === "web_save") {
                        assert.deepEqual(args.args[1].p[0][2], { int_field: 1, text: false });
                    }
                },
            });

            await addRow(target);
            await editInput(target, "[name='int_field'] input", 1);
            await click(target, ".o_form_view");
            assert.containsNone(target, "[name='int_field'] input");

            await clickSave(target);
            assert.containsOnce(target, ".o_list_renderer .o_data_row");
            assert.strictEqual(
                target.querySelector(".o_list_renderer .o_data_row [name='int_field']").textContent,
                "1"
            );
            assert.verifySteps(["get_views", "onchange", "onchange", "web_save"]);
        }
    );

    QUnit.test("help on field as precedence over field's declaration -- form", async (assert) => {
        serverData.models.partner.fields.foo.help = "pythonHelp";
        patchWithCleanup(odoo, { debug: "1" });
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: `<form><sheet><field name="foo" help="xmlHelp" /></sheet></form>`,
            serverData,
        });

        assert.strictEqual(
            JSON.parse(target.querySelector(".o_field_widget").dataset.tooltipInfo).field.help,
            "xmlHelp"
        );
    });

    QUnit.test("help on field is shown without debug mode -- form", async (assert) => {
        serverData.models.partner.fields.bar.help = "bar tooltip";

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => { },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <label for="foo"/>
                        <div><field name="foo" help="foo xml tooltip"/></div>
                        <label for="bar"/>
                        <div><field name="bar" help="bar xml tooltip"/></div>
                    </group>
                </form>`,
        });

        await mouseEnter(target.querySelector(".o_form_label[for=foo_0] sup"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip .o-tooltip--help").textContent,
            "foo xml tooltip"
        );

        await mouseEnter(target.querySelector(".o_form_label[for=bar_0] sup"));
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o-tooltip .o-tooltip--help").textContent,
            "bar xml tooltip"
        );
    });

    QUnit.test("onSave/onDiscard props", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="foo"/></form>`,
            resId: 1,
            onSave: () => assert.step("save"),
            onDiscard: () => assert.step("discard"),
        });

        await editInput(target, ".o_field_widget input", "test");
        await clickSave(target);
        await editInput(target, ".o_field_widget input", "test");
        await clickDiscard(target);
        assert.verifySteps(["save", "discard"]);
    });

    QUnit.test("form view does not deactivate sample data on other views", async function (assert) {
        serverData.models.partner.records = [];
        serverData.views = {
            "partner,false,list": `<tree sample="1"><field name="name"/></tree>`,
            "partner,false,form": `<form><field name="name"/></form>`,
            "partner,false,search": `<search/>`,
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });

        assert.containsOnce(target, ".o_list_view .o_content.o_view_sample_data");
        await click(target, ".o_control_panel_main_buttons .d-none button.o_list_button_add");
        assert.containsOnce(target, ".o_form_view");
        await click(target.querySelector(".o_form_view .breadcrumb-item a"));
        assert.containsOnce(target, ".o_list_view .o_content.o_view_sample_data");
    });

    QUnit.test("empty x2manys when coming form a list with sample data", async function (assert) {
        serverData.models.partner.records = [];
        serverData.views = {
            "partner,false,list": `<tree sample="1"><field name="name"/></tree>`,
            "partner,false,form": `
                <form>
                    <field name="p">
                        <kanban>
                            <templates>
                                <t t-name="kanban-box">
                                    <div><field name="name"/></div>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
            "partner,false,search": `<search/>`,
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        });

        assert.containsOnce(target, ".o_list_view .o_content.o_view_sample_data");
        await click(target, ".o_control_panel_main_buttons .d-none button.o_list_button_add");
        assert.containsOnce(target, ".o_form_view .o_field_x2many .o_kanban_renderer");
        assert.containsNone(target, ".o_view_nocontent");
    });

    QUnit.test("status indicator: saved state", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="foo"/></form>`,
        });

        assert.containsOnce(target, ".o_form_status_indicator");
        assert.containsOnce(target, ".o_form_status_indicator_buttons");
        assert.containsOnce(target, ".o_form_status_indicator_buttons.invisible");
        assert.containsN(target, ".o_form_status_indicator_buttons button", 2);
    });

    QUnit.test("status indicator: dirty state", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="foo"/></form>`,
        });

        assert.containsOnce(target, ".o_form_status_indicator_buttons.invisible");
        await editInput(target, ".o_field_widget input", "dirty");
        assert.containsNone(target, ".o_form_status_indicator_buttons.invisible");
    });

    QUnit.test("status indicator: field dirty state", async (assert) => {
        // this test check that the indicator don't need the onchange to be displayed
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="foo"/></form>`,
        });

        assert.containsOnce(target, ".o_form_status_indicator_buttons.invisible");

        const input = target.querySelector(".o_field_widget input");
        input.value = "dirty";
        await triggerEvent(input, null, "input");

        assert.containsNone(target, ".o_form_status_indicator_buttons.invisible");
    });

    QUnit.test("status indicator: field dirty state (date)", async (assert) => {
        // this test check that the indicator don't need the onchange to be displayed
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="date"/></form>`,
        });

        assert.containsOnce(target, ".o_form_status_indicator_buttons.invisible");

        const input = target.querySelector(".o_field_widget input");
        input.value = "03/26/2019";
        await triggerEvent(input, null, "input");

        assert.containsNone(target, ".o_form_status_indicator_buttons.invisible");
    });

    QUnit.test("status indicator: field dirty state (datetime)", async (assert) => {
        // this test check that the indicator don't need the onchange to be displayed
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="datetime"/></form>`,
        });

        assert.containsOnce(target, ".o_form_status_indicator_buttons.invisible");

        const input = target.querySelector(".o_field_widget input");
        input.value = "12/12/2012 11:55:05";
        await triggerEvent(input, null, "input");

        assert.containsNone(target, ".o_form_status_indicator_buttons.invisible");
    });

    QUnit.test("status indicator: save dirty state", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="foo"/></form>`,
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "yop");
        await editInput(target, ".o_field_widget input", "dirty");
        assert.containsNone(target, ".o_form_status_indicator_buttons.invisible");
        await clickSave(target);
        assert.containsOnce(target, ".o_form_status_indicator_buttons.invisible");
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "dirty");
    });

    QUnit.test("status indicator: discard dirty state", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="foo"/></form>`,
        });

        assert.strictEqual(target.querySelector(".o_field_widget input").value, "yop");
        await editInput(target, ".o_field_widget input", "dirty");
        assert.containsNone(target, ".o_form_status_indicator_buttons.invisible");
        await clickDiscard(target);
        assert.containsOnce(target, ".o_form_status_indicator_buttons.invisible");
        assert.strictEqual(target.querySelector(".o_field_widget input").value, "yop");
    });

    QUnit.test("status indicator: invalid state", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="foo" required="1"/></form>`,
            mockRPC(route, { method }) {
                if (method === "web_save") {
                    throw makeServerError();
                }
            },
        });

        assert.strictEqual(target.querySelector(".o_form_status_indicator").textContent, "");
        await editInput(target, ".o_field_widget input", "");
        assert.strictEqual(target.querySelector(".o_form_status_indicator").textContent, "");
        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_form_status_indicator .text-danger").dataset.tooltip,
            "Unable to save. Correct the issue or discard changes"
        );
    });

    QUnit.test(
        "execute an action before and after each valid save in a form view",
        async function (assert) {
            const formView = registry.category("views").get("form");
            class CustomFormController extends formView.Controller {
                async onRecordSaved(record) {
                    assert.step(`onRecordSaved ${record.resId}`);
                }

                async onWillSaveRecord(record) {
                    assert.step(`onWillSaveRecord ${record.resId}`);
                }
            }
            registry.category("views").add("custom_form", {
                ...formView,
                Controller: CustomFormController,
            });

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `<form js_class="custom_form"><field name="foo" required="1"/></form>`,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.step(`write ${args.args[0]}`);
                    }
                },
            });

            await editInput(target, "[name='foo'] input", "");
            await clickSave(target);
            assert.verifySteps([]);

            await editInput(target, "[name='foo'] input", "YOLO");
            await clickSave(target);
            assert.verifySteps(["onWillSaveRecord 1", "write 1", "onRecordSaved 1"]);
        }
    );

    QUnit.test(
        "don't exec a valid save with onWillSaveRecord in a form view",
        async function (assert) {
            const formView = registry.category("views").get("form");
            class CustomFormController extends formView.Controller {
                async onRecordSaved(record) {
                    throw new Error("should not execute onRecordSaved");
                }

                async onWillSaveRecord(record) {
                    assert.step(`onWillSaveRecord ${record.resId}`);
                    return false;
                }
            }
            registry.category("views").add("custom_form", {
                ...formView,
                Controller: CustomFormController,
            });

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `<form js_class="custom_form"><field name="foo" required="1"/></form>`,
                mockRPC(route, args) {
                    if (args.method === "web_save") {
                        assert.step("web_save");
                    }
                },
            });

            await editInput(target, "[name='foo'] input", "");
            await clickSave(target);
            assert.verifySteps([]);

            await editInput(target, "[name='foo'] input", "YOLO");
            await clickSave(target);
            assert.verifySteps(["onWillSaveRecord 1"]);
        }
    );

    QUnit.test("Can't use FormRenderer implementation details in arch", async (assert) => {
        // using t-esc in form view archs isn't accepted, so it displays a warning
        // in the console
        patchWithCleanup(console, {
            warn: () => assert.step("warn"),
        });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <div>
                        <t t-esc="__owl__"/>
                        <t t-esc="props"/>
                        <t t-esc="env"/>
                        <t t-esc="render"/>
                    </div>
                </form>`,
        });
        assert.strictEqual(target.querySelector(".o_form_nosheet").innerHTML, "<div></div>");
        assert.verifySteps(["warn", "warn", "warn", "warn"]);
    });

    QUnit.test("reload form view with an empty notebook", async function (assert) {
        assert.expect(1);

        serverData.views = {
            "partner,false,form": `
            <form>
                <sheet>
                    <notebook>
                    </notebook>
                </sheet>
            </form>`,
            "partner,false,list": '<tree><field name="foo"/></tree>',
            "partner,false,search": "<search></search>",
        };

        serverData.actions = {
            1: {
                id: 1,
                name: "Partner",
                res_model: "partner",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
            },
        };

        const target = getFixture();
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        await click(target.querySelector(".o_data_row .o_data_cell"));
        await click(target.querySelector(".o_back_button"));
        await click(target.querySelector(".o_data_row .o_data_cell"));
        assert.containsOnce(target, ".o_form_view");
    });

    QUnit.test("setting : boolean field", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <setting help="this is bar" documentation="/applications/technical/web/settings/this_is_a_test.html">
                        <field name="bar"/>
                        <button name="buttonName" icon="oi-arrow-right" type="action" string="Manage Users" class="btn-link"/>
                    </setting>
                </form>`,
        });

        assert.containsOnce(target, ".o_setting_left_pane .form-check-input");
        assert.strictEqual(target.querySelector(".o_form_label").textContent, "Bar");
        assert.containsOnce(target, ".o_doc_link");
        assert.hasAttrValue(
            target.querySelector(".o_doc_link"),
            "href",
            "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_a_test.html"
        );
        assert.containsOnce(target, ".btn-link[name='buttonName']");
    });

    QUnit.test("setting : char field", async function (assert) {
        patchWithCleanup(session, {
            display_switch_company_menu: true,
        });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <setting help="this is foo" company_dependent="1">
                        <field name="foo"/>
                    </setting>
                </form>`,
        });

        assert.strictEqual(target.querySelector(".o_setting_left_pane").childElementCount, 0);
        assert.strictEqual(target.querySelector(".o_form_label").textContent, "Foo");
        assert.strictEqual(target.querySelector(".text-muted").textContent, "this is foo");
        assert.containsOnce(target, ".fa-building-o");
        assert.containsOnce(target, ".o_field_char input");
    });

    QUnit.test("setting : without field", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <setting string="Personalize setting" help="this is full personalize setting">
                        <div>This is a different setting</div>
                    </setting>
                </form>`,
        });

        assert.strictEqual(target.querySelector(".o_setting_left_pane").childElementCount, 0);
        assert.containsNone(target, ".o_field_char input");
        assert.strictEqual(
            target.querySelector(".o_form_label").textContent,
            "Personalize setting"
        );
        assert.strictEqual(
            target.querySelector(".text-muted").textContent,
            "this is full personalize setting"
        );
    });

    QUnit.test(
        "action button in x2many should display a notification if the record is virtual",
        async (assert) => {
            const notificationService = makeFakeNotificationService((msg, options) => {
                assert.step(`${options.type}:${msg}`);
            });
            registry.category("services").add("notification", notificationService, { force: true });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="foo"/>
                            <button class="oe_stat_button" name="test_action" type="object" icon="fa-check">MyButton</button>
                        </tree>
                    </field>
                </form>`,
            });

            await click(target.querySelector(".o_field_one2many .o_field_x2many_list_row_add a"));
            await click(target.querySelector("button.oe_stat_button[name='test_action']"));
            assert.verifySteps(['danger:Please click on the "save" button first']);
        }
    );

    QUnit.test("prevent recreating a deleted record", async (assert) => {
        serverData.models.partner.records.length = 1;

        serverData.actions[1] = {
            id: 1,
            name: "Partner",
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "list"],
                [false, "form"],
            ],
        };
        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="name"/>
                </tree>`,
            "partner,false,form": `
                <form>
                    <group>
                        <field name="name"/>
                    </group>
                </form>`,
            "partner,false,search": "<search></search>",
        };

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        assert.containsOnce(target, ".o_data_row");
        assert.strictEqual(target.querySelector(".o_data_row").textContent, "name");
        await click(target, ".o_data_row .o_data_cell");

        await editInput(target, ".o_field_char .o_input", "now dirty");
        assert.isVisible(target.querySelector(".o_form_status_indicator_buttons"));

        await click(target, ".o_cp_action_menus .dropdown-toggle");
        await click($(target).find(".o_cp_action_menus .dropdown-item:contains(Delete)")[0]);
        assert.containsOnce(target, ".modal");

        await click(target, ".modal-footer button.btn-primary");
        assert.containsOnce(target, ".o_list_view");
        assert.containsNone(target, ".o_data_row");
    });

    QUnit.test(
        "coming to an action with an error from a form view with a dirty x2m",
        async function (assert) {
            assert.expectErrors();

            class TestClientAction extends Component {
                setup() {
                    throw new Error("Something went wrong");
                }
            }
            TestClientAction.template = xml`<div></div>`;
            registry.category("actions").add("TestClientAction", TestClientAction);

            class MyWidget extends Component {
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
            MyWidget.template = xml`
                <div class="test_widget">
                    <button t-on-click="onClick">MyButton</button>
                </div>`;
            const myWidget = {
                component: MyWidget,
            };
            widgetRegistry.add("test_widget", myWidget);
            registry.category("services").add("error", errorService);

            serverData.actions = {
                1: {
                    id: 1,
                    name: "test",
                    res_model: "partner",
                    res_id: 1,
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
            };
            serverData.views = {
                "partner,false,list": `
                    <tree editable="bottom">
                        <field name="foo"/>
                    </tree>`,
                "partner,false,search": `<search></search>`,
                "partner,false,form": `
                    <form>
                        <widget name="test_widget"/>
                        <field name="foo"/>
                        <field name="p"/>
                    </form>`,
            };

            const mockRPC = async (route, args) => {
                if (
                    (args.method === "web_read" || args.method === "web_save") &&
                    args.args[0][0] === 1
                ) {
                    assert.step(args.method);
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 1);
            await addRow(target, "[name='p']");
            await editInput(target, "[name='p'] input", "new");
            assert.verifySteps(["web_read"]);

            await click(target, ".test_widget button");
            await nextTick();
            assert.verifyErrors(["Something went wrong"]);

            // Close ErrorDialog
            await click(target, ".o_dialog .btn-close");
            assert.deepEqual(target.querySelectorAll("[name='p'] .o_data_row").length, 1);
            assert.verifySteps(["web_save", "web_read"]);

            await editInput(target, "[name=foo] input", "new value");
            await clickSave(target);
            assert.deepEqual(target.querySelectorAll("[name='p'] .o_data_row").length, 1);
            assert.verifySteps(["web_save"]);
        }
    );

    QUnit.test(
        "coming to an action with an error from a form view with a record in creation",
        async function (assert) {
            assert.expectErrors();

            class TestClientAction extends Component {
                setup() {
                    throw new Error("Something went wrong");
                }
            }
            TestClientAction.template = xml`<div></div>`;
            registry.category("actions").add("TestClientAction", TestClientAction);

            class MyWidget extends Component {
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
            MyWidget.template = xml`
                <div class="test_widget">
                    <button t-on-click="onClick">MyButton</button>
                </div>`;
            const myWidget = {
                component: MyWidget,
            };
            widgetRegistry.add("test_widget", myWidget);
            registry.category("services").add("error", errorService);

            serverData.actions = {
                1: {
                    id: 1,
                    name: "test",
                    res_model: "partner",
                    type: "ir.actions.act_window",
                    views: [[false, "form"]],
                },
            };
            serverData.views = {
                "partner,false,search": `<search></search>`,
                "partner,false,form": `
                    <form>
                        <widget name="test_widget"/>
                        <field name="foo"/>
                    </form>`,
            };

            const mockRPC = async (route, args) => {
                if (args.method === "web_read") {
                    assert.step(args.method);
                    assert.deepEqual(args.args[0], [6]);
                } else if (args.method === "web_save") {
                    assert.step(args.method);
                    assert.deepEqual(args.args[1], {
                        foo: "new value",
                    });
                }
            };
            const webClient = await createWebClient({ serverData, mockRPC });
            await doAction(webClient, 1);
            await editInput(target, "[name=foo] input", "new value");
            assert.strictEqual(target.querySelector("[name=foo] input").value, "new value");

            await click(target, ".test_widget button");
            await nextTick();
            assert.verifyErrors(["Something went wrong"]);

            // Close ErrorDialog
            await click(target, ".o_dialog .btn-close");
            assert.strictEqual(target.querySelector("[name=foo] input").value, "new value");
            assert.verifySteps(["web_save", "web_read"]);
        }
    );

    QUnit.test("only re-render necessary fields after change", async function (assert) {
        function logLifeCycle(Component) {
            patchWithCleanup(Component.prototype, {
                setup() {
                    super.setup(...arguments);
                    const prefix = `${this.constructor.name} ${this.props.name}`;
                    onMounted(() => assert.step(`[${prefix}] onMounted`));
                    onPatched(() => assert.step(`[${prefix}] onPatched`));
                    onWillStart(() => assert.step(`[${prefix}] onWillStart`));
                    onWillUpdateProps(() => assert.step(`[${prefix}] onWillUpdateProps`));
                },
            });
        }
        logLifeCycle(Field);
        logLifeCycle(CharField);
        logLifeCycle(IntegerField);
        logLifeCycle(DateTimeField);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="date"/>
                </form>`,
            resId: 2,
        });

        assert.verifySteps([
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

        await editInput(target, ".o_field_widget[name=foo] input", "new value");

        assert.verifySteps(["[Field foo] onPatched", "[CharField foo] onPatched"]);

        await editInput(target, ".o_field_widget[name=int_field] input", "5846");

        assert.verifySteps(["[Field int_field] onPatched", "[IntegerField int_field] onPatched"]);
    });

    QUnit.test(
        "only re-render necessary fields after change (with onchange)",
        async function (assert) {
            function logLifeCycle(Component) {
                patchWithCleanup(Component.prototype, {
                    setup() {
                        super.setup(...arguments);
                        const prefix = `${this.constructor.name} ${this.props.name}`;
                        onMounted(() => assert.step(`[${prefix}] onMounted`));
                        onPatched(() => assert.step(`[${prefix}] onPatched`));
                        onWillStart(() => assert.step(`[${prefix}] onWillStart`));
                        onWillUpdateProps(() => assert.step(`[${prefix}] onWillUpdateProps`));
                    },
                });
            }
            logLifeCycle(Field);
            logLifeCycle(CharField);
            logLifeCycle(IntegerField);
            logLifeCycle(DateTimeField);

            serverData.models.partner.onchanges = {
                foo(obj) {
                    obj.int_field = 23;
                },
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="foo"/>
                    <field name="int_field"/>
                    <field name="date"/>
                </form>`,
                resId: 2,
            });

            assert.verifySteps([
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

            await editInput(target, ".o_field_widget[name=foo] input", "new value");

            assert.verifySteps([
                "[Field foo] onPatched",
                "[CharField foo] onPatched",
                "[Field int_field] onPatched",
                "[IntegerField int_field] onPatched",
            ]);

            await editInput(target, ".o_field_widget[name=int_field] input", "5846");

            assert.verifySteps([
                "[Field int_field] onPatched",
                "[IntegerField int_field] onPatched",
            ]);
        }
    );

    QUnit.test("widget update several fields including an x2m", async function (assert) {
        assert.expect(7);

        serverData.models.partner.onchanges = {
            name() {},
            p() {},
        };
        class TestWidget extends Component {
            static template = xml`<div><button t-on-click="onClick">Click</button></div>`;

            onClick() {
                this.props.record.update({ name: "New Name", p: [[0, false, { name: "yop" }]] });
            }
        }
        widgetRegistry.add("test", {
            component: TestWidget,
            fieldDependencies: [
                { name: "name", type: "char" },
                { name: "p", type: "one2many", relation: "partner" },
            ],
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <widget name="test"/>
                    <field name="name"/>
                    <field name="p">
                        <tree>
                            <field name="name"/>
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            async mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.strictEqual(args.args[1].name, "New Name");
                    assert.strictEqual(args.args[1].p.length, 1);
                    assert.deepEqual(args.args[1].p[0][2], { name: "yop" });
                }
            },
        });

        assert.strictEqual(target.querySelector("[name=name] input").value, "name");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            []
        );

        await click(target, ".o_widget_test button");
        assert.strictEqual(target.querySelector("[name=name] input").value, "New Name");
        assert.deepEqual(
            [...target.querySelectorAll(".o_data_row")].map((el) => el.textContent),
            ["yop"]
        );
    });

    QUnit.test(
        "commitChanges with a field input removed during an update",
        async function (assert) {
            assert.expect(1);
            serverData.models.partner.records[1].p = [1, 5];
            serverData.models.partner.onchanges = {
                foo() {},
            };

            const def = makeDeferred();

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 2,
                serverData,
                arch: `
                 <form>
                    <field name="p">
                        <tree editable="bottom">
                            <field name="foo"/>
                        </tree>
                    </field>
                </form>`,
                async mockRPC(route, args) {
                    if (args.method === "onchange") {
                        await def;
                    }

                    if (args.method === "web_save") {
                        assert.deepEqual(args.args[1], {
                            p: [[1, 1, { foo: "new foo" }]],
                        });
                    }
                },
            });

            await click(target.querySelector('.o_data_cell[name="foo"]'));
            const input = target.querySelector('.o_data_cell[name="foo"] input');
            input.value = "new foo";
            await triggerEvent(input, null, "input");

            triggerHotkey("Tab");
            await nextTick();

            def.resolve();
            await click(target, ".o_form_button_save");
        }
    );

    QUnit.test("containing a nested x2many list view should not overflow", async function (assert) {
        serverData.models.partner_type.records.push({
            id: 3,
            display_name: "very".repeat(30) + "_long_name",
            color: 10,
        });

        const record = serverData.models.partner.records[0];
        record.timmy = [3];

        await makeView({
            type: "form",
            resModel: "partner",
            resId: record.id,
            serverData,
            arch: `
            <form>
                <sheet>
                    <group>
                        <group/>
                        <group>
                            <field name="timmy" widget="many2many">
                                <tree>
                                    <field name="display_name"/>
                                    <field name="color"/>
                                </tree>
                            </field>
                        </group>
                    </group>
                </sheet>
            </form>`,
        });

        const table = target.querySelector("table");
        const group = target.querySelector(".o_inner_group:last-child");

        assert.equal(group.clientWidth, group.scrollWidth);
        table.style.tableLayout = "auto";
        assert.ok(group.clientWidth < group.scrollWidth);
    });

    QUnit.test(
        "multiple views for m2m field after list item edit in form",
        async function (assert) {
            serverData.models.partner.records[0].timmy = [1, 2];

            serverData.models.partner_type = {
                fields: {
                    m2m: { string: "M2M field", type: "many2many", relation: "extra" },
                },
                records: [
                    { id: 1, display_name: "ma", m2m: [1] },
                    { id: 2, display_name: "cr", m2m: [2] },
                ],
            };

            serverData.models.extra = {
                fields: {
                    name: { string: "Char", type: "char" },
                },
                records: [
                    { id: 1, display_name: "ma", name: "ma" },
                    { id: 2, display_name: "cr", name: "cr" },
                ],
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                resId: 1,
                arch: `
                <form>
                    <field name="timmy">
                        <tree>
                            <field name="display_name"/>
                            <field name="m2m" widget="many2many_tags"/>
                        </tree>
                        <form>
                            <field name="display_name"/>
                            <field name="m2m">
                                <tree>
                                    <field name="name"/>
                                    <field name="display_name"/>
                                </tree>
                             </field>
                        </form>
                    </field>
                </form>`,
            });

            await click(target.querySelectorAll(".o_data_cell")[0]);
            assert.hasClass(
                document.querySelector("body"),
                "modal-open",
                "body should have modal-open class"
            );

            target.querySelector(".modal-body [name='display_name'] input").value = "updated";
            await click(target.querySelector(".modal-footer .o_form_button_save"));

            assert.containsOnce(target, ".o_form_button_save");
            await click(target.querySelector(".o_form_button_save"));

            assert.equal(target.querySelectorAll(".o_data_cell")[0].innerText, "updated");
        }
    );

    QUnit.test("custom x2many with relatedFields and list view inline", async function (assert) {
        class MyField extends X2ManyField {}
        fieldRegistry.add("my_widget", {
            ...x2ManyField,
            component: MyField,
            relatedFields: [
                { name: "trululu", type: "many2one", relation: "partner" },
                { name: "int_field", type: "integer" },
            ],
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="p" widget='my_widget'>
                        <tree editable="bottom" >
                            <field name="foo"/>
                            <field name="int_field" />
                        </tree>
                    </field>
                </form>`,
            resId: 2,
            mockRPC(route, args) {
                if (args.method === "web_read") {
                    assert.step("web_read");
                    assert.deepEqual(args.kwargs.specification.p.fields, {
                        trululu: { fields: { display_name: {} } },
                        foo: {},
                        int_field: {},
                    });
                } else if (args.method === "write") {
                    assert.step("write");
                    assert.deepEqual(args.args[1].p[0][2], {
                        foo: "new record",
                        int_field: 0,
                    });
                } else if (args.method === "web_save") {
                    assert.step("web_save");
                    assert.deepEqual(args.kwargs.specification.p.fields, {
                        trululu: { fields: { display_name: {} } },
                        foo: {},
                        int_field: {},
                    });
                }
            },
        });

        await addRow(target);
        await editInput(target, ".o_data_row [name='foo'] input", "new record");
        await clickSave(target);
        assert.verifySteps(["web_read", "web_save"]);
    });

    QUnit.test(
        "custom x2many with a m2o in relatedFields and column_invisible",
        async function (assert) {
            class MyField extends X2ManyField {}
            fieldRegistry.add("my_widget", {
                ...x2ManyField,
                component: MyField,
                relatedFields: [{ name: "trululu", type: "many2one", relation: "partner" }],
            });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p" widget='my_widget'>
                        <tree editable="bottom" >
                            <field name="foo"/>
                            <field name="trululu" column_invisible="True"/>
                        </tree>
                    </field>
                </form>`,
                resId: 2,
                mockRPC(route, args) {
                    if (args.method === "web_read") {
                        assert.step("web_read");
                        assert.deepEqual(args.kwargs.specification.p.fields, {
                            trululu: { fields: { display_name: {} } },
                            foo: {},
                        });
                    } else if (args.method === "write") {
                        assert.step("write");
                        assert.deepEqual(args.args[1].p[0][2], {
                            foo: "new record",
                            int_field: 0,
                        });
                    } else if (args.method === "web_save") {
                        assert.step("web_save");
                        assert.deepEqual(args.kwargs.specification.p.fields, {
                            trululu: { fields: { display_name: {} } },
                            foo: {},
                        });
                    }
                },
            });

            await addRow(target);
            await editInput(target, ".o_data_row [name='foo'] input", "new record");
            await clickSave(target);
            assert.verifySteps(["web_read", "web_save"]);
        }
    );

    QUnit.test(
        "custom x2many with relatedFields and list view not inline",
        async function (assert) {
            class MyField extends X2ManyField {}
            fieldRegistry.add("my_widget", {
                ...x2ManyField,
                component: MyField,
                relatedFields: [
                    { name: "trululu", type: "many2one", relation: "partner" },
                    { name: "int_field", type: "integer" },
                ],
            });

            serverData.views = {
                "partner,false,list": `
                <tree editable="bottom" >
                    <field name="foo"/>
                    <field name="int_field" />
                </tree>`,
            };

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="p" widget='my_widget'/>
                </form>`,
                resId: 2,
                mockRPC(route, args) {
                    if (args.method === "web_read") {
                        assert.step("web_read");
                        assert.deepEqual(args.kwargs.specification.p.fields, {
                            trululu: { fields: { display_name: {} } },
                            foo: {},
                            int_field: {},
                        });
                    } else if (args.method === "write") {
                        assert.step("write");
                        assert.deepEqual(args.args[1].p[0][2], {
                            foo: "new record",
                            int_field: 0,
                        });
                    } else if (args.method === "web_save") {
                        assert.step("web_save");
                        assert.deepEqual(args.kwargs.specification.p.fields, {
                            trululu: { fields: { display_name: {} } },
                            foo: {},
                            int_field: {},
                        });
                    }
                },
            });

            await addRow(target);
            await editInput(target, ".o_data_row [name='foo'] input", "new record");
            await clickSave(target);
            assert.verifySteps(["web_read", "web_save"]);
        }
    );

    QUnit.test("existing record with falsy display_name", async function (assert) {
        serverData.models.partner.records[0].display_name = "";
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="int_field"/></form>`,
            resId: 1,
        });
        assert.strictEqual(target.querySelector(".o_breadcrumb").innerText, "Unnamed");
    });

    QUnit.test("field with special data", async function (assert) {
        class MyWidget extends Component {
            static template = xml`<div>MyWidget</div>`;
            setup() {
                this.specialData = useSpecialData((orm, props) => {
                    const { record } = props;
                    return orm.call("my.model", "get_special_data", [record.data.int_field]);
                });
            }
        }
        widgetRegistry.add("my_widget", {
            component: MyWidget,
        });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="int_field" />
                    <widget name="my_widget" />
                </form>`,
            resId: 2,
            async mockRPC(route, args) {
                if (args.method === "get_special_data") {
                    assert.step(`get_special_data ${args.args[0]}`);
                    return {};
                }
            },
        });

        await editInput(target, "[name='int_field'] input", "42");
        assert.verifySteps(["get_special_data 9", "get_special_data 42"]);
    });
});
