import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    name = fields.Char();
    image_1920 = fields.Binary();
    image_128 = fields.Binary();

    _records = [
        { id: 1, name: "first record" },
        { id: 2, name: "second record" },
    ];
}

defineModels([Partner]);

test("ContactImageField renders a placeholder when no value is present", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: `
            <form>
                <field name="image_1920" widget="contact_image" options="{'preview_image': 'image_128'}"/>
            </form>`,
    });

    expect('div[name="image_1920"] img').toHaveAttribute(
        "data-src",
        "/web/static/img/placeholder.png",
        { message: "the image should have the correct src" }
    );
});
