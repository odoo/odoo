import { expect, test } from "@odoo/hoot";
import { setInputFiles } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Turtle extends models.Model {
    picture_ids = fields.Many2many({
        string: "Pictures",
        relation: "ir.attachment",
    });
    _records = [{ id: 1, picture_ids: [17] }];
}

class IrAttachment extends models.Model {
    _name = "ir.attachment";
    name = fields.Char();
    mimetype = fields.Char();
    _records = [{ id: 17, name: "Marley&Me.jpg", mimetype: "jpg" }];
}

defineModels([Turtle, IrAttachment]);

test("widget many2many_binary", async () => {
    expect.assertions(17);

    mockService("http", () => ({
        post(route, params) {
            expect(route).toBe("/web/binary/upload_attachment");
            expect(params.ufile[0].name).toBe("fake_file.tiff", {
                message: "file is correctly uploaded to the server",
            });
            const file = {
                id: 10,
                name: params.ufile[0].name,
                mimetype: "text/plain",
            };
            IrAttachment._records.push(file);
            return JSON.stringify([file]);
        },
    }));

    IrAttachment._views.list = '<list string="Pictures"><field name="name"/></list>';
    onRpc((args) => {
        if (args.method !== "get_views") {
            expect.step(args.route);
        }
        if (args.method === "web_read" && args.model === "turtle") {
            expect(args.kwargs.specification).toEqual({
                display_name: {},
                picture_ids: {
                    fields: {
                        mimetype: {},
                        name: {},
                    },
                },
            });
        }
        if (args.method === "web_save" && args.model === "turtle") {
            expect(args.kwargs.specification).toEqual({
                display_name: {},
                picture_ids: {
                    fields: {
                        mimetype: {},
                        name: {},
                    },
                },
            });
        }
        if (args.method === "web_read" && args.model === "ir.attachment") {
            expect(args.kwargs.specification).toEqual({
                mimetype: {},
                name: {},
            });
        }
    });

    await mountView({
        type: "form",
        resModel: "turtle",
        arch: `
            <form>
                <group>
                    <field name="picture_ids" widget="many2many_binary" options="{'accepted_file_extensions': 'image/*'}"/>
                </group>
            </form>`,
        resId: 1,
    });

    expect("div.o_field_widget .oe_fileupload").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attachments").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attach").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attach").toHaveText("Pictures");

    expect("input.o_input_file").toHaveAttribute("accept", "image/*");
    expect.verifySteps(["/web/dataset/call_kw/turtle/web_read"]);

    // Set and trigger the change of a file for the input
    const file = new File(["fake_file"], "fake_file.tiff", { type: "text/plain" });
    await contains(".o_file_input_trigger").click();
    await setInputFiles([file]);
    await animationFrame();

    expect(".o_attachment:nth-child(2) .caption a:eq(0)").toHaveText("fake_file.tiff", {
        message: 'value of attachment should be "fake_file.tiff"',
    });
    expect(".o_attachment:nth-child(2) .caption.small a").toHaveText("TIFF", {
        message: "file extension should be correct",
    });
    expect(".o_attachment:nth-child(2) .o_image.o_hover").toHaveAttribute(
        "data-mimetype",
        "text/plain",
        { message: "preview displays the right mimetype" }
    );

    // delete the attachment
    await contains("div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete").click();

    await clickSave();
    expect("div.o_field_widget .oe_fileupload .o_attachments").toHaveCount(1);
    expect.verifySteps([
        "/web/dataset/call_kw/ir.attachment/web_read",
        "/web/dataset/call_kw/turtle/web_save",
    ]);
});

test("widget many2many_binary displays notification on error", async () => {
    expect.assertions(12);

    mockService("http", () => ({
        post(route, params) {
            expect(route).toBe("/web/binary/upload_attachment");
            expect([params.ufile[0].name, params.ufile[1].name]).toEqual(
                ["good_file.txt", "bad_file.txt"],
                { message: "files are correctly sent to the server" }
            );
            const files = [
                {
                    id: 10,
                    name: params.ufile[0].name,
                    mimetype: "text/plain",
                },
                {
                    id: 11,
                    name: params.ufile[1].name,
                    mimetype: "text/plain",
                    error: `Error on file: ${params.ufile[1].name}`,
                },
            ];
            IrAttachment._records.push(files[0]);
            return JSON.stringify(files);
        },
    }));

    IrAttachment._views.list = '<list string="Pictures"><field name="name"/></list>';

    await mountView({
        type: "form",
        resModel: "turtle",
        arch: `
            <form>
                <group>
                    <field name="picture_ids" widget="many2many_binary" options="{'accepted_file_extensions': 'image/*'}"/>
                </group>
            </form>`,
        resId: 1,
    });

    expect("div.o_field_widget .oe_fileupload").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attachments").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attach").toHaveCount(1);
    expect("div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete").toHaveCount(1);

    // Set and trigger the import of 2 files in the input
    const files = [
        new File(["good_file"], "good_file.txt", { type: "text/plain" }),
        new File(["bad_file"], "bad_file.txt", { type: "text/plain" }),
    ];
    await contains(".o_file_input_trigger").click();
    await setInputFiles(files);
    await animationFrame();

    expect(".o_attachment:nth-child(2) .caption a:eq(0)").toHaveText("good_file.txt", {
        message: 'value of attachment should be "good_file.txt"',
    });
    expect("div.o_field_widget .oe_fileupload .o_attachments").toHaveCount(1);
    expect(".o_notification").toHaveCount(1);
    expect(".o_notification_title").toHaveText("Uploading error");
    expect(".o_notification_content").toHaveText("Error on file: bad_file.txt");
    expect(".o_notification_bar").toHaveClass("bg-danger");
});
