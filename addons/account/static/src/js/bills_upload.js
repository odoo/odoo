odoo.define('account.upload.bill.mixin', function (require) {
"use strict";

    var core = require('web.core');
    var _t = core._t;

    var qweb = core.qweb;

    var UploadBillMixin = {

        start: function () {
            // define a unique uploadId and a callback method
            this.fileUploadID = _.uniqueId('account_bill_file_upload');
            $(window).on(this.fileUploadID, this._onFileUploaded.bind(this));
            return this._super.apply(this, arguments);
        },

        _onAddAttachment: function (ev) {
            // Auto submit form once we've selected an attachment
            var $input = $(ev.currentTarget).find('input.o_input_file');
            if ($input.val() !== '') {
                var $binaryForm = this.$('.o_vendor_bill_upload form.o_form_binary_form');
                $binaryForm.submit();
            }
        },

        _onFileUploaded: function () {
            // Callback once attachment have been created, create a bill with attachment ids
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
                method: 'create_invoice_from_attachment',
                args: ["", attachent_ids],
                context: this.initialState.context,
            }).then(function(result) {
                self.do_action(result);
            }).catch(function () {
                // Reset the file input, allowing to select again the same file if needed
                self.$('.o_vendor_bill_upload .o_input_file').val('');
            });
        },

        _onUpload: function (event) {
            var self = this;
            // If hidden upload form don't exists, create it
            var $formContainer = this.$('.o_content').find('.o_vendor_bill_upload');
            if (!$formContainer.length) {
                $formContainer = $(qweb.render('account.BillsHiddenUploadForm', {widget: this}));
                $formContainer.appendTo(this.$('.o_content'));
            }
            // Trigger the input to select a file
            this.$('.o_vendor_bill_upload .o_input_file').click();
        },
    }
    return UploadBillMixin;
});


odoo.define('account.bills.tree', function (require) {
"use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var UploadBillMixin = require('account.upload.bill.mixin');
    var viewRegistry = require('web.view_registry');

    var BillsListController = ListController.extend(UploadBillMixin, {
        buttons_template: 'BillsListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_upload_bill': '_onUpload',
            'change .o_vendor_bill_upload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    var BillsListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: BillsListController,
        }),
    });

    viewRegistry.add('account_tree', BillsListView);
});

odoo.define('account.bills.kanban', function (require) {
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var UploadBillMixin = require('account.upload.bill.mixin');
    var viewRegistry = require('web.view_registry');

    var BillsKanbanController = KanbanController.extend(UploadBillMixin, {
        buttons_template: 'BillsKanbanView.buttons',
        events: _.extend({}, KanbanController.prototype.events, {
            'click .o_button_upload_bill': '_onUpload',
            'change .o_vendor_bill_upload .o_form_binary_form': '_onAddAttachment',
        }),
    });

    var BillsKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: BillsKanbanController,
        }),
    });

    viewRegistry.add('account_bills_kanban', BillsKanbanView);
});

odoo.define('account.dashboard.kanban', function (require) {
"use strict";
    var core = require('web.core');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var UploadBillMixin = require('account.upload.bill.mixin');
    var viewRegistry = require('web.view_registry');

    var DashboardKanbanController = KanbanController.extend(UploadBillMixin, {
        events: _.extend({}, KanbanController.prototype.events, {
            'click .o_button_upload_bill': '_onUpload',
            'change .o_vendor_bill_upload .o_form_binary_form': '_onAddAttachment',
        }),
        /**
         * We override _onUpload (from the upload bill mixin) to pass default_journal_id
         * and default_move_type in context.
         *
         * @override
         */
        _onUpload: function (event) {
            var kanbanRecord = $(event.currentTarget).closest('.o_kanban_record').data('record');
            this.initialState.context['default_journal_id'] = kanbanRecord.id;
            if ($(event.currentTarget).attr('journal_type') == 'sale') {
                this.initialState.context['default_move_type'] = 'out_invoice'
            } else if ($(event.currentTarget).attr('journal_type') == 'purchase') {
                this.initialState.context['default_move_type'] = 'in_invoice'
            }
            UploadBillMixin._onUpload.apply(this, arguments);
        }
    });

    var DashboardKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: DashboardKanbanController,
        }),
    });

    viewRegistry.add('account_dashboard_kanban', DashboardKanbanView);
});
