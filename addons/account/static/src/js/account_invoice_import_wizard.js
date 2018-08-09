odoo.define("account_invoice_import_wizard.attachments", function (require) {
"use strict";

var relational_fields = require("web.relational_fields");
var FieldMany2ManyBinaryMultiFiles = relational_fields.FieldMany2ManyBinaryMultiFiles;
var field_registry = require("web.field_registry");
var field_utils = require('web.field_utils');
var session = require('web.session');

var core = require("web.core");
var qweb = core.qweb;

var AccountInvoiceImportWizardWidget = FieldMany2ManyBinaryMultiFiles.extend({

    // @override
    init: function () {
        this._super.apply(this, arguments);
        this.xmlMetadata = {};
    },
    // @override
    _render: function(){
        this._generatedMetadata();
        this.$('.oe_placeholder_files, .oe_attachments')
            .replaceWith($(qweb.render('account_invoice_import_widget_view', {
                widget: this,
                show_table: Object.keys(this.value.data).length + Object.keys(this.uploadingFiles).length > 0,
            })));
        this.$('.oe_fileupload').show();
    },
});

field_registry.add("account_invoice_import_wizard_widget", ImportXMLAttachmentsWidget);

});