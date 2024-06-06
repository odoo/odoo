/** @odoo-module **/

import { registerCleanup } from "@web/../tests/helpers/cleanup";
import { makeMockXHR } from "@web/../tests/helpers/mock_services";
import {
    click,
    clickSave,
    editInput,
    getFixture,
    makeDeferred,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";
import { RPCError } from "@web/core/network/rpc_service";
import { MAX_FILENAME_SIZE_BYTES } from "@web/views/fields/binary/binary_field";
import { toBase64Length } from "@web/core/utils/binary";

const BINARY_FILE =
    "R0lGODlhDAAMAKIFAF5LAP/zxAAAANyuAP/gaP///wAAAAAAACH5BAEAAAUALAAAAAAMAAwAAAMlWLPcGjDKFYi9lxKBOaGcF35DhWHamZUW0K4mAbiwWtuf0uxFAgA7";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            trim: true,
                        },
                        document: { string: "Binary", type: "binary" },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            foo: "coucou.txt",
                            document: "coucou==\n",
                        },
                    ],
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BinaryField");

    QUnit.test("BinaryField is correctly rendered (readonly)", async function (assert) {
        assert.expect(6);

        async function send(data) {
            assert.ok(data instanceof FormData);
            assert.strictEqual(
                data.get("field"),
                "document",
                "we should download the field document"
            );
            assert.strictEqual(
                data.get("data"),
                "coucou==\n",
                "we should download the correct data"
            );

            this.status = 200;
            this.response = new Blob([data.get("data")], { type: "text/plain" });
        }
        const MockXHR = makeMockXHR("", send);

        patchWithCleanup(
            browser,
            {
                XMLHttpRequest: MockXHR,
            },
            { pure: true }
        );

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form edit="0">
                    <field name="document" filename="foo"/>
                    <field name="foo"/>
                </form>`,
            resId: 1,
        });
        assert.containsOnce(
            target,
            '.o_field_widget[name="document"] a > .fa-download',
            "the binary field should be rendered as a downloadable link in readonly"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="document"]').textContent,
            "coucou.txt",
            "the binary field should display the name of the file in the link"
        );
        assert.strictEqual(
            target.querySelector(".o_field_char").textContent,
            "coucou.txt",
            "the filename field should have the file name as value"
        );

        // Testing the download button in the field
        // We must avoid the browser to download the file effectively
        const prom = makeDeferred();
        const downloadOnClick = (ev) => {
            const target = ev.target;
            if (target.tagName === "A" && "download" in target.attributes) {
                ev.preventDefault();
                document.removeEventListener("click", downloadOnClick);
                prom.resolve();
            }
        };
        document.addEventListener("click", downloadOnClick);
        registerCleanup(() => document.removeEventListener("click", downloadOnClick));
        await click(target.querySelector('.o_field_widget[name="document"] a'));
        await prom;
    });

    QUnit.test("BinaryField is correctly rendered", async function (assert) {
        assert.expect(12);

        async function send(data) {
            assert.ok(data instanceof FormData);
            assert.strictEqual(
                data.get("field"),
                "document",
                "we should download the field document"
            );
            assert.strictEqual(
                data.get("data"),
                "coucou==\n",
                "we should download the correct data"
            );

            this.status = 200;
            this.response = new Blob([data.get("data")], { type: "text/plain" });
        }
        const MockXHR = makeMockXHR("", send);

        patchWithCleanup(
            browser,
            {
                XMLHttpRequest: MockXHR,
            },
            { pure: true }
        );

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="document" filename="foo"/>
                    <field name="foo"/>
                </form>`,
            resId: 1,
        });

        assert.containsNone(
            target,
            '.o_field_widget[name="document"] a > .fa-download',
            "the binary field should not be rendered as a downloadable link in edit"
        );
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="document"].o_field_binary .o_input').value,
            "coucou.txt",
            "the binary field should display the file name in the input edit mode"
        );
        assert.containsOnce(
            target,
            ".o_field_binary .o_clear_file_button",
            "there shoud be a button to clear the file"
        );
        assert.strictEqual(
            target.querySelector(".o_field_char input").value,
            "coucou.txt",
            "the filename field should have the file name as value"
        );

        // Testing the download button in the field
        // We must avoid the browser to download the file effectively
        const prom = makeDeferred();
        const downloadOnClick = (ev) => {
            const target = ev.target;
            if (target.tagName === "A" && "download" in target.attributes) {
                ev.preventDefault();
                document.removeEventListener("click", downloadOnClick);
                prom.resolve();
            }
        };
        document.addEventListener("click", downloadOnClick);
        registerCleanup(() => document.removeEventListener("click", downloadOnClick));
        await click(target.querySelector(".fa-download"));
        await prom;

        await click(target.querySelector(".o_field_binary .o_clear_file_button"));

        assert.isNotVisible(
            target.querySelector(".o_field_binary input"),
            "the input should be hidden"
        );
        assert.containsOnce(
            target,
            ".o_field_binary .o_select_file_button",
            "there should be a button to upload the file"
        );
        assert.strictEqual(
            target.querySelector(".o_field_char input").value,
            "",
            "the filename field should be empty since we removed the file"
        );

        await clickSave(target);
        assert.containsNone(
            target,
            '.o_field_widget[name="document"] a > .fa-download',
            "the binary field should not render as a downloadable link since we removed the file"
        );
        assert.containsNone(
            target,
            "o_field_widget span",
            "the binary field should not display a filename in the link since we removed the file"
        );
    });

    QUnit.test("BinaryField is correctly rendered (isDirty)", async function (assert) {
        assert.expect(2);

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="document" filename="foo"/>
                    <field name="foo"/>
                </form>`,
            resId: 1,
        });
        // Simulate a file upload
        const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
        await editInput(target, ".o_field_binary .o_input_file", file);
        assert.containsNone(
            target,
            '.o_field_widget[name="document"] .fa-download',
            "the binary field should not be rendered as a downloadable since the record is dirty"
        );
        await clickSave(target);
        assert.containsOnce(
            target,
            '.o_field_widget[name="document"] .fa-download',
            "the binary field should render as a downloadable link since the record is not dirty"
        );
    });

    QUnit.test("file name field is not defined", async (assert) => {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: /* xml */ `
                <form>
                    <field name="document" filename="foo"/>
                </form>`,
            resId: 1,
        });

        assert.strictEqual(
            target.querySelector(".o_field_binary").textContent,
            "",
            "there should be no text since the name field is not in the view"
        );
        assert.isVisible(
            target,
            ".o_field_binary .o_form_uri fa-download",
            "download icon should be visible"
        );
    });

    QUnit.test(
        "binary fields input value is empty when clearing after uploading",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="document" filename="foo"/>
                        <field name="foo"/>
                    </form>`,
                resId: 1,
            });

            const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
            await editInput(target, ".o_field_binary .o_input_file", file);

            assert.ok(
                target.querySelector(".o_field_binary input[type=text]").hasAttribute("readonly")
            );
            assert.strictEqual(
                target.querySelector(".o_field_binary input[type=text]").value,
                "fake_file.txt",
                'displayed value should be changed to "fake_file.txt"'
            );
            assert.strictEqual(
                target.querySelector(".o_field_char input[type=text]").value,
                "fake_file.txt",
                'related value should be changed to "fake_file.txt"'
            );

            await click(target.querySelector(".o_clear_file_button"));

            assert.strictEqual(
                target.querySelector(".o_field_binary .o_input_file").value,
                "",
                "file input value should be empty"
            );
            assert.strictEqual(
                target.querySelector(".o_field_char input").value,
                "",
                "related value should be empty"
            );
        }
    );

    QUnit.test("BinaryField: option accepted_file_extensions", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="document" widget="binary" options="{'accepted_file_extensions': '.dat,.bin'}"/>
                </form>`,
        });
        assert.strictEqual(
            target.querySelector("input.o_input_file").getAttribute("accept"),
            ".dat,.bin",
            "the input should have the correct ``accept`` attribute"
        );
    });

    QUnit.test(
        "BinaryField that is readonly in create mode does not download",
        async function (assert) {
            async function download() {
                assert.step("We shouldn't be getting the file.");
            }
            const MockXHR = makeMockXHR("", download);

            patchWithCleanup(
                browser,
                {
                    XMLHttpRequest: MockXHR,
                },
                { pure: true }
            );

            serverData.models.partner.onchanges = {
                product_id: function (obj) {
                    obj.document = "onchange==\n";
                },
            };

            serverData.models.partner.fields.document.readonly = true;

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <field name="product_id"/>
                        <field name="document" filename="yooo"/>
                    </form>`,
                resId: 1,
            });

            await click(target, ".o_form_button_create");
            await click(target, ".o_field_many2one[name='product_id'] input");
            await click(
                target.querySelector(".o_field_many2one[name='product_id'] .dropdown-item")
            );

            assert.containsNone(
                target,
                '.o_field_widget[name="document"] a',
                "The link to download the binary should not be present"
            );
            assert.containsNone(
                target,
                '.o_field_widget[name="document"] a > .fa-download',
                "The download icon should not be present"
            );

            assert.verifySteps([], "We shouldn't have passed through steps");
        }
    );

    QUnit.test("Binary field in list view", async function (assert) {
        serverData.models.partner.records[0].document = BINARY_FILE;

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                    <tree>
                        <field name="document" filename="yooo"/>
                    </tree>`,
            resId: 1,
        });

        assert.strictEqual(
            target.querySelector(".o_data_row .o_data_cell").textContent,
            "93.43 Bytes"
        );
    });

    QUnit.test("Binary field for new record has no download button", async function (assert) {
        serverData.models.partner.fields.document.default = BINARY_FILE;
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="document" filename="foo"/>
                </form>
            `,
        });
        assert.containsNone(target, "button.fa-download");
    });

    QUnit.test("Binary filename doesn't exceed 255 bytes", async function (assert) {
        const LARGE_BINARY_FILE = BINARY_FILE.repeat(5);
        assert.ok((LARGE_BINARY_FILE.length / 4 * 3) > MAX_FILENAME_SIZE_BYTES,
            "The initial binary file should be larger than max bytes that can represent the filename");
        serverData.models.partner.fields.document.default = LARGE_BINARY_FILE;
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="document"/>
                </form>
            `,
        });
        assert.strictEqual(
            target.querySelector(".o_field_binary input[type=text]").value.length,
            toBase64Length(MAX_FILENAME_SIZE_BYTES),
            "The filename shouldn't exceed the maximum size in bytes in base64"
        );
    });

    QUnit.test("BinaryField filename is updated when using the pager", async function (assert) {
        serverData.models.partner.records.push(
            {
                id: 1,
                document: "abc",
                foo: "abc.txt",
            },
            {
                id: 2,
                document: "def",
                foo: "def.txt",
            }
        );
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <field name="document" filename="foo"/>
                    <field name="foo"/>
                </form>
            `,
            resIds: [1, 2],
            resId: 1,
        });

        assert.strictEqual(
            target.querySelector(".o_field_binary input[type=text]").value,
            "abc.txt",
            'displayed value should be "abc.txt"'
        );

        await click(target.querySelector(".o_pager_next"));

        assert.strictEqual(
            target.querySelector(".o_field_binary input[type=text]").value,
            "def.txt",
            'displayed value should be changed to "def.txt"'
        );
    });

    QUnit.test('isUploading state should be set to false after upload', async function(assert) {
        assert.expect(1);
        serverData.models.partner.onchanges = {
            document: function (obj) {
                if (obj.document) {
                    const error = new RPCError();
                    error.exceptionName = "odoo.exceptions.ValidationError";
                    throw error;
                }
            },
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="document"/>
                </form>`,
        });
        const file = new File(["test"], "fake_file.txt", { type: "text/plain" });
        await editInput(target, ".o_field_binary .o_input_file", file);
        assert.equal(
            target.querySelector(".o_select_file_button").innerText,
            "UPLOAD YOUR FILE",
            "displayed value should be upload your file"
        );
    });
});
