import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "res.partner";
    _rec_name = "display_name";

    many2one_field = fields.Many2one({ relation: "res.partner" });
    selection_field = fields.Selection({
        selection: [
            ["normal", "Normal"],
            ["blocked", "Blocked"],
            ["done", "Done"],
        ],
    });

    _records = [
        {
            id: 1,
            display_name: "first record",
            many2one_field: 4,
            selection_field: "blocked",
        },
        {
            id: 2,
            display_name: "second record",
            many2one_field: 1,
            selection_field: "normal",
        },
        {
            id: 3,
            display_name: "", // empty value
            selection_field: "done",
        },
        {
            id: 4,
            display_name: "fourth record",
            selection_field: "done",
        },
    ];
}

defineModels([Partner]);

onRpc("has_group", () => true);

test("BadgeField component on a char field in list view", async () => {
    await mountView({
        resModel: "res.partner",
        type: "list",
        arch: `<list><field name="display_name" widget="badge"/></list>`,
    });

    expect(`.o_field_badge[name="display_name"]:contains(first record)`).toHaveCount(1);
    expect(`.o_field_badge[name="display_name"]:contains(second record)`).toHaveCount(1);
    expect(`.o_field_badge[name="display_name"]:contains(fourth record)`).toHaveCount(1);
});

test("BadgeField component on a selection field in list view", async () => {
    await mountView({
        resModel: "res.partner",
        type: "list",
        arch: `<list><field name="selection_field" widget="badge"/></list>`,
    });

    expect(`.o_field_badge[name="selection_field"]:contains(Blocked)`).toHaveCount(1);
    expect(`.o_field_badge[name="selection_field"]:contains(Normal)`).toHaveCount(1);
    expect(`.o_field_badge[name="selection_field"]:contains(Done)`).toHaveCount(2);
});

test("BadgeField component on a many2one field in list view", async () => {
    await mountView({
        resModel: "res.partner",
        type: "list",
        arch: `<list><field name="many2one_field" widget="badge"/></list>`,
    });

    expect(`.o_field_badge[name="many2one_field"]:contains(first record)`).toHaveCount(1);
    expect(`.o_field_badge[name="many2one_field"]:contains(fourth record)`).toHaveCount(1);
});

test("BadgeField component with decoration-xxx attributes", async () => {
    await mountView({
        resModel: "res.partner",
        type: "list",
        arch: `
            <list>
                <field name="selection_field" widget="badge"/>
                <field name="display_name" widget="badge" decoration-danger="selection_field == 'done'" decoration-warning="selection_field == 'blocked'"/>
            </list>
        `,
    });

    expect(`.o_field_badge[name="display_name"]`).toHaveCount(4);
    expect(`.o_field_badge[name="display_name"] .text-bg-danger`).toHaveCount(1);
    expect(`.o_field_badge[name="display_name"] .text-bg-warning`).toHaveCount(1);
});
