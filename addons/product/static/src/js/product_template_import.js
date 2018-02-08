odoo.define('product_template_import.import', function (require) {
"use strict";

var core = require('web.core');
var BaseImport = require('base_import.import');

var _t = core._t;

BaseImport.DataImport.include({
    renderImportLink: function() {
        this._super();
        if (this.res_model == 'product.template') {
            this.$(".import-link").prop({"text": _t(" Import Template for Products"), "href": "/product/static/csv/product.template.csv"});
            this.$(".template-import").removeClass("hidden");
        }
    },   
});

});
