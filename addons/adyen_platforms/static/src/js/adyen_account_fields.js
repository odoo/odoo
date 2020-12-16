odoo.define('adyen_platforms.fields', function (require) {
"use strict";

var core = require('web.core');
var FieldSelection = require('web.relational_fields').FieldSelection;
var field_registry = require('web.field_registry');

var qweb = core.qweb;

var AdyenKYCStatusTag = FieldSelection.extend({
    _render: function () {
        this.$el.append(qweb.render('AdyenKYCStatusTag', {
            value: this.value,
        }));
    },
});

field_registry.add("adyen_kyc_status_tag", AdyenKYCStatusTag);

});
