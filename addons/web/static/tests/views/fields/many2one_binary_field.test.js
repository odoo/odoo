import { expect, test } from "@odoo/hoot";
import { setInputFiles } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    MockServer,
    mockService,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";

class IrAttachment extends models.Model {
    _name = "ir.attachment";
    name = fields.Char();
    mimetype = fields.Char();
}

class Turtle extends models.Model {
    picture_id = fields.Many2one({
        string: "Pictures",
        relation: "ir.attachment",
    });
    _records = [{ id: 1 }];
}

defineModels([IrAttachment, Turtle]);

test("widget many2one_binary", async () => {
    expect.assertions(7);

    // Mock the http service to handle the upload
    mockService("http", {
        post(route, { ufile }) {
            expect(route).toBe("/web/binary/upload_attachment");
            expect(ufile[0].name).toBe("Marley&Me.jpg", {
                message: "the correct file is sent to the server",
            });
            const ids = MockServer.env["ir.attachment"].create({
                name: ufile[0].name,
                mimetype: "image/jpeg",
            });
            return JSON.stringify(MockServer.env["ir.attachment"].read(ids));
        },
    });

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

    expect("div.o_field_widget .oe_fileupload").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attach").toHaveCount(1);

    // Set and trigger the import of file in the input
    await contains(".o_file_input_trigger").click();
    await setInputFiles([new File(["Marley&Me"], "Marley&Me.jpg", { type: "image/jpeg" })]);
    await animationFrame();

    // Confirm that attachment is displayed
    expect(".o_attachment .caption a:eq(0)").toHaveText("Marley&Me.jpg");

    // Confirm that the upload input is hidden or removed after a file is already present
    expect("input.o_input_file").toHaveCount(0, {
        message: "Upload input should be removed after one file is uploaded",
    });

    // delete the attachment
    await contains("div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete").click();

    // Confirm that attachment is removed
    expect(".o_attachment").toHaveCount(0, {
        message: "Attachment should be removed after clicking delete",
    });
});

test("widget many2one_binary displays notification on error", async () => {
    expect.assertions(7);

    // Mock the http service to simulate an upload error
    mockService("http", {
        post(route, { ufile }) {
            expect(route).toBe("/web/binary/upload_attachment");
            expect(ufile[0].name).toBe("bad_file.txt", {
                message: "the correct file is sent to the server",
            });
            return JSON.stringify([
                {
                    name: ufile[0].name,
                    mimetype: "text/plain",
                    error: `Error on file: ${ufile[0].name}`,
                },
            ]);
        },
    });

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

    expect("div.o_field_widget .oe_fileupload").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attach").toHaveCount(1);

    // Set and trigger the import of 2 files in the input
    await contains(".o_file_input_trigger").click();
    await setInputFiles([new File(["bad_file"], "bad_file.txt", { type: "text/plain" })]);
    await animationFrame();

    // Confirm that the notification is displayed
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_content").toHaveText("Uploading error. Error on file: bad_file.txt");
    expect(".o_notification_bar").toHaveClass("bg-danger");
});
