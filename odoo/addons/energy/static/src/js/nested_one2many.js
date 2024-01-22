odoo.define('your_module_assets', function (require) {
    'use strict';

    const FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    const registry = require('web.field_registry');
    const core = require('web.core');
    const QWeb = core.qweb;

    const NestedOne2Many = FieldOne2Many.extend({
        _render: function () {
            this._super.apply(this, arguments);
            this.$('.o_form_field_one2many_list').addClass('o_nested_table');
        },
    });

    registry.add('nested_one2many', NestedOne2Many);

    return {
        NestedOne2Many,
    };
});
