/** @odoo-module **/

import MrpDocumentsKanbanView from '@mrp/js/mrp_document_kanban_view';
import MrpDocumentsKanbanController from '@mrp/js/mrp_documents_kanban_controller';
import testUtils from 'web.test_utils';

const createView = testUtils.createView;

QUnit.module('Views', {}, function () {

QUnit.module('MrpDocumentsKanbanView', {
    beforeEach: function () {
        this.ORIGINAL_CREATE_XHR = MrpDocumentsKanbanController.prototype._createXHR;
        this.patchDocumentXHR = (mockedXHRs, customSend) => {
            MrpDocumentsKanbanController.prototype._createXhr = () => {
                const xhr = {
                    upload: new window.EventTarget(),
                    open() { },
                    send(data) { customSend && customSend(data); },
                };
                mockedXHRs.push(xhr);
                return xhr;
            };
        };
        this.data = {
            'mrp.document': {
                fields: {
                    name: {string: "Name", type: 'char', default: ' '},
                    priority: {string: 'priority', type: 'selection',
                        selection: [['0', 'Normal'], ['1', 'Low'], ['2', 'High'], ['3', 'Very High']]},
                },
                records: [
                    {id: 1, name: 'test1', priority: 2},
                    {id: 4, name: 'test2', priority: 1},
                    {id: 3, name: 'test3', priority: 3},
                ],
            },
        };
    },
    afterEach() {
        MrpDocumentsKanbanController.prototype._createXHR = this.ORIGINAL_CREATE_XHR;
    },
}, function () {
    QUnit.test('MRP documents kanban basic rendering', async function (assert) {
        assert.expect(6);

        const kanban = await createView({
            View: MrpDocumentsKanbanView,
            model: 'mrp.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        assert.ok(kanban, "kanban is created");
        assert.ok(kanban.$buttons.find('.o_mrp_documents_kanban_upload'),
            "should have upload button in kanban buttons");
        assert.containsN(kanban, '.o_legacy_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3,
            "should have 3 records in the renderer");
        // check view layout
        assert.hasClass(kanban.$('.o_legacy_kanban_view'), 'o_mrp_documents_kanban_view',
            "should have classname 'o_mrp_documents_kanban_view'");
        // check control panel buttons
        assert.containsN(kanban, '.o_cp_buttons .btn-primary', 1,
            "should have only 1 primary button i.e. Upload button");
        assert.strictEqual(kanban.$('.o_cp_buttons .btn-primary:first').text().trim(), 'Upload',
            "should have a primary 'Upload' button");

        kanban.destroy();
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

        const kanban = await createView({
            View: MrpDocumentsKanbanView,
            model: 'mrp.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        kanban.trigger_up('upload_file', {files: [file1]});
        await testUtils.nextTick();
        assert.verifySteps(['xhrSend']);

        kanban.trigger_up('upload_file', {files: [file2, file3]});
        await testUtils.nextTick();
        assert.verifySteps(['xhrSend']);

        kanban.destroy();
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

        const kanban = await createView({
            View: MrpDocumentsKanbanView,
            model: 'mrp.document',
            data: this.data,
            arch: '<kanban><templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        kanban.trigger_up('upload_file', {files: [file1]});
        await testUtils.nextTick();
        assert.verifySteps(['xhrSend']);

        const progressEvent = new Event('progress', { bubbles: true });
        progressEvent.loaded = 250000000;
        progressEvent.total = 500000000;
        progressEvent.lengthComputable = true;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);
        assert.strictEqual(
            kanban.$('.o_file_upload_progress_text_left').text(),
            "Uploading... (50%)",
            "the current upload progress should be at 50%"
        );

        progressEvent.loaded = 350000000;
        mockedXHRs[0].upload.dispatchEvent(progressEvent);
        assert.strictEqual(
            kanban.$('.o_file_upload_progress_text_right').text(),
            "(350/500Mb)",
            "the current upload progress should be at (350/500Mb)"
        );

        kanban.destroy();
    });
});

});
