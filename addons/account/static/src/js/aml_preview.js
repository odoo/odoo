odoo.define('account.move.line.preview', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;


var AccountMoveLinePreviewWidget = AbstractField.extend({

    supportedFieldTypes: ['char'],

    /**
     * @private
     * @override
     */
    _render: function() {
        var self = this;
        var all_aml_data = JSON.parse(this.value);

        if (!all_aml_data) {
            this.$el.html('');
            return;
        }

        this.$el.html(QWeb.render('AccountMoveLinePreview', {
            lines_to_preview: all_aml_data,
        }));

    },
});

field_registry.add('aml_preview', AccountMoveLinePreviewWidget);

return {
    AccountMoveLinePreviewWidget: AccountMoveLinePreviewWidget
};

});