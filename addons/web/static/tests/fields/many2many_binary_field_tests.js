/** @odoo-module **/

import { click, getFixture, nextTick, patchWithCleanup } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";
import { FileUploader } from "@web/fields/file_handler";

let target;
let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                turtle: {
                    fields: {
                        picture_ids: {
                            string: "Pictures",
                            type: "many2many",
                            relation: "ir.attachment",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            picture_ids: [17],
                        },
                    ],
                },
                "ir.attachment": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        mimetype: { string: "Mimetype", type: "char" },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Marley&Me.jpg",
                            mimetype: "jpg",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("Many2ManyBinaryField");

    QUnit.test("widget many2many_binary", async function (assert) {
        assert.expect(23);

        patchWithCleanup(FileUploader.prototype, {
            async onFileChange(ev) {
                const file = new File([ev.target.value], ev.target.value + ".tiff", {
                    type: "text/plain",
                });
                await this._super({
                    target: { files: [file] },
                });
            },
        });
        serverData.views = {
            "ir.attachment,false,list": '<tree string="Pictures"><field name="name"/></tree>',
        };

        await makeView({
            serverData,
            type: "form",
            resModel: "turtle",
            arch:
                '<form string="Turtles">' +
                '<group><field name="picture_ids" widget="many2many_binary" options="{\'accepted_file_extensions\': \'image/*\'}"/></group>' +
                "</form>",
            resId: 1,
            mockRPC(route, args) {
                if (args.method !== "get_views") {
                    assert.step(route);
                }
                if (route === "/web/dataset/call_kw/ir.attachment/read") {
                    assert.deepEqual(args.args[1], ["name", "mimetype"]);
                }
            },
        });

        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload",
            "there should be the attachment widget"
        );
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attachments",
            "there should be one attachment"
        );
        assert.containsNone(
            target,
            "div.o_field_widget .oe_fileupload .o_attach",
            "there should not be an Add button (readonly)"
        );
        assert.containsNone(
            target,
            "div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete",
            "there should not be a Delete button (readonly)"
        );

        // to edit mode
        await click(target, ".o_form_button_edit");
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attach",
            "there should be an Add button"
        );
        assert.strictEqual(
            target.querySelector("div.o_field_widget .oe_fileupload .o_attach").textContent.trim(),
            "Pictures",
            "the button should be correctly named"
        );

        assert.strictEqual(
            target.querySelector("input.o_input_file").getAttribute("accept"),
            "image/*",
            'there should be an attribute "accept" on the input'
        );
        assert.verifySteps([
            "/web/dataset/call_kw/turtle/read",
            "/web/dataset/call_kw/ir.attachment/read",
        ]);

        const input = target.querySelector(".o_field_many2many_binary input");
        // We need to convert the input type since we can't programmatically set
        // the value of a file input. The patch of the onFileChange will create
        // a file object to be used by the component.
        input.setAttribute("type", "text");
        input.value = "fake_file";
        input.dispatchEvent(new InputEvent("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
        await nextTick();
        await nextTick();

        assert.verifySteps([
            "/web/dataset/call_kw/ir.attachment/name_create",
            "/web/dataset/call_kw/ir.attachment/read",
        ]);
        assert.strictEqual(
            target.querySelector(".o_attachment:nth-child(2) .caption a").textContent,
            "fake_file.tiff",
            'value of attachment should be "fake_file.tiff"'
        );
        assert.strictEqual(
            target.querySelector(".o_attachment:nth-child(2) .caption.small a").textContent,
            "tiff",
            "file extension should be correct"
        );

        // delete the attachment
        await click(
            target.querySelector(
                "div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete"
            )
        );

        await click(target, ".o_form_button_save");
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attachments",
            "there should be only one attachment left"
        );
        assert.verifySteps([
            "/web/dataset/call_kw/turtle/write",
            "/web/dataset/call_kw/turtle/read",
            "/web/dataset/call_kw/ir.attachment/read",
        ]);
    });
});
