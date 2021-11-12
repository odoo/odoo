/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { registry } from "@web/core/registry";
import { makeFakeLocalizationService, makeFakeUserService } from "../helpers/mock_services";
import { click, makeDeferred, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
import {
    setupControlPanelFavoriteMenuRegistry,
    setupControlPanelServiceRegistry,
} from "../search/helpers";
import { makeView } from "../views/helpers";

const serviceRegistry = registry.category("services");

let serverData;

function hasGroup(group) {
    return group === "base.group_allow_export";
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        date: { string: "A date", type: "date", searchable: true },
                        datetime: { string: "A datetime", type: "datetime", searchable: true },
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        txt: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            searchable: true,
                        },
                        trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                            searchable: true,
                        },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            searchable: true,
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            searchable: true,
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                        document: { string: "Binary", type: "binary" },
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            date: "2017-02-03",
                            datetime: "2017-02-08 10:00:00",
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            p: [],
                            timmy: [],
                            trululu: 4,
                            selection: "blocked",
                            document: "coucou==\n",
                            hex_color: "#ff0000",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 0,
                            qux: 0,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            sequence: 4,
                            currency_id: 2,
                            selection: "normal",
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            foo: "abc",
                            sequence: 9,
                            int_field: false,
                            qux: false,
                            selection: "done",
                        },
                        { id: 3, bar: true, foo: "gnap", int_field: 80, qux: -3.89859 },
                        { id: 5, bar: false, foo: "blop", int_field: -4, qux: 9.1, currency_id: 1 },
                    ],
                    onchanges: {},
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
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
                        },
                        {
                            id: 2,
                            display_name: "€",
                            symbol: "€",
                            position: "after",
                        },
                    ],
                },
                "ir.translation": {
                    fields: {
                        lang: { type: "char" },
                        value: { type: "char" },
                        res_id: { type: "integer" },
                    },
                    records: [
                        {
                            id: 99,
                            res_id: 37,
                            value: "",
                            lang: "en_US",
                        },
                    ],
                },
            },
        };

        setupControlPanelFavoriteMenuRegistry();
        setupControlPanelServiceRegistry();
        serviceRegistry.add("dialog", dialogService);
        serviceRegistry.add("user", makeFakeUserService(hasGroup), { force: true });
    });

    QUnit.module("PdfViewerField");

    QUnit.skip("PdfViewerField without data", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: "<form>" + '<field name="document" widget="pdf_viewer"/>' + "</form>",
        });

        assert.hasClass(form.$(".o_field_widget"), "o_field_pdfviewer");
        assert.strictEqual(
            form.$(".o_select_file_button:not(.o_hidden)").length,
            1,
            "there should be a visible 'Upload' button"
        );
        assert.isNotVisible(
            form.$(".o_field_widget iframe.o_pdfview_iframe"),
            "there should be an invisible iframe"
        );
        assert.containsOnce(form, 'input[type="file"]', "there should be one input");

        form.destroy();
    });

    QUnit.skip("PdfViewerField: basic rendering", async function (assert) {
        assert.expect(4);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            res_id: 1,
            arch: "<form>" + '<field name="document" widget="pdf_viewer"/>' + "</form>",
            mockRPC: function (route) {
                if (route.indexOf("/web/static/lib/pdfjs/web/viewer.html") !== -1) {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.hasClass(form.$(".o_field_widget"), "o_field_pdfviewer");
        assert.strictEqual(
            form.$(".o_select_file_button:not(.o_hidden)").length,
            0,
            "there should not be a any visible 'Upload' button"
        );
        assert.isVisible(
            form.$(".o_field_widget iframe.o_pdfview_iframe"),
            "there should be an visible iframe"
        );
        assert.hasAttrValue(
            form.$(".o_field_widget iframe.o_pdfview_iframe"),
            "data-src",
            "/web/static/lib/pdfjs/web/viewer.html?file=%2Fweb%2Fcontent%3Fmodel%3Dpartner%26field%3Ddocument%26id%3D1#page=1",
            "the src attribute should be correctly set on the iframe"
        );

        form.destroy();
    });

    QUnit.skip("PdfViewerField: upload rendering", async function (assert) {
        assert.expect(6);

        testUtils.mock.patch(field_registry.map.pdf_viewer, {
            on_file_change: function (ev) {
                ev.target = { files: [new Blob()] };
                this._super.apply(this, arguments);
            },
            _getURI: function (fileURI) {
                this._super.apply(this, arguments);
                assert.step("_getURI");
                assert.ok(_.str.startsWith(fileURI, "blob:"));
                this.PDFViewerApplication = {
                    open: function (URI) {
                        assert.step("open");
                        assert.ok(_.str.startsWith(URI, "blob:"));
                    },
                };
                return "about:blank";
            },
        });

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: "<form>" + '<field name="document" widget="pdf_viewer"/>' + "</form>",
        });

        // first upload initialize iframe
        form.$('input[type="file"]').trigger("change");
        assert.verifySteps(["_getURI"]);
        // second upload call pdfjs method inside iframe
        form.$('input[type="file"]').trigger("change");
        assert.verifySteps(["open"]);

        testUtils.mock.unpatch(field_registry.map.pdf_viewer);
        form.destroy();
    });
});
