odoo.define('mrp.MrpDocumentsKanbanController', function (require) {
"use strict";

const core = require('web.core');
const DocumentViewer = require('mrp.MrpDocumentViewer');
const framework = require('web.framework');
const KanbanController = require('web.KanbanController');

const qweb = core.qweb;
const _t = core._t;

const MrpDocumentsKanbanController = KanbanController.extend({
    events: _.extend({}, KanbanController.prototype.events, {
        'click .o_mrp_documents_kanban_upload': '_onUpload',
    }),
    custom_events: _.extend({}, KanbanController.prototype.custom_events, {
        kanban_image_clicked: '_onKanbanPreview',
        upload_file: '_onUploadFile',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {jQueryElement} $node
     */
    renderButtons($node) {
        this.$buttons = $(qweb.render('MrpDocumentsKanbanView.buttons'));
        this.$buttons.appendTo($node);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * used to use a mocked version of XHR in the tests.
     *
     * @private
     * @returns {XMLHttpRequest}
     */
    _createXHR() {
        return new window.XMLHttpRequest();
    },
    /**
     * Prepares and upload files.
     *
     * @private
     * @param {Object[]} files
     * @returns {Promise}
     */
    _processFiles(files) {
        const data = new FormData();

        data.append('csrf_token', core.csrf_token);
        for (const file of files) {
            data.append('ufile', file);
            data.append('default_res_id', this.initialState.context.default_res_id);
            data.append('default_res_model', this.initialState.context.default_res_model);
        }
        const prom = new Promise(resolve => {
            framework.blockUI();
            const xhr = this._createXHR();
            xhr.open('POST', '/mrp/upload_attachment');
            xhr.onload = async () => {
                resolve();
                const result = JSON.parse(xhr.response);
                if (result.error) {
                    this.do_notify(_t("Error"), result.error, true);
                }
                await this.reload();
            };
            xhr.onerror = async () => {
                resolve();
                this.do_notify(xhr.status, _.str.sprintf(_t('message: %s'), xhr.reponseText), true);
                await this.reload();
            };
            xhr.onloadend = () => {
                framework.unblockUI();
            };
            xhr.send(data);
        });
        return prom;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     * @param {integer} ev.data.recordID
     * @param {Array<Object>} ev.data.recordList
     */
    _onKanbanPreview(ev) {
        const documents = ev.data.recordList;
        const documentID = ev.data.recordID;
        const documentViewer = new DocumentViewer(this, documents, documentID);
        documentViewer.appendTo(this.$('.o_mrp_documents_kanban_view'));
    },
    /**
     * @private
     */
    _onUpload() {
        const self = this;
        const $uploadInput = $('<input>', {type: 'file', name: 'files[]', multiple: 'multiple'});
        const always = function () {
            $uploadInput.remove();
        };
        $uploadInput.on('change', function (ev) {
            self._processFiles(ev.target.files).then(always).guardedCatch(always);
        });
        $uploadInput.click();
    },
    /**
     * specially created to call _processFiles method from tests
     * @private
     * @param {OdooEvent} ev
     */
    _onUploadFile(ev) {
        this._processFiles(ev.data.files);
    },
});

return MrpDocumentsKanbanController;

});
