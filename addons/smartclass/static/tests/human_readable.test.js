import { expect, test } from "@odoo/hoot";
import { formatHumanReadable } from "../src/js/formatters";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Volume extends models.Model {
    _name = "smartclass.volume";
    name = fields.Char({ string: "Name" });
    depth = fields.Float({ string: "Depth (m)" });
    width = fields.Float({ string: "Width (m)" });
    height = fields.Float({ string: "Height (m)" });
    volume = fields.Float({ string: "Volume (m³)", compute: "_compute_volume", store: true });
    category = fields.Selection({
        selection: [
            ["small", "Small"],
            ["medium", "Medium"],
            ["large", "Large"],
        ],
        compute: "_compute_category",
        store: true,
    });
    _records = [
        { name: "Volume 1", id: 1, depth: 4, width: 5, height: 6 },
        { name: "Volume 2", id: 2, depth: 10, width: 10, height: 10 },
        { name: "Volume 3", id: 3, depth: 2.453, width: 1.4355, height: 6.4334 },
    ];
    _views = {
        list: `<list editable="top" multi_edit="1" create="1">
                <field name="width"/>
                <field name="depth"/>
                <field name="height"/>
                <field name="volume" readonly="1" widget="human_readable_widget"/>
                <field name="category" readonly="1"/>
            </list>`,
    };
    _compute_volume() {
        for (const record of this) {
            record.volume = record.depth * record.height * record.width;
        }
    }
    _compute_category() {
        for (const record of this) {
            record.category = "large";
            if (record.volume <= 1) {
                record.category = "small";
            } else if (record.volume <= 100) {
                record.category = "small";
            }
        }
    }
}

defineModels([Volume]);

// ===== TO AVOID GET =====
// Error during test:
// The following error occurred in onWillStart: "cannot find a definition for model "res.users":
// could not get model from server environment (did you forget to use `defineModels()?`)"
onRpc("has_group", () => true);

test("formatHumanReadable function", () => {
    expect(formatHumanReadable(false)).toBe("NaN");
    expect(formatHumanReadable(6000)).toBe("6.00 k");
    expect(formatHumanReadable(6000000)).toBe("6.00 M");
    expect(formatHumanReadable(30000000000)).toBe("30.00 B");
    expect(formatHumanReadable(-3453456)).toBe("-3.45 M");
    expect(formatHumanReadable(-3453.456)).toBe("-3.45 k");
    expect(formatHumanReadable(-3453456.56789)).toBe("-3.45 M");
});

test("human readable widget in list view", async () => {
    await mountView({
        type: "list",
        resModel: "smartclass.volume",
        resIds: [1, 2],
    });

    expect(`td[name=volume]:eq(0)`).toHaveText("120.00");
    expect(`td[name=volume]:eq(1)`).toHaveText("1.00 k");
    expect(`td[name=volume]:eq(2)`).toHaveText("22.65");

    await contains(`td[name=width]:eq(0)`).click();
    await contains(`td[name=width]:eq(0) input`).edit("43.43");
    expect(`td[name=volume]:eq(0)`).toHaveText("1.04 k");
    await contains(`td[name=depth]:eq(0)`).click();
    await contains(`td[name=depth]:eq(0) input`).edit("43.43");
    expect(`td[name=volume]:eq(0)`).toHaveText("11.32 k");
    await contains(`td[name=height]:eq(0)`).click();
    await contains(`td[name=height]:eq(0) input`).edit("43.43");
    expect(`td[name=volume]:eq(0)`).toHaveText("81.92 k");
});
