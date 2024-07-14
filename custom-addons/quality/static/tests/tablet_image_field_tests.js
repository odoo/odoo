/** @odoo-module **/
import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;
const MY_IMAGE =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";

QUnit.module("Quality", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        document: { string: "Binary", type: "binary" },
                    },
                    records: [
                        {
                            id: 1,
                        },
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.module("TabletImageField");

    QUnit.test("tablet image field: open a preview when clicked", async function (assert) {
        serverData.models.partner.records[0].document = MY_IMAGE;

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
            <form>
                <field name="document" widget="tablet_image" options="{'size': [90, 90]}" />
            </form>`,
        });

        assert.containsOnce(
            target,
            ".o_field_tablet_image",
            "field is present in the view"
        );
        assert.strictEqual(
            target.querySelector("#picture_button button").textContent,
            "Take a Picture",
            "button to open the modal displays the right text"
        );

        await click(target, ".o_field_tablet_image img");
        assert.containsOnce(target, ".o_dialog", "a dialog is present");
        assert.strictEqual(
            target.querySelector(".o_viewer_img_wrapper img").dataset.src,
            `data:image/png;base64,${MY_IMAGE}`,
            "the dialog contains the right image"
        );

        await click(target, ".modal-footer button");        
        await click(target, ".o_field_tablet_image button:not(#picture_button button)");
        assert.containsNone(target, ".o_dialog", "no dialog should be present");
        assert.strictEqual(
            target.querySelector(".o_field_tablet_image img").dataset.src,
            "/web/static/img/placeholder.png",
            "the dialog contains the right image"
        );
    });
});
