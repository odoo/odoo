/** @odoo-module **/

import { click, editInput, getFixture, makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { HtmlField } from "@web_editor/js/backend/html_field";
import { onRendered } from "@odoo/owl";

QUnit.module("WebEditor.HtmlField", ({ beforeEach }) => {
    let serverData;
    let target;

    beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        txt: { string: "txt", type: "html", trim: true },
                    },
                    records: [],
                },
            },
        };
        target = getFixture();

        setupViewRegistries();

        // Explicitly removed by web_editor, we need to add it back
        registry.category("fields").add("html", HtmlField, { force: true });
    });

    /**
     * Check that documents with data in a <head> node are set to readonly
     * with a codeview option.
     */
    QUnit.test("html fields with complete HTML document", async (assert) => {
        assert.timeout(2000);
        assert.expect(12);
        let codeViewState = false;
        let togglePromiseId = 0;
        const togglePromises = [makeDeferred(), makeDeferred()];
        patchWithCleanup(HtmlField.prototype, {
            setup: function () {
                this._super(...arguments);
                onRendered(() => {
                    if (codeViewState !== this.state.showCodeView) {
                        togglePromises[togglePromiseId].resolve();
                    }
                    codeViewState = this.state.showCodeView;
                });
            },
        });
        const htmlDocumentTextTemplate = (text, color) => `
        <!DOCTYPE HTML>
        <html xml:lang="en" lang="en">
            <head>

                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                <meta name="format-detection" content="telephone=no"/>
                <style type="text/css">
                    body {
                        color: ${color};
                    }
                </style>
            </head>
            <body>
                ${text}
            </body>
        </html>
        `;
        serverData.models.partner.records = [{
            id: 1,
            txt: htmlDocumentTextTemplate('Hello', 'red'),
        }];
        const writePromise = makeDeferred();
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partner">
                    <sheet>
                        <notebook>
                                <page string="Body" name="body">
                                    <field name="txt" widget="html"/>
                                </page>
                        </notebook>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "write" && args.model === 'partner') {
                    assert.equal(args.args[1].txt, htmlDocumentTextTemplate('Hi', 'black'));
                    writePromise.resolve();
                }
            }
        });

        const fieldHtml = target.querySelector('.o_field_html');
        let readonlyNode = fieldHtml.querySelector('.o_readonly');
        assert.ok(readonlyNode);
        assert.equal(readonlyNode.innerText, 'Hello');
        assert.equal(window.getComputedStyle(readonlyNode).color, 'rgb(255, 0, 0)');

        const codeViewButton = fieldHtml.querySelector('.o_codeview_btn');
        assert.ok(codeViewButton);

        await click(codeViewButton);
        await togglePromises[togglePromiseId];
        const codeView = fieldHtml.querySelector('textarea.o_codeview');
        assert.ok(codeView);
        assert.equal(codeView.value, htmlDocumentTextTemplate('Hello', 'red'));

        await editInput(codeView, null, htmlDocumentTextTemplate('Hi', 'black'));

        assert.ok(codeViewButton);
        togglePromiseId++;
        await click(codeViewButton);
        await togglePromises[togglePromiseId];
        readonlyNode = fieldHtml.querySelector('.o_readonly');
        assert.ok(readonlyNode);
        assert.equal(readonlyNode.innerText, 'Hi');
        assert.equal(window.getComputedStyle(readonlyNode).color, 'rgb(0, 0, 0)');

        const saveButton = target.querySelector('.o_form_button_save');
        assert.ok(saveButton);
        await click(saveButton);
        await writePromise;
    });
});
