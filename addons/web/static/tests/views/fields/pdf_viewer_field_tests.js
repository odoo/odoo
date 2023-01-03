/** @odoo-module **/

import { clickSave, editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

const getIframe = () => target.querySelector(".o_field_widget iframe.o_pdfview_iframe");

const getIframeProtocol = () => getIframe().dataset.src.match(/\?file=(\w+)%3A/)[1];

const getIframeViewerParams = () =>
    decodeURIComponent(getIframe().dataset.src.match(/%2Fweb%2Fcontent%3F(.*)#page/)[1]);

QUnit.module("Fields", (hooks) => {
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
                            document: "coucou==\n",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("PdfViewerField");

    QUnit.test("PdfViewerField without data", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="document" widget="pdf_viewer"/></form>',
        });

        assert.hasClass(target.querySelector(".o_field_widget"), "o_field_pdf_viewer");
        assert.containsOnce(
            target,
            ".o_select_file_button:not(.o_hidden)",
            "there should be a visible 'Upload' button"
        );
        assert.containsNone(target, ".o_pdfview_iframe", "there should be no iframe");
        assert.containsOnce(target, 'input[type="file"]', "there should be one input");
    });

    QUnit.test("PdfViewerField: basic rendering", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: '<form><field name="document" widget="pdf_viewer"/></form>',
        });

        assert.hasClass(target.querySelector(".o_field_widget"), "o_field_pdf_viewer");
        assert.containsOnce(target, ".o_select_file_button", "there should be an 'Upload' button");
        assert.containsOnce(
            target,
            ".o_field_widget iframe.o_pdfview_iframe",
            "there should be an iframe"
        );
        assert.strictEqual(getIframeProtocol(), "http");
        assert.strictEqual(getIframeViewerParams(), "model=partner&field=document&id=1");
    });

    QUnit.test("PdfViewerField: upload rendering", async function (assert) {
        assert.expect(5);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="document" widget="pdf_viewer"/></form>',
            async mockRPC(_route, { method, args }) {
                if (method === "create") {
                    assert.deepEqual(args[0], { document: btoa("test") });
                }
            },
        });

        assert.containsNone(target, ".o_pdfview_iframe", "there is no PDF Viewer");

        const file = new File(["test"], "test.pdf", { type: "application/pdf" });
        await editInput(target, ".o_field_pdf_viewer input[type=file]", file);

        assert.containsOnce(target, ".o_pdfview_iframe", "there is a PDF Viewer");
        assert.strictEqual(getIframeProtocol(), "blob");

        await clickSave(target);

        assert.strictEqual(getIframeProtocol(), "blob");
    });
});
