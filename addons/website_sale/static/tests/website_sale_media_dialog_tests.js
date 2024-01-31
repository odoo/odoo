import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { MultiMediaDialog } from "@website_sale/js/components/media_dialog/website_sale_media_dialog";

const serverData = {
    models: {
        "product.template": {
            fields: {
                display_name: { string: "Name", type: "char" },
                product_template_image_ids: {
                    string: "Extra Product Media",
                    type: "one2many",
                    relation: "product.image",
                },
            },
            records: [
                {
                    id: 1,
                    display_name: "Product 1",
                    product_template_image_ids: [1, 2],
                },
            ],
        },
        "product.image": {
            fields: {
                name: { string: "Name", type: "char" },
                image_1920: { string: "Image", type: "binary" },
                video_url: { string: "Video URL", type: "char" },
                sequence: { string: "Sequence", type: "integer" },
            },
            records: [
                {
                    id: 1,
                    name: "Image 1",
                    image_1920: "R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==",
                },
                {
                    id: 2,
                    name: "Image 2",
                    image_1920: "R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==",
                    video_url: "https://www.youtube.com/watch?v=123456",
                },
            ],
        },
    },
    views: {
        "product.image,false,kanban": `
            <kanban string="Product Images" >
                <field name="name"/>
                <field name="image_1920"/>
                <field name="video_url"/>
                <field name="sequence" widget="handle"/>
                <templates>
                    <t t-name="kanban-box">
                        <div class="o_squared_image">
                            <field class="card-img-top" name="image_1920"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        "product.template,false,form": `
            <form>
                <group colspan="2" name="product_template_images" string="Extra Product Media">
                    <field colspan="2" name="product_template_image_ids" mode="kanban" widget="product_media_viewer" add-label="Add Media" nolabel="1"/>
                </group>
            </form>`,
    },
};

QUnit.module("ProductTemplate > MediaDialog");

QUnit.test("Adding Media button opens a media dialog", async function (assert) {
    const target = getFixture();
    setupViewRegistries();

    patchWithCleanup(MultiMediaDialog.prototype, {
        setup() {
            this.state = {};
            assert.step("open media dialog");
        },
    });

    await makeView({
        type: "form",
        resId: 1,
        resModel: "product.template",
        serverData,
    });

    await click(target, ".o_field_product_media_viewer .o_cp_buttons button");
    assert.verifySteps(["open media dialog"]);
});
