/** @odoo-module **/

import { FileSelectorControlPanel } from '@web_editor/components/media_dialog/file_selector';
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { HtmlField } from '@web_editor/js/backend/html_field';
import {registry} from '@web/core/registry';
import testUtils from '@web/../tests/legacy/helpers/test_utils';
import { uploadService } from '@web_editor/components/upload_progress_toast/upload_service';
import { unsplashService } from '@web_unsplash/services/unsplash_service';
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import weTestUtils from '@web_editor/../tests/test_utils';
import {Wysiwyg} from '@web_editor/js/wysiwyg/wysiwyg';
import { useEffect } from "@odoo/owl";

QUnit.module('field html file upload', {
    beforeEach: function () {
        this.data = weTestUtils.wysiwygData({
            'mail.compose.message': {
                fields: {
                    display_name: {
                        string: "Displayed name",
                        type: "char"
                    },
                    body: {
                        string: "Message Body inline (to send)",
                        type: "html"
                    },
                    attachment_ids: {
                        string: "Attachments",
                        type: "many2many",
                        relation: "ir.attachment",
                    }
                },
                records: [{
                    id: 1,
                    display_name: "Some Composer",
                    body: "Hello",
                    attachment_ids: [],
                }],
            },
        });
    },
}, function () {
    QUnit.test('media dialog: upload', async function (assert) {
        assert.expect(4);
        const onAttachmentChangeTriggered = testUtils.makeTestPromise();
        patchWithCleanup(HtmlField.prototype, {
            _onAttachmentChange(event) {
                super._onAttachmentChange(event);
                onAttachmentChangeTriggered.resolve(true);
            }
        });
        const defFileSelector = testUtils.makeTestPromise();
        const onChangeTriggered = testUtils.makeTestPromise();
        patchWithCleanup(FileSelectorControlPanel.prototype, {
            setup() {
                super.setup();
                useEffect(() => {
                    defFileSelector.resolve(true);
                }, () => []);
            },
            async onChangeFileInput() {
                super.onChangeFileInput();
                onChangeTriggered.resolve(true);
            }
        });
        patchWithCleanup(Wysiwyg.prototype, {
            async _getColorpickerTemplate() {
                return weTestUtils.COLOR_PICKER_TEMPLATE;
            }
        });

        // create and load form view
        const serviceRegistry = registry.category("services");
        serviceRegistry.add("upload", uploadService);
        serviceRegistry.add("unsplash", unsplashService);
        const serverData = {
            models: this.data,
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "test",
                res_model: "mail.compose.message",
                type: "ir.actions.act_window",
                views: [[false, "form"]],
            },
        };
        serverData.views = {
            "mail.compose.message,false,search": "<search></search>",
            "mail.compose.message,false,form": `
                <form>
                    <field name="body" type="html"/>
                    <field name="attachment_ids" widget="many2many_binary"/>
                </form>`,
        };
        const mockRPC = (route, args) => {
            if (route === "/web_editor/attachment/add_data") {
                return Promise.resolve({"id": 5, "name": "test.jpg", "description": false, "mimetype": "image/jpeg", "checksum": "7951a43bbfb08fd742224ada280913d1897b89ab",
                                        "url": false, "type": "binary", "res_id": 1, "res_model": "note.note", "public": false, "access_token": false,
                                        "image_src": "/web/image/1-a0e63e61/test.jpg", "image_width": 1, "image_height": 1, "original_id": false
                                        });
            }
            else if (route === "/web/dataset/call_kw/ir.attachment/generate_access_token") {
                return Promise.resolve(["129a52e1-6bf2-470a-830e-8e368b022e13"]);
            }
        };
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);
        //trigger wysiwyg mediadialog
        const fixture = getFixture();
        const formField = fixture.querySelector('.o_field_html[name="body"]');
        const textInput = formField.querySelector('.note-editable p');
        textInput.innerText = "test";
        const pText = $(textInput).contents()[0];
        Wysiwyg.setRange(pText, 1, pText, 2);
        await new Promise((resolve) => setTimeout(resolve)); //ensure fully set up
        const wysiwyg = $(textInput.parentElement).data('wysiwyg');
        wysiwyg.openMediaDialog();
        assert.ok(await Promise.race([defFileSelector, new Promise((res, _) => setTimeout(() => res(false), 400))]), "File Selector did not mount");
        // upload test
        const fileInputs = document.querySelectorAll(".o_select_media_dialog input.d-none.o_file_input");
        const fileB64 = '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q==';
        const fileBytes = new Uint8Array(atob(fileB64).split('').map(char => char.charCodeAt(0)));
        // redefine 'files' so we can put mock data in through js
        fileInputs.forEach((input) => Object.defineProperty(input, 'files', {
            value: [new File(fileBytes, "test.jpg", { type: 'image/jpeg' })],
        }));
        fileInputs.forEach(input => {
            input.dispatchEvent(new Event('change', {}));
        });

        assert.ok(await Promise.race([onChangeTriggered, new Promise((res, _) => setTimeout(() => res(false), 400))]),
                  "File change event was not triggered");
        assert.ok(await Promise.race([onAttachmentChangeTriggered, new Promise((res, _) => setTimeout(() => res(false), 400))]),
                  "_onAttachmentChange was not called with the new attachment, necessary for unsused upload cleanup on backend");

        // wait to check that dom is properly updated
        await new Promise((res, _) => setTimeout(() => res(false), 400));
        assert.ok(fixture.querySelector('.o_attachment[title="test.jpg"]'));
    });
});
