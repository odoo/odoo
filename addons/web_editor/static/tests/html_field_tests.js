/** @odoo-module **/

import { click, editInput, getFixture, makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { FormController } from '@web/views/form/form_controller';
import { HtmlField } from "@web_editor/js/backend/html_field";
import { parseHTML } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { onRendered } from "@odoo/owl";
import { wysiwygData } from "web_editor.test_utils";

// Legacy
import legacyEnv from 'web.commonEnv';

async function iframeReady(iframe) {
    const iframeLoadPromise = makeDeferred();
    iframe.addEventListener("load", function () {
        iframeLoadPromise.resolve();
    });
    if (!iframe.contentDocument.body) {
        await iframeLoadPromise;
    }
    await nextTick(); // ensure document is loaded
}

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


    QUnit.module('Sandboxed Preview');

    QUnit.test("complex html is automatically in sandboxed preview mode", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
            <!DOCTYPE HTML>
            <html xml:lang="en" lang="en">
                <head>

                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                    <meta name="format-detection" content="telephone=no"/>
                    <style type="text/css">
                        body {
                            color: blue;
                        }
                    </style>
                </head>
                <body>
                    Hello
                </body>
            </html>
            `,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });

        assert.containsOnce(target, '.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
    });

    QUnit.test("readonly sandboxed preview", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
            <!DOCTYPE HTML>
            <html xml:lang="en" lang="en">
                <head>

                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
                    <meta name="format-detection" content="telephone=no"/>
                    <style type="text/css">
                        body {
                            color: blue;
                        }
                    </style>
                </head>
                <body>
                    Hello
                </body>
            </html>`,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form string="Partner">
                    <field name="txt" widget="html" readonly="1" options="{'sandboxedPreview': true}"/>
                </form>`,
        });

        const readonlyIframe = target.querySelector('.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
        assert.ok(readonlyIframe);
        await iframeReady(readonlyIframe);
        assert.strictEqual(readonlyIframe.contentDocument.body.innerText, 'Hello');
        assert.strictEqual(readonlyIframe.contentWindow.getComputedStyle(readonlyIframe.contentDocument.body).color, 'rgb(0, 0, 255)');

        assert.containsN(target, '#codeview-btn-group > button', 0, 'Codeview toggle should not be possible in readonly mode.');
    });

    QUnit.test("sandboxed preview display and editing", async (assert) => {
        let codeViewState = false;
        const togglePromises = [makeDeferred(), makeDeferred()];
        let togglePromiseId = 0;
        const writePromise = makeDeferred();
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
        <html>
            <head>
                <style>
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
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <notebook>
                                <page string="Body" name="body">
                                    <field name="txt" widget="html" options="{'sandboxedPreview': true}"/>
                                </page>
                        </notebook>
                    </sheet>
                </form>`,
            mockRPC(route, args) {
                if (args.method === "write" && args.model === 'partner') {
                    assert.equal(args.args[1].txt, htmlDocumentTextTemplate('Hi', 'blue'));
                    writePromise.resolve();
                }
            }
        });

        // check original displayed content
        let iframe = target.querySelector('.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
        assert.ok(iframe, 'Should use a sanboxed iframe');
        await iframeReady(iframe);
        assert.strictEqual(iframe.contentDocument.body.textContent.trim(), 'Hello');
        assert.strictEqual(iframe.contentDocument.head.querySelector('style').textContent.trim().replace(/\s/g, ''),
                           'body{color:red;}', 'Head nodes should remain unaltered in the head');
        assert.equal(iframe.contentWindow.getComputedStyle(iframe.contentDocument.body).color, 'rgb(255, 0, 0)');
        // check button is there
        assert.containsOnce(target, '#codeview-btn-group > button');
        // edit in xml editor
        await click(target, '#codeview-btn-group > button');
        await togglePromises[togglePromiseId];
        togglePromiseId++;
        assert.containsOnce(target, '.o_field_html[name="txt"] textarea');
        await editInput(target, '.o_field_html[name="txt"] textarea', htmlDocumentTextTemplate('Hi', 'blue'));
        await click(target, '#codeview-btn-group > button');
        await togglePromises[togglePromiseId];
        // check dispayed content after edit
        iframe = target.querySelector('.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
        await iframeReady(iframe);
        assert.strictEqual(iframe.contentDocument.body.textContent.trim(), 'Hi');
        assert.strictEqual(iframe.contentDocument.head.querySelector('style').textContent.trim().replace(/\s/g, ''),
                          'body{color:blue;}', 'Head nodes should remain unaltered in the head');
        assert.equal(iframe.contentWindow.getComputedStyle(iframe.contentDocument.body).color, 'rgb(0, 0, 255)',
                     'Style should be applied inside the iframe.');

        const saveButton = target.querySelector('.o_form_button_save');
        assert.ok(saveButton);
        await click(saveButton);
        await writePromise;
    });


    QUnit.test("sanboxed preview mode not automatically enabled for regular values", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
                <body>
                    <p>Hello</p>
                </body>
            `,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
        });

        assert.containsN(target, '.o_field_html[name="txt"] iframe[sandbox]', 0);
        assert.containsN(target, '.o_field_html[name="txt"] textarea', 0);
    });

    QUnit.test("sandboxed preview option applies even for simple text", async (assert) => {
        serverData.models.partner.records = [{
            id: 1,
            txt: `
                Hello
            `,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html" options="{'sandboxedPreview': true}"/>
                </form>`,
        });

        assert.containsOnce(target, '.o_field_html[name="txt"] iframe[sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"]');
    });

    QUnit.module('Readonly mode');

    QUnit.test("Links should open on a new tab", async (assert) => {
        assert.expect(6);
        serverData.models.partner.records = [{
            id: 1,
            txt: `
                <body>
                    <a href="/contactus">Relative link</a>
                    <a href="${location.origin}/contactus">Internal link</a>
                    <a href="https://google.com">External link</a>
                </body>`,
        }];
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html" readonly="1"/>
                </form>`,
        });

        for (const link of target.querySelectorAll('a')) {
            assert.strictEqual(link.getAttribute('target'), '_blank');
            assert.strictEqual(link.getAttribute('rel'), 'noreferrer');
        }
    });

    QUnit.module('Save scenarios');

    QUnit.test("Ensure that urgentSave works even with modified image to save", async (assert) => {
        assert.expect(3);
        let formController;
        // Patch to get the controller instance.
        patchWithCleanup(FormController.prototype, {
            setup() {
                this._super(...arguments);
                formController = this;
            }
        });
        // Patch to get a promise to get the htmlField component instance when
        // the wysiwyg is instancied.
        const htmlFieldPromise = makeDeferred();
        patchWithCleanup(HtmlField.prototype, {
            async startWysiwyg() {
                await this._super(...arguments);
                await nextTick();
                htmlFieldPromise.resolve(this);
            }
        });
        // Add a partner record and ir.attachments model and record.
        serverData.models.partner.records.push({
            id: 1,
            txt: "<p class='test_target'><br></p>",
        });
        serverData.models["ir.attachment"] = wysiwygData({})["ir.attachment"];
        const imageRecord = serverData.models["ir.attachment"].records[0];
        // Method to get the html of a cropped image.
        // Use `data-src` instead of `src` when the SRC is an URL that would
        // make a call to the server.
        const getImageContainerHTML = (src, isModified) => {
            return `
                <p>
                    <img
                        class="img img-fluid o_we_custom_image o_we_image_cropped${isModified ? ' o_modified_image_to_save' : ''}"
                        data-original-id="${imageRecord.id}"
                        data-original-src="${imageRecord.image_src}"
                        data-mimetype="image/png"
                        data-width="50"
                        data-height="50"
                        data-scale-x="1"
                        data-scale-y="1"
                        data-aspect-ratio="0/0"
                        ${src.startsWith("/web") ? 'data-src="' : 'src="'}${src}"
                    >
                    <br>
                </p>
            `.replace(/(?:\s|(?:\r\n))+/g, ' ')
             .replace(/\s?(<|>)\s?/g, '$1');
        };
        // Promise to resolve when we want the response of the modify_image RPC.
        const modifyImagePromise = makeDeferred();
        let writeCount = 0;
        let modifyImageCount = 0;
        // Valid base64 encoded image in its transitory modified state.
        const imageContainerHTML = getImageContainerHTML(
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII",
            true
        );
        // New src URL to assign to the image when the modification is
        // "registered".
        const newImageSrc = "/web/image/1234/cropped_transparent.png";
        const mockRPC = async function (route, args) {
            if (
                route === '/web/dataset/call_kw/partner/write' &&
                args.model === 'partner'
            ) {
                if (writeCount === 0) {
                    // Save normal value without image.
                    assert.equal(args.args[1].txt, `<p class="test_target"><br></p>`);
                } else if (writeCount === 1) {
                    // Save image with unfinished modification changes.
                    assert.equal(args.args[1].txt, imageContainerHTML);
                } else if (writeCount === 2) {
                    // Save the modified image.
                    assert.equal(args.args[1].txt, getImageContainerHTML(newImageSrc, false));
                } else {
                    // Fail the test if too many write are called.
                    assert.ok(writeCount === 2, "Write should only be called 3 times during this test");
                }
                writeCount += 1;
            } else if (
                route === `/web_editor/modify_image/${imageRecord.id}`
            ) {
                if (modifyImageCount === 0) {
                    await modifyImagePromise;
                    return newImageSrc;
                } else {
                    // Fail the test if too many modify_image are called.
                    assert.ok(modifyImageCount === 0, "The image should only have been modified once during this test");
                }
                modifyImageCount += 1;
            }
        };
        // Add the ajax service (legacy), because wysiwyg RPCs use it.
        patchWithCleanup(legacyEnv, {
            services: {
                ...legacyEnv.services,
                ajax: {
                    rpc: mockRPC,
                },
            }
        });
        await makeView({
            type: "form",
            resId: 1,
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="txt" widget="html"/>
                </form>`,
            mockRPC: mockRPC,
        });
        // Let the htmlField be mounted and recover the Component instance.
        const htmlField = await htmlFieldPromise;
        const editor = htmlField.wysiwyg.odooEditor;

        // Simulate an urgent save without any image in the content.
        await formController.beforeUnload();
        await nextTick();

        // Replace the empty paragraph with a paragrah containing an unsaved
        // modified image
        editor.editable.classList.add("o_dirty");
        const imageContainerElement = parseHTML(imageContainerHTML).firstChild;
        let paragraph = editor.editable.querySelector(".test_target");
        editor.editable.replaceChild(imageContainerElement, paragraph);
        editor.historyStep();

        // Simulate an urgent save before the end of the RPC roundtrip for the
        // image.
        await formController.beforeUnload();
        await nextTick();

        // Resolve the image modification (simulate end of RPC roundtrip).
        modifyImagePromise.resolve();
        await modifyImagePromise;
        await nextTick();

        // Simulate the last urgent save, with the modified image.
        await formController.beforeUnload();
        await nextTick();
    });
});
