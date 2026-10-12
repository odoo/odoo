import { expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, queryOne, waitFor } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

const MY_IMAGE =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";

class Product extends models.Model {
    _name = "product";

    name = fields.Char();
    image = fields.Binary();
    image_ids = fields.One2many({ relation: "product.image", string: "Images" });

    _records = [{ id: 7, name: "Test product", image: MY_IMAGE, image_ids: [] }];
}

class ProductImage extends models.Model {
    _name = "product.image";

    name = fields.Char();
    video_url = fields.Char();
    image_1920 = fields.Binary();

    _records = [];
}

class IrAttachment extends models.Model {
    _name = "ir.attachment";

    name = fields.Char();
    description = fields.Char();
    mimetype = fields.Char();
    checksum = fields.Char();
    url = fields.Char();
    type = fields.Char();
    raw = fields.Binary();
    res_id = fields.Integer();
    res_model = fields.Char();
    public = fields.Boolean();
    access_token = fields.Char();
    image_src = fields.Char();
    image_width = fields.Integer();
    image_height = fields.Integer();
    original_id = fields.Many2one({ relation: "ir.attachment" });

    _records = [
        {
            id: 1,
            name: "fake_file.png",
            mimetype: "image/png",
            raw: MY_IMAGE,
            image_src: "/web/image/1",
        },
    ];
}

defineModels([Product, ProductImage, IrAttachment]);

async function uploadThroughMediaDialog(openSelector) {
    onRpc("/html_editor/attachment/add_data", async (request) => {
        const { params } = await request.json();
        expect.step(`${params.res_model},${params.res_id}`);
        return { id: 1, name: params.name, image_src: "/web/image/1", mimetype: "image/png" };
    });

    await openSelector();
    await waitFor(".o_select_media_dialog");

    const fileInput = queryOne(".o_select_media_dialog input.d-none.o_file_input");
    Object.defineProperty(fileInput, "files", {
        value: [new File([], "fake_file.png", { type: "image/png" })],
    });
    manuallyDispatchProgrammaticEvent(fileInput, "change");
}

test("image_with_media_dialog uploads against the form record", async () => {
    await uploadThroughMediaDialog(async () => {
        await mountView({
            type: "form",
            resId: 7,
            resModel: "product",
            arch: `
                <form>
                    <field name="image" widget="image_with_media_dialog"/>
                </form>`,
        });
        await click(".o_select_file_button");
    });

    await expect.waitForSteps(["product,7"]);
});

test("x2_many_media_viewer uploads against the parent form record", async () => {
    await uploadThroughMediaDialog(async () => {
        await mountView({
            type: "form",
            resId: 7,
            resModel: "product",
            arch: `
                <form>
                    <field name="image_ids" mode="kanban" widget="x2_many_media_viewer">
                        <kanban>
                            <templates>
                                <t t-name="card">
                                    <field name="image_1920" widget="x2_many_image"/>
                                </t>
                            </templates>
                        </kanban>
                    </field>
                </form>`,
        });
        await click(".o-kanban-button-new");
    });

    await expect.waitForSteps(["product,7"]);
});
