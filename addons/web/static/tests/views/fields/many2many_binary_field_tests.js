/** @odoo-module **/

import { click, clickSave, getFixture, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

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
        assert.expect(24);

        const fakeHTTPService = {
            start() {
                return {
                    post: (route, params) => {
                        assert.strictEqual(route, "/web/binary/upload_attachment");
                        assert.strictEqual(
                            params.ufile[0].name,
                            "fake_file.tiff",
                            "file is correctly uploaded to the server"
                        );
                        const file = {
                            id: 10,
                            name: params.ufile[0].name,
                            mimetype: "text/plain",
                        };
                        serverData.models["ir.attachment"].records.push(file);
                        return JSON.stringify([file]);
                    },
                };
            },
        };
        serviceRegistry.add("http", fakeHTTPService);

        serverData.views = {
            "ir.attachment,false,list": '<tree string="Pictures"><field name="name"/></tree>',
        };

        await makeView({
            serverData,
            type: "form",
            resModel: "turtle",
            arch: `
                <form>
                    <group>
                        <field name="picture_ids" widget="many2many_binary" options="{'accepted_file_extensions': 'image/*'}"/>
                    </group>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method !== "get_views") {
                    assert.step(route);
                }
                if (route === "/web/dataset/call_kw/ir.attachment/read") {
                    assert.deepEqual(args.args[1], ["name", "mimetype", "res_id", "access_token"]);
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
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attach",
            "there should be an Add button (edit)"
        );
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete",
            "there should be a Delete button (edit)"
        );

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

        // Set and trigger the change of a file for the input
        const fileInput = target.querySelector('input[type="file"]');
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(new File(["fake_file"], "fake_file.tiff", { type: "text/plain" }));
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event("change", { bubbles: true }));
        await nextTick();

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
        assert.strictEqual(
            target.querySelector(".o_attachment:nth-child(2) .o_image.o_hover").dataset.mimetype,
            "text/plain",
            "preview displays the right mimetype"
        );

        // delete the attachment
        await click(
            target.querySelector(
                "div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete"
            )
        );

        await clickSave(target);
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attachments",
            "there should be only one attachment left"
        );
        assert.verifySteps([
            "/web/dataset/call_kw/ir.attachment/read",
            "/web/dataset/call_kw/turtle/write",
            "/web/dataset/call_kw/turtle/read",
            "/web/dataset/call_kw/ir.attachment/read",
        ]);
    });

    QUnit.test("widget many2many_binary displays notification on error", async function (assert) {
        assert.expect(12);

        const fakeHTTPService = {
            start() {
                return {
                    post: (route, params) => {
                        assert.strictEqual(route, "/web/binary/upload_attachment");
                        assert.deepEqual(
                            [params.ufile[0].name, params.ufile[1].name],
                            ["good_file.txt", "bad_file.txt"],
                            "files are correctly sent to the server"
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
                        serverData.models["ir.attachment"].records.push(files[0]);
                        return JSON.stringify(files);
                    },
                };
            },
        };
        serviceRegistry.add("http", fakeHTTPService);

        serverData.views = {
            "ir.attachment,false,list": '<tree string="Pictures"><field name="name"/></tree>',
        };

        await makeView({
            serverData,
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
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attach",
            "there should be an Add button (edit)"
        );
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attachment .o_attachment_delete",
            "there should be a Delete button (edit)"
        );

        // Set and trigger the import of 2 files in the input
        const fileInput = target.querySelector('input[type="file"]');
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(new File(["good_file"], "good_file.txt", { type: "text/plain" }));
        dataTransfer.items.add(new File(["bad_file"], "bad_file.txt", { type: "text/plain" }));
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event("change", { bubbles: true }));
        await nextTick();

        assert.strictEqual(
            target.querySelector(".o_attachment:nth-child(2) .caption a").textContent,
            "good_file.txt",
            'value of attachment should be "good_file.txt"'
        );
        assert.containsOnce(
            target,
            "div.o_field_widget .oe_fileupload .o_attachments",
            "there should be only one attachment uploaded"
        );
        assert.containsOnce(target, ".o_notification");
        assert.strictEqual(
            target.querySelector(".o_notification_title").textContent,
            "Uploading error"
        );
        assert.strictEqual(
            target.querySelector(".o_notification_content").textContent,
            "Error on file: bad_file.txt"
        );
        assert.hasClass(target.querySelector(".o_notification"), "border-danger");
    });
});
