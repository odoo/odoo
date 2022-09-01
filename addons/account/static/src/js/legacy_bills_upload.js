odoo.define('account.upload.document', function (require) {
"use strict";

    var core = require('web.core');
    var qweb = core.qweb;
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');

    var UploadDocumentMixin = {
        events: {
            'click .o_button_upload_document': '_onUpload',
            'change .o_account_document_upload .o_form_binary_form': '_onAddAttachment',
            'drop .o_drop_area': '_onDrop',
            'dragenter .o_content': '_highlight',
            'dragleave .o_drop_area': '_unhighlight',
            'dragover .o_drop_area': '_clear',
        },

        start: async function () {
            // define a unique uploadId and a callback method
            this.fileUploadID = _.uniqueId('account_bill_file_upload');
            $(window).on(this.fileUploadID, this._onFileUploaded.bind(this));
            let result = await this._super.apply(this, arguments);
            await this.$(this._dropZone).prepend($(qweb.render('account.DocumentDropZone')));
            return result;
        },

        reload: async function () {
            let result = await this._super.apply(this, arguments);
            await this.$(this._dropZone).prepend($(qweb.render('account.DocumentDropZone')));
            return result;
        },

        _onAddAttachment: function (ev) {
            // Auto submit form once we've selected an attachment
            var $input = $(ev.currentTarget).find('input.o_input_file');
            if ($input.val() !== '') {
                var $binaryForm = this.$('.o_account_document_upload form.o_form_binary_form');
                $binaryForm.submit();
            }
        },

        _onFileUploaded: function () {
            // Callback once attachment have been created, create a document with attachment ids
            var self = this;
            var attachments = Array.prototype.slice.call(arguments, 1);
            // Get id from result
            var attachent_ids = attachments.reduce(function(filtered, record) {
                if (record.id) {
                    filtered.push(record.id);
                }
                return filtered;
            }, []);
            return this._rpc({
                model: 'account.journal',
                method: 'create_document_from_attachment',
                args: ["", attachent_ids],
                context: this.initialState.context,
            }).then(function(result) {
                self.do_action(result);
            }).catch(function () {
                // Reset the file input, allowing to select again the same file if needed
                self.$('.o_account_document_upload .o_input_file').val('');
            });
        },

        _createForm: function() {
            // If hidden upload form don't exists, create it
            var $formContainer = this.$('.o_content').find('.o_account_document_upload');
            if (!$formContainer.length) {
                $formContainer = $(qweb.render('account.DocumentsHiddenUploadForm', {widget: this}));
                $formContainer.appendTo(this.$('.o_content'));
            }
        },

        _onUpload: function (ev) {
            this._createForm();
            // Trigger the input to select a file
            this.$('.o_account_document_upload .o_input_file').click();
        },

        _highlight: function(ev) {
            $('.o_drop_area').show();
        },

        _unhighlight: function(ev) {
            $('.o_drop_area').hide();
        },

        _clear: function(ev) {
            ev.preventDefault();
        },

        _onDrop: function (ev) {
            ev.preventDefault();
            this._createForm();
            if (ev.originalEvent.dataTransfer.files.length) {
                this.$('.o_account_document_upload .o_input_file')[0].files = ev.originalEvent.dataTransfer.files;
                this.$('.o_form_binary_form')[0].submit();
            }
            this._unhighlight(ev);
        },
    }

    var DocumentsListView = ListView.extend({
        config: Object.assign({}, ListView.prototype.config, {
            Controller: ListController.extend({_dropZone: '.o_content'}, UploadDocumentMixin, {
                buttons_template: 'DocumentsListView.buttons',
                events: Object.assign({}, ListController.prototype.events, UploadDocumentMixin.events),
            }),
        }),
    });

    var DocumentsKanbanView = KanbanView.extend({
        config: Object.assign({}, KanbanView.prototype.config, {
            Controller: KanbanController.extend({_dropZone: '.o_content'}, UploadDocumentMixin, {
                buttons_template: 'DocumentsKanbanView.buttons',
                events: Object.assign({}, KanbanController.prototype.events, UploadDocumentMixin.events),
            }),
        }),
    });

    var DashboardKanbanController = KanbanController.extend({_dropZone: '.o_kanban_record'}, UploadDocumentMixin, {
        events: Object.assign({}, KanbanController.prototype.events, UploadDocumentMixin.events),

        _setJournalContext: function(ev) {
            var kanbanRecord = $(ev.currentTarget).closest('.o_kanban_record').data('record');
            this.initialState.context['default_journal_id'] = kanbanRecord.id;
            let journal_type = kanbanRecord.state.data.type;
            if (journal_type == 'sale') {
                this.initialState.context['default_move_type'] = 'out_invoice';
            } else if (journal_type == 'purchase') {
                this.initialState.context['default_move_type'] = 'in_invoice';
            }
        },

        _onUpload: function (ev) {
            this._setJournalContext(ev);
            UploadDocumentMixin._onUpload.apply(this, arguments);
        },

        _onDrop: function (ev) {
            this._setJournalContext(ev);
            UploadDocumentMixin._onDrop.apply(this, arguments);
        },
    });

    var DashboardKanbanView = KanbanView.extend({
        config: Object.assign({}, KanbanView.prototype.config, {
            Controller: DashboardKanbanController,
        }),
    });

    viewRegistry.add('account_tree', DocumentsListView);
    viewRegistry.add('account_documents_kanban', DocumentsKanbanView);
    viewRegistry.add('account_dashboard_kanban', DashboardKanbanView);
});
