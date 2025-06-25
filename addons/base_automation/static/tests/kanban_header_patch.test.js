import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();

    _records = [
        {
            id: 1,
            bar: true,
            foo: "yop",
        },
        {
            id: 2,
            bar: true,
            foo: "blip",
        },
        {
            id: 3,
            bar: true,
            foo: "gnap",
        },
        {
            id: 4,
            bar: false,
            foo: "blip",
        },
    ];
}

defineMailModels();
defineModels([Partner]);

test.tags("desktop");
test("basic grouped rendering with automations", async () => {
    mockService("action", {
        doAction: (action, options) => {
            expect.step(action);
            expect(options).toEqual({
                additionalContext: {
                    active_test: false,
                    search_default_model_id: 42,
                    default_model_id: 42,
                    default_trigger: "on_create_or_write",
                },
            });
        },
    });
    onRpc("ir.model", "search", ({ args, kwargs }) => {
        expect(args).toEqual([[["model", "=", "partner"]]]);
        expect(kwargs.limit).toBe(1);
        return [42]; // model id
    });
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: `
            <kanban class="o_kanban_test">
                <field name="bar" />
                <templates>
                    <t t-name="card">
                        <field name="foo" />
                    </t>
                </templates>
            </kanban>`,
        groupBy: ["bar"],
    });
    expect(".o_kanban_view").toHaveClass("o_kanban_test");
    expect(".o_kanban_renderer").toHaveClass("o_kanban_grouped");
    expect(".o_kanban_group").toHaveCount(2);
    expect(".o_kanban_group:first-child .o_kanban_record").toHaveCount(1);
    expect(".o_kanban_group:nth-child(2) .o_kanban_record").toHaveCount(3);

    await contains(".o_kanban_group:eq(0) .o_kanban_config .dropdown-toggle", {
        visible: false,
    }).click();

    // check available actions in kanban header's config dropdown
    expect(".o-dropdown--menu .o_kanban_toggle_fold").toHaveCount(1);
    expect(".o-dropdown--menu .o_column_automations").toHaveCount(1);
    expect(".o-dropdown--menu .o_column_edit").toHaveCount(0);
    expect(".o-dropdown--menu .o_column_delete").toHaveCount(0);
    expect(".o-dropdown--menu .o_column_archive_records").toHaveCount(0);
    expect(".o-dropdown--menu .o_column_unarchive_records").toHaveCount(0);
    expect.verifySteps([]);
    await contains(".o-dropdown--menu .o_column_automations").click();
    expect.verifySteps(["base_automation.base_automation_act"]);
});
