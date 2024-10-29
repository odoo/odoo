import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    foo = fields.Char({ default: "My little Foo Value" });
    int_field = fields.Integer({ string: "int_field" });
    qux = fields.Float({ digits: [16, 1] });
    monetary = fields.Monetary({ currency_field: "" });

    _records = [{ id: 1, foo: "yop", int_field: 10, qux: 0.44444, monetary: 9.999999 }];
}

defineModels([Partner]);

test("StatInfoField formats decimal precision", async () => {
    // sometimes the round method can return numbers such as 14.000001
    // when asked to round a number to 2 decimals, as such is the behaviour of floats.
    // we check that even in that eventuality, only two decimals are displayed
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <button class="oe_stat_button" name="items" icon="fa-gear">
                    <field name="qux" widget="statinfo" />
                </button>
                <button class="oe_stat_button" name="money" icon="fa-money">
                    <field name="monetary" widget="statinfo" />
                </button>
            </form>
        `,
    });

    // formatFloat renders according to this.field.digits
    expect("button.oe_stat_button .o_field_widget .o_stat_value:eq(0)").toHaveText("0.4", {
        message: "Default precision should be [16,1]",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_value:eq(1)").toHaveText("10.00", {
        message: "Currency decimal precision should be 2",
    });
});

test.tags("desktop")("StatInfoField in form view on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <div class="oe_button_box" name="button_box">
                    <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                        <field name="int_field" widget="statinfo" />
                    </button>
                </div>
            </form>
        `,
    });

    expect("button.oe_stat_button .o_field_widget .o_stat_info").toHaveCount(1, {
        message: "should have one stat button",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_value").toHaveText("10", {
        message: "should have 10 as value",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_text").toHaveText("int_field", {
        message: "should have 'int_field' as text",
    });
});

test.tags("mobile")("StatInfoField in form view on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <div class="oe_button_box" name="button_box">
                    <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                        <field name="int_field" widget="statinfo" />
                    </button>
                </div>
            </form>
        `,
    });

    await contains(".o-form-buttonbox .o_button_more").click();
    expect("button.oe_stat_button .o_field_widget .o_stat_info").toHaveCount(1, {
        message: "should have one stat button",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_value").toHaveText("10", {
        message: "should have 10 as value",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_text").toHaveText("int_field", {
        message: "should have 'int_field' as text",
    });
});

test.tags("desktop")(
    "StatInfoField in form view with specific label_field on desktop",
    async () => {
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: /* xml */ `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                            <field string="Useful stat button" name="int_field" widget="statinfo" options="{'label_field': 'foo'}" />
                        </button>
                    </div>
                    <group>
                        <field name="foo" invisible="1" />
                    </group>
                </sheet>
            </form>
        `,
        });

        expect("button.oe_stat_button .o_field_widget .o_stat_info").toHaveCount(1, {
            message: "should have one stat button",
        });
        expect("button.oe_stat_button .o_field_widget .o_stat_value").toHaveText("10", {
            message: "should have 10 as value",
        });
        expect("button.oe_stat_button .o_field_widget .o_stat_text").toHaveText("yop", {
            message: "should have 'yop' as text, since it is the value of field foo",
        });
    }
);

test.tags("mobile")("StatInfoField in form view with specific label_field on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                            <field string="Useful stat button" name="int_field" widget="statinfo" options="{'label_field': 'foo'}" />
                        </button>
                    </div>
                    <group>
                        <field name="foo" invisible="1" />
                    </group>
                </sheet>
            </form>
        `,
    });

    await contains(".o-form-buttonbox .o_button_more").click();
    expect("button.oe_stat_button .o_field_widget .o_stat_info").toHaveCount(1, {
        message: "should have one stat button",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_value").toHaveText("10", {
        message: "should have 10 as value",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_text").toHaveText("yop", {
        message: "should have 'yop' as text, since it is the value of field foo",
    });
});

test.tags("desktop")("StatInfoField in form view with no label on desktop", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                            <field string="Useful stat button" name="int_field" widget="statinfo" nolabel="1" />
                        </button>
                    </div>
                </sheet>
            </form>
        `,
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_info").toHaveCount(1, {
        message: "should have one stat button",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_value").toHaveText("10", {
        message: "should have 10 as value",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_text").toHaveCount(0, {
        message: "should not have any label",
    });
});

test.tags("mobile")("StatInfoField in form view with no label on mobile", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                            <field string="Useful stat button" name="int_field" widget="statinfo" nolabel="1" />
                        </button>
                    </div>
                </sheet>
            </form>
        `,
    });
    await contains(".o-form-buttonbox .o_button_more").click();
    expect("button.oe_stat_button .o_field_widget .o_stat_info").toHaveCount(1, {
        message: "should have one stat button",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_value").toHaveText("10", {
        message: "should have 10 as value",
    });
    expect("button.oe_stat_button .o_field_widget .o_stat_text").toHaveCount(0, {
        message: "should not have any label",
    });
});
