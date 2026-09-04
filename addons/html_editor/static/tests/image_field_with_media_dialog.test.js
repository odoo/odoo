import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
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

defineModels([Product, ProductImage]);

async function uploadThroughMediaDialog(openSelector) {
    onRpc("/html_editor/attachment/add_data", async (request) => {
        const { params } = await request.json();
        expect.step(`${params.res_model},${params.res_id}`);
        return { id: 1, name: params.name, image_src: "/web/image/1", mimetype: "image/png" };
    });

    await openSelector();
    await waitFor(".o_select_media_dialog");

    const file = new File(["fake image"], "fake_file.png", { type: "image/png" });
    const input = document.querySelector(".o_select_media_dialog .o_file_input");
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    input.files = dataTransfer.files;
    input.dispatchEvent(new Event("change"));
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

    expect.verifySteps(["product,7"]);
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

    expect.verifySteps(["product,7"]);
});
