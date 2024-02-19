import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { test, expect } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";

class Partner extends models.Model {
    foo = fields.Char({
        string: "Foo",
        default: "My little Foo Value",
        searchable: true,
        trim: true,
    });
    int_field = fields.Integer({
        string: "int_field",
        sortable: true,
        searchable: true,
    });
    float_field = fields.Float({
        string: "float_field",
        sortable: true,
        searchable: true,
    });
    _records = [
        { id: 1, foo: "yop", int_field: 10 },
        { id: 2, foo: "gnap", int_field: 80 },
        { id: 3, foo: "blip", float_field: 33.3333 },
    ];
}

defineModels([Partner]);

test("PercentPieField in form view with value < 50%", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
                <form>
                    <sheet>
                        <group>
                            <field name="int_field" widget="percentpie"/>
                        </group>
                    </sheet>
                </form>`,
        resId: 1,
    });

    expect(".o_field_percent_pie.o_field_widget .o_pie").toHaveCount(1);
    expect(".o_field_percent_pie.o_field_widget .o_pie_info .o_pie_value").toHaveText("10%", {
        message: "should have 10% as pie value since int_field=10",
    });

    expect(
        queryOne(".o_field_percent_pie.o_field_widget .o_pie").style.background.replaceAll(
            /\s+/g,
            " "
        )
    ).toBe(
        "conic-gradient( var(--PercentPieField-color-active) 0% 10%, var(--PercentPieField-color-static) 0% 100% )",
        { message: "pie should have a background computed for its value of 10%" }
    );
});

test("PercentPieField in form view with value > 50%", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
                <form>
                    <sheet>
                        <group>
                            <field name="int_field" widget="percentpie"/>
                        </group>
                    </sheet>
                </form>`,
        resId: 2,
    });

    expect(".o_field_percent_pie.o_field_widget .o_pie").toHaveCount(1);
    expect(".o_field_percent_pie.o_field_widget .o_pie_info .o_pie_value").toHaveText("80%", {
        message: "should have 80% as pie value since int_field=80",
    });
    expect(
        queryOne(".o_field_percent_pie.o_field_widget .o_pie").style.background.replaceAll(
            /\s+/g,
            " "
        )
    ).toBe(
        "conic-gradient( var(--PercentPieField-color-active) 0% 80%, var(--PercentPieField-color-static) 0% 100% )",
        { message: "pie should have a background computed for its value of 80%" }
    );
});

test("PercentPieField in form view with float value", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
                <form>
                    <sheet>
                        <group>
                            <field name="float_field" widget="percentpie"/>
                        </group>
                    </sheet>
                </form>`,
        resId: 3,
    });

    expect(".o_field_percent_pie.o_field_widget .o_pie").toHaveCount(1);
    expect(".o_field_percent_pie.o_field_widget .o_pie_info .o_pie_value").toHaveText("33.33%", {
        message:
            "should have 33.33% as pie value since float_field=33.3333 and its value is rounded to 2 decimals",
    });
    expect(
        queryOne(".o_field_percent_pie.o_field_widget .o_pie").style.background.replaceAll(
            /\s+/g,
            " "
        )
    ).toBe(
        "conic-gradient( var(--PercentPieField-color-active) 0% 33.3333%, var(--PercentPieField-color-static) 0% 100% )",
        { message: "pie should have a background computed for its value of 33.3333%" }
    );
});
