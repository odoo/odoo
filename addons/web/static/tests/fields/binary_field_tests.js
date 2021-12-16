/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { download } from "@web/core/network/download";
import { makeMockXHR } from "../helpers/mock_services";
import { click, makeDeferred, patchWithCleanup } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";
import { registerCleanup } from "../helpers/cleanup";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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
                    },
                    records: [
                        {
                            foo: "coucou.txt",
                            document: "coucou==\n",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BinaryField");

    QUnit.test("BinaryField is correctly rendered", async function (assert) {
        assert.expect(15);

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
        let MockXHR = makeMockXHR("", send);

        patchWithCleanup(
            browser,
            {
                XMLHttpRequest: MockXHR,
            },
            { pure: true }
        );

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                '<field name="document" filename="foo"/>' +
                '<field name="foo"/>' +
                "</form>",
            resId: 1,
        });
        assert.containsOnce(
            form,
            '.o_field_widget[name="document"] a > .fa-download',
            "the binary field should be rendered as a downloadable link in readonly"
        );
        assert.strictEqual(
            form.el.querySelector('.o_field_widget[name="document"] span').innerText.trim(),
            "coucou.txt",
            "the binary field should display the name of the file in the link"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_char").innerText,
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
        await click(form.el.querySelector('.o_field_widget[name="document"] a'));
        await prom;

        await click(form.el, ".o_form_button_edit");

        assert.containsNone(
            form,
            '.o_field_widget[name="document"] a > .fa-download',
            "the binary field should not be rendered as a downloadable link in edit"
        );
        assert.strictEqual(
            form.el.querySelector('.o_field_widget[name="document"] div.o_field_binary_file span')
                .innerText,
            "coucou.txt",
            "the binary field should display the file name in the input edit mode"
        );
        assert.containsOnce(
            form,
            ".o_field_binary_file .o_clear_file_button",
            "there shoud be a button to clear the file"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_char input").value,
            "coucou.txt",
            "the filename field should have the file name as value"
        );

        await click(form.el.querySelector(".o_field_binary_file .o_clear_file_button"));

        assert.isNotVisible(
            form.el.querySelector(".o_field_binary_file input"),
            "the input should be hidden"
        );
        assert.containsOnce(
            form,
            ".o_field_binary_file .o_select_file_button",
            "there shoud be a button to upload the file"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_char input").value,
            "",
            "the filename field should be empty since we removed the file"
        );

        await click(form.el, ".o_form_button_save");
        assert.containsNone(
            form,
            '.o_field_widget[name="document"] a > .fa-download',
            "the binary field should not render as a downloadable link since we removed the file"
        );
        assert.containsNone(
            form,
            "o_field_widget span",
            "the binary field should not display a filename in the link since we removed the file"
        );
    });

    QUnit.test("BinaryField: option accepted_file_extensions", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `<form string="Partners">
                      <field name="document" widget="binary" options="{'accepted_file_extensions': '.dat,.bin'}"/>
                   </form>`,
        });
        assert.strictEqual(
            form.el.querySelector("input.o_input_file").getAttribute("accept"),
            ".dat,.bin",
            "the input should have the correct ``accept`` attribute"
        );
    });

    QUnit.skip(
        "BinaryField that is readonly in create mode does not download",
        async function (assert) {
            assert.expect(4);

            // save the session function
            var oldGetFile = download;
            download = function (option) {
                assert.step("We shouldn't be getting the file.");
                return oldGetFile.bind(download)(option);
            };

            serverData.models.partner.onchanges = {
                product_id: function (obj) {
                    obj.document = "onchange==\n";
                },
            };

            serverData.models.partner.fields.document.readonly = true;

            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    '<form string="Partners">' +
                    '<field name="product_id"/>' +
                    '<field name="document" filename="\'yooo\'"/>' +
                    "</form>",
                resId: 1,
            });

            await click(form.el, ".o_form_button_create");
            await testUtils.fields.many2one.clickOpenDropdown("product_id");
            await testUtils.fields.many2one.clickHighlightedItem("product_id");

            assert.containsOnce(
                form,
                '.o_field_widget[name="document"] a',
                "The link to download the binary should be present"
            );
            assert.containsNone(
                form,
                '.o_field_widget[name="document"] a > .fa-download',
                "The download icon should not be present"
            );

            var link = form.el.querySelector('.o_field_widget[name="document"] a');
            assert.ok(link.is(":hidden"), "the link element should not be visible");

            assert.verifySteps([]); // We shouldn't have passed through steps

            download = oldGetFile;
        }
    );
});
