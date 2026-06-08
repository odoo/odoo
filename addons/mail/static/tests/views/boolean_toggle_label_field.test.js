import { contains, mailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    boolean_field = fields.Boolean();

    _records = [{ id: 1, boolean_field: false }];
}

defineModels({ ...mailModels, Partner });

test("use BooleanToggleLabelField in form view", async () => {
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="boolean_field" string="btnLabel" widget="mail_boolean_toggle_label"
                          options="{'btn_class_on': 'btn-primary', 'btn_class_off': 'btn-secondary'}"/>
                      <div class="boolean_field_on" invisible="boolean_field">on</div>
                      <div class="boolean_field_off" invisible="not boolean_field">off</div>
               </form>`,
    });
    await contains(".o_field_mail_boolean_toggle_label .btn-secondary", { text: "btnLabel" });
    expect(".boolean_field_on").toHaveCount(1);
    expect(".boolean_field_off").toHaveCount(0);
    await click(".o_field_mail_boolean_toggle_label button");
    await contains(".boolean_field_off");
    await contains(".boolean_field_on", { count: 0 });
});

test("BooleanToggleLabelField is disabled with a readonly attribute", async () => {
    await mountView({
        resModel: "partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="boolean_field" widget="mail_boolean_toggle_label" readonly="1"/></form>`,
    });
    expect(`.o_field_mail_boolean_toggle_label`).toHaveCount(1);
    expect(`.o_field_mail_boolean_toggle_label button`).not.toBeEnabled();
});

test("BooleanToggleLabelField is disabled if readonly in editable list", async () => {
    Partner._fields.boolean_field.readonly = true;

    onRpc("has_group", () => true);
    await mountView({
        resModel: "partner",
        type: "list",
        arch: `
            <list editable="bottom">
                <field name="boolean_field" widget="mail_boolean_toggle_label"
                    options="{'btn_class_on': 'btn-primary', 'btn_class_off': 'btn-secondary'}"/>
            </list>
        `,
    });
    expect(".o_field_mail_boolean_toggle_label button").not.toBeEnabled();
    await contains(".o_field_mail_boolean_toggle_label button.btn-secondary");
    await contains(".o_field_mail_boolean_toggle_label button.btn-primary", { count: 0 });

    await click(`.o_field_mail_boolean_toggle_label button`);
    await animationFrame();
    await contains(".o_field_mail_boolean_toggle_label button.btn-secondary");
    await contains(".o_field_mail_boolean_toggle_label button.btn-primary", { count: 0 });
});
