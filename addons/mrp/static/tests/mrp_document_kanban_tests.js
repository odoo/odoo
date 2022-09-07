/** @odoo-module **/

import testUtils from 'web.test_utils';
import { registry } from "@web/core/registry";
import {
    click,
    getFixture,
    nextTick,
} from '@web/../tests/helpers/utils';
import { setupViewRegistries } from "@web/../tests/views/helpers";
import {
    start,
    startServer,
} from '@mail/../tests/helpers/test_utils';

import { fileUploadService } from "@web/core/file_upload/file_upload_service";

import { addModelNamesToFetch } from '@bus/../tests/helpers/model_definitions_helpers';
addModelNamesToFetch([
    'mrp.document',
]);

const serviceRegistry = registry.category("services");

let target;
let pyEnv;

QUnit.module('Views', {}, function () {

QUnit.module('MrpDocumentsKanbanView', {
    beforeEach: async function () {
        serviceRegistry.add("file_upload", fileUploadService);
        this.ORIGINAL_CREATE_XHR = fileUploadService.createXhr;
        this.patchDocumentXHR = (mockedXHRs, customSend) => {
            fileUploadService.createXhr = () => {
                const xhr = {
                    upload: new window.EventTarget(),
                    open() { },
                    send(data) { customSend && customSend(data); },
                };
                mockedXHRs.push(xhr);
                return xhr;
            };
        };
        pyEnv = await startServer();
        const irAttachment = pyEnv['ir.attachment'].create({
            mimetype: 'image/png',
            name: 'test.png',
        })
        pyEnv['mrp.document'].create([
            {name: 'test1', priority: 2, ir_attachment_id: irAttachment},
            {name: 'test2', priority: 1},
            {name: 'test3', priority: 3},
        ]);
        target = getFixture();
        setupViewRegistries();
    },
    afterEach() {
        fileUploadService.createXhr = this.ORIGINAL_CREATE_XHR;
    },
}, function () {
    QUnit.test('MRP documents kanban basic rendering', async function (assert) {
        assert.expect(4);

        const views = {
            'mrp.document,false,kanban':
                `<kanban js_class="mrp_documents_kanban" create="false"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: 'mrp.document',
            views: [[false, 'kanban']],
        });

        assert.ok(target.querySelector('.o_mrp_documents_kanban_upload'),
            "should have upload button in kanban buttons");
        assert.containsN(target, '.o_kanban_renderer .o_kanban_record:not(.o_kanban_ghost)', 3,
            "should have 3 records in the renderer");
        // check control panel buttons
        assert.containsN(target, '.o_cp_buttons .btn-primary', 1,
            "should have only 1 primary button i.e. Upload button");
        assert.equal(target.querySelector(".o_cp_buttons .btn-primary").innerText.trim().toUpperCase(), 'UPLOAD',
            "should have a primary 'Upload' button");
    });

    QUnit.test('mrp: upload multiple files', async function (assert) {
        assert.expect(4);

        const file1 = await testUtils.file.createFile({
            name: 'text1.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });
        const file2 = await testUtils.file.createFile({
            name: 'text2.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });
        const file3 = await testUtils.file.createFile({
            name: 'text3.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs, data => assert.step('xhrSend'));

        const views = {
            'mrp.document,false,kanban':
                `<kanban js_class="mrp_documents_kanban" create="false"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: 'mrp.document',
            views: [[false, 'kanban']],
        });

        const fileInput = target.querySelector(".o_input_file");

        let dataTransfer = new DataTransfer();
        dataTransfer.items.add(file1);
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        assert.verifySteps(['xhrSend']);

        dataTransfer = new DataTransfer();
        dataTransfer.items.add(file2);
        dataTransfer.items.add(file3);
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        assert.verifySteps(['xhrSend']);
    });

    QUnit.test('mrp: upload progress bars', async function (assert) {
        assert.expect(4);

        const file1 = await testUtils.file.createFile({
            name: 'text1.txt',
            content: 'hello, world',
            contentType: 'text/plain',
        });

        const mockedXHRs = [];
        this.patchDocumentXHR(mockedXHRs, data => assert.step('xhrSend'));

        const views = {
            'mrp.document,false,kanban':
                `<kanban js_class="mrp_documents_kanban" create="false"><templates><t t-name="kanban-box">
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: 'mrp.document',
            views: [[false, 'kanban']],
        });

        const fileInput = target.querySelector(".o_input_file");

        let dataTransfer = new DataTransfer();
        dataTransfer.items.add(file1);
        fileInput.files = dataTransfer.files;
        fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        assert.verifySteps(['xhrSend']);

        const progressEvent = new Event('progress', { bubbles: true });
        progressEvent.loaded = 250000000;
        progressEvent.total = 500000000;
        progressEvent.lengthComputable = true;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);
        await nextTick();
        assert.strictEqual(
            target.querySelector('.o_file_upload_progress_text_left').innerText,
            "Uploading... (50%)",
            "the current upload progress should be at 50%"
        );
            
        progressEvent.loaded = 350000000;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);
        await nextTick();
        assert.strictEqual(
            target.querySelector('.o_file_upload_progress_text_right').innerText,
            "(350/500MB)",
            "the current upload progress should be at (350/500Mb)"
        );
    });

    QUnit.test("mrp: click on image opens attachment viewer", async function (assert) {
        assert.expect(4);

        const views = {
            'mrp.document,false,kanban':
                `<kanban js_class="mrp_documents_kanban" create="false"><templates><t t-name="kanban-box">
                    <div class="o_kanban_image" t-if="record.ir_attachment_id.raw_value">
                        <div class="o_kanban_previewer">
                            <field name="ir_attachment_id" invisible="1"/>
                            <img t-attf-src="/web/image/#{record.ir_attachment_id.raw_value}" width="100" height="100" alt="Document" class="o_attachment_image"/>
                        </div>
                    </div>
                    <div>
                        <field name="name"/>
                    </div>
                </t></templates></kanban>`
        };
        const { openView } = await start({
            serverData: { views },
        });
        await openView({
            res_model: 'mrp.document',
            views: [[false, 'kanban']],
        });

        assert.containsOnce(target, ".o_kanban_previewer");
        await click(target.querySelector(".o_kanban_previewer"));
        await nextTick();

        assert.containsOnce(target, '.o_AttachmentViewer',
            "should have a document preview");
        assert.containsOnce(target, '.o_AttachmentViewer_headerItemButtonClose',
            "should have a close button");

        await click(target, '.o_AttachmentViewer_headerItemButtonClose');
        assert.containsNone(target, '.o_AttachmentViewer',
            "should not have a document preview");
    });
});

});
