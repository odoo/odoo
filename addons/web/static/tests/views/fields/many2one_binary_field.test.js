import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class IrAttachment extends models.Model {
    _name = "ir.attachment";
    name = fields.Char();
    mimetype = fields.Char();
    _records = [{ id: 17, name: "Marley&Me.jpg", mimetype: "jpg" }];
}

class Turtle extends models.Model {
    picture_id = fields.Many2one({
        string: "Pictures",
        relation: "ir.attachment",
    });
    _records = [{ id: 1, picture_id: 17 }];
}

defineModels([IrAttachment, Turtle]);

test("widget many2one_binary: only one file upload allowed", async () => {
    expect.assertions(2);

    // Mount form view with many2one_binary field
    await mountView({
        type: "form",
        resModel: "turtle",
        arch: `
            <form>
                <group>
                    <field name="picture_id" widget="many2one_binary"
                        options="{'accepted_file_extensions': 'image/*'}"/>
                </group>
            </form>
        `,
        resId: 1,
    });

    // Confirm that attachment is displayed
    expect(".o_attachment .caption a:eq(0)").toHaveText("Marley&Me.jpg");

    // Confirm that the upload input is hidden or removed after a file is already present
    expect("input.o_input_file").toHaveCount(0, {
        message: "Upload input should be removed after one file is uploaded",
    });
});
