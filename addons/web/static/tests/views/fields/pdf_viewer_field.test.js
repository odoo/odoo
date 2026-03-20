import {
    clickSave,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { test, expect } from "@odoo/hoot";
import { click, setInputFiles, queryOne, waitFor } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";

const getIframeSrc = () => queryOne(".o_field_widget iframe.o_pdfview_iframe").dataset.src;

const getIframeProtocol = () => getIframeSrc().match(/\?file=(\w+)%3A/)[1];

const getIframeViewerParams = () =>
    decodeURIComponent(getIframeSrc().match(/%2Fweb%2Fcontent%3F(.*)#page/)[1]);

class Partner extends models.Model {
    document = fields.Binary({ string: "Binary" });
    _records = [
        {
            document: "coucou==\n",
        },
    ];
}

defineModels([Partner]);

test("PdfViewerField without data", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="document" widget="pdf_viewer"/></form>',
    });
    expect(".o_field_widget").toHaveClass("o_field_pdf_viewer");
    expect(".o_select_file_button:not(.o_hidden)").toHaveCount(1);
    expect(".o_pdfview_iframe").toHaveCount(0);
    expect(`input[type="file"]`).toHaveCount(1);
});

test("PdfViewerField: basic rendering", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: '<form><field name="document" widget="pdf_viewer"/></form>',
    });

    expect(".o_field_widget").toHaveClass("o_field_pdf_viewer");
    expect(".o_select_file_button").toHaveCount(1);
    expect(".o_field_widget iframe.o_pdfview_iframe").toHaveCount(1);
    expect(getIframeProtocol()).toBe("https");
    expect(getIframeViewerParams()).toBe("model=partner&field=document&id=1");
});

test("PdfViewerField: upload rendering", async () => {
    expect.assertions(4);

    onRpc("web_save", ({ args }) => {
        expect(args[1]).toEqual({ document: btoa("test") });
    });

    await mountView({
        type: "form",
        resModel: "partner",
        arch: '<form><field name="document" widget="pdf_viewer"/></form>',
    });

    expect("iframe.o_pdfview_iframe").toHaveCount(0);
    const file = new File(["test"], "test.pdf", { type: "application/pdf" });
    await click(".o_field_pdf_viewer input[type=file]");
    await setInputFiles(file);
    await waitFor("iframe.o_pdfview_iframe");
    expect(getIframeProtocol()).toBe("blob");
    await clickSave();
    expect(getIframeProtocol()).toBe("blob");
});

test("PdfViewerField: upload file and download it", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: '<form><field name="document" widget="pdf_viewer"/></form>',
    });
    mockService("action", {
        doAction({ type }) {
            expect.step(type);
            return super.doAction(...arguments);
        },
    });
    patchWithCleanup(browser, {
        open: (_url, type) => {
            expect.step(`browser_open:${type}`);
        },
    });
    expect("iframe.o_pdfview_iframe").toHaveCount(1);
    const file = new File(["test"], "test.pdf", { type: "application/pdf" });
    await click(".o_field_pdf_viewer input[type=file]");
    await setInputFiles(file);
    await waitFor("iframe.o_pdfview_iframe");
    await clickSave();
    await click(".fa-download");
    expect.verifySteps(["ir.actions.act_url", "browser_open:_blank"]);
});
