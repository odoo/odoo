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
            if (!attachent_ids.length) {
                return self.do_notify(_t("Error"), _t("An error occurred during the upload"));
            }
            return this._rpc({
                model: 'account.invoice.import.wizard',
                method: 'create_invoices',
                args: ["", attachent_ids],
                context: this.initialState.context,
            }).then(function(result) {
                self.do_action(result);
            });
        },

        _onUpload: function (event) {
            var self = this;
            if (!this.initialState.context.journal_type) {
                this.initialState.context.journal_type = event.currentTarget.attributes['journal_type'].value;
            }
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
    });

    var DashboardKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: DashboardKanbanController,
        }),
    });

    viewRegistry.add('account_dashboard_kanban', DashboardKanbanView);
});
