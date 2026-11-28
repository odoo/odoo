import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    MockServer,
    models,
    mountViewInDialog,
    onRpc,
    selectFieldDropdownItem,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

class HrTestTarget extends models.Model {
    _name = "hr.test.target";
    name = fields.Char();
    _records = [{ id: 1, name: "first target" }];
    _views = { form: '<form><field name="name"/></form>' };
}

class HrTestRecord extends models.Model {
    _name = "hr.test.record";
    note = fields.Char();
    target_id = fields.Many2one({ relation: "hr.test.target" });
    _records = [{ id: 1, note: "first target", target_id: 1 }];
    _onChanges = {
        target_id(record) {
            const id = Array.isArray(record.target_id) ? record.target_id[0] : record.target_id;
            const target = MockServer.env["hr.test.target"].find((r) => r.id === id);
            record.note = target?.name || false;
        },
    };
}

defineMailModels();
defineModels([HrTestTarget, HrTestRecord]);

const arch = `
    <form>
        <field name="note"/>
        <field name="target_id" widget="many2one_extended" options="{'no_save_on_open': True}"/>
    </form>`;

/**
 * Opens the target from the record dialog, renames it and saves it.
 */
async function renameTargetInDialog() {
    await contains(".o_field_widget .o_external_button", { visible: false }).click();
    expect(".modal").toHaveCount(2);
    expect.verifySteps([]);

    await contains(".o_dialog:not(.o_inactive_modal) .o_field_widget[name=name] input").edit(
        "renamed target"
    );
    await contains(
        ".o_dialog:not(.o_inactive_modal) .modal-footer .btn-primary:not(.d-none)"
    ).click();
    expect(".modal").toHaveCount(1);
    expect.verifySteps(["web_save hr.test.target"]);
}

test("no_save_on_open: new record, open the related record without saving it", async () => {
    // Saving the related record triggers the onchange, which reads the new data of the record.
    onRpc("get_formview_id", () => false);
    onRpc("web_save", ({ model }) => expect.step(`web_save ${model}`));
    await mountViewInDialog({ type: "form", resModel: "hr.test.record", arch });
    await selectFieldDropdownItem("target_id", "first target");

    await renameTargetInDialog();
    expect(".o_field_widget[name=target_id] input").toHaveValue("renamed target");
    expect(".o_field_widget[name=note] input").toHaveValue("renamed target");
});

test("no_save_on_open: existing record, open the related record without saving it", async () => {
    // Saving the related record reloads the record, and keeps its pending changes.
    onRpc("get_formview_id", () => false);
    onRpc("web_save", ({ model }) => expect.step(`web_save ${model}`));
    await mountViewInDialog({ type: "form", resModel: "hr.test.record", resId: 1, arch });
    await contains(".o_field_widget[name=note] input").edit("pending note");

    await renameTargetInDialog();
    expect(".o_field_widget[name=target_id] input").toHaveValue("renamed target");
    expect(".o_field_widget[name=note] input").toHaveValue("pending note");
});
