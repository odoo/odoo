/** @odoo-module **/

import { triggerEvent, nextTick } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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
        assert.expect(4);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: "<form>" + '<field name="document" widget="pdf_viewer"/>' + "</form>",
        });

        assert.hasClass(form.el.querySelector(".o_field_widget"), "o_field_pdf_viewer");
        assert.containsOnce(
            form,
            ".o_select_file_button:not(.o_hidden)",
            "there should be a visible 'Upload' button"
        );
        assert.containsNone(form, ".o_pdfview_iframe", "there should be no iframe");
        assert.containsOnce(form, 'input[type="file"]', "there should be one input");
    });

    QUnit.test("PdfViewerField: basic rendering", async function (assert) {
        assert.expect(4);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: "<form>" + '<field name="document" widget="pdf_viewer"/>' + "</form>",
            mockRPC: function (route) {
                if (route.indexOf("/web/static/lib/pdfjs/web/viewer.html") !== -1) {
                    return Promise.resolve();
                }
            },
        });
        assert.hasClass(form.el.querySelector(".o_field_widget"), "o_field_pdf_viewer");
        assert.containsNone(form, ".o_select_file_button", "there should be no 'Upload' button");
        assert.containsOnce(
            form,
            ".o_field_widget iframe.o_pdfview_iframe",
            "there should be an iframe"
        );
        const iframeFile = form.el
            .querySelector(".o_field_widget iframe.o_pdfview_iframe")
            .src.split("%2Fweb%2Fcontent")[1];
        assert.strictEqual(
            iframeFile,
            "%3Fmodel%3Dpartner%26id%3D1%26field%3Ddocument#page=1",
            "the src attribute should be correctly set on the iframe"
        );
    });

    QUnit.test("PdfViewerField: upload rendering", async function (assert) {
        assert.expect(3);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: "<form>" + '<field name="document" widget="pdf_viewer"/>' + "</form>",
        });

        assert.containsNone(form, ".o_pdfview_iframe", "there is no PDF Viewer");

        // Set and trigger the change of a pdf file for the input
        const fileInput = form.el.querySelector('input[type="file"]');
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(new File(["test"], "test.pdf", { type: "application/pdf" }));
        fileInput.files = dataTransfer.files;
        await triggerEvent(fileInput, null, "change");

        await nextTick();

        assert.containsOnce(form, ".o_pdfview_iframe", "there is a PDF Viewer");
        const iframeFile = form.el
            .querySelector(".o_field_widget iframe.o_pdfview_iframe")
            .src.split("?file=")[1];
        assert.ok(/^blob%3/.test(iframeFile), "the file starts with 'blob:'");
    });
});
