odoo.define('stock.json_widget', function (require) {
'use strict';

const AbstractField = require('web.AbstractField');
const fieldRegistry = require('web.field_registry');
const core = require('web.core');
const QWeb = core.qweb;

const JsonWidget = AbstractField.extend({
    supportedFieldTypes: ['char'],

    _render: function () {
        var value = JSON.parse(this.value);
        if (!value || !value.template) {
            this.$el.html('');
            return;
        }
        $(QWeb.render(value.template, value)).appendTo(this.$el);
    },
});

fieldRegistry.add('json_widget', JsonWidget);

return JsonWidget;
});
