odoo.define('hr_expense.documents.upload.mixin', function (require) {
"use strict";

var core = require('web.core');
var _t = core._t;
var qweb = core.qweb;

/**
* Mixin for uploading single or multiple documents.
*/
var DocumentUploadMixin = {
    start: function () {
        // define a unique uploadId and a callback method
        this.fileUploadID = _.uniqueId('hr_expense_document_upload');
        $(window).on(this.fileUploadID, this._onFileUploaded.bind(this));
        return this._super.apply(this, arguments);
    },
    /**
     * @private
     */
    _onAddAttachment: function (ev) {
        // Auto submit form once we've selected an attachment
        var $input = $(ev.currentTarget).find('input.o_input_file');
        if ($input.val() !== '') {
            var $binaryForm = this.$('.o_expense_documents_upload form.o_form_binary_form');
            $binaryForm.submit();
        }
    },
    /**
     * @private
     */
    _onFileUploaded: function () {
        // Callback once attachment have been created, create an expense with attachment ids
        var self = this;
        var attachments = Array.prototype.slice.call(arguments, 1);
        // Get id from result
        var attachent_ids = attachments.reduce(function(filtered, record) {
            if (record.id) {
                filtered.push(record.id);
            } 
            return filtered;
        }, []);
        if (!attachent_ids.length) {
            return self.do_notify(_t("Error"), _t("An error occurred during the upload"));
        }
        return this._rpc({
            model: 'hr.expense',
            method: 'create_expense_from_attachments',
            args: ["", attachent_ids],
            context: this.initialState.context,
        }).then(function(result) {
            self.do_action(result);
        });
    },
    /**
     * @private
     * @param {Event} event
     */
    _onUpload: function (event) {
        var self = this;
        // If hidden upload form don't exists, create it
        var $formContainer = this.$('.o_content').find('.o_expense_documents_upload');
        if (!$formContainer.length) {
            $formContainer = $(qweb.render('hr.expense.DocumentsHiddenUploadForm', {widget: this}));
            $formContainer.appendTo(this.$('.o_content'));
        }
        // Trigger the input to select a file
        this.$('.o_expense_documents_upload .o_input_file').click();
    },
};

return DocumentUploadMixin;

});
