odoo.define('account_bank_statement_import.import', function (require) {
"use strict";

var core = require('web.core');
var BaseImport = require('base_import.import');

var _t = core._t;

BaseImport.DataImport.include({
    renderImportLink: function() {
        this._super();
        if (this.res_model == 'account.bank.statement') {
            this.$(".import-link").prop({"text": _t(" Import Template for Bank Statements"), "href": "/account_bank_statement_import/static/csv/account.bank.statement.csv"});
            this.$(".template-import").removeClass('d-none');
        }
    },   
});

});
