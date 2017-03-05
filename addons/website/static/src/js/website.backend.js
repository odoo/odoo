odoo.define('website.backend', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;


var WidgetWebsiteButton = AbstractField.extend({
    template: 'WidgetWebsiteButton',
    supportedFieldTypes: ['boolean'],

    render: function () {
        this._super.apply(this, arguments);

        var $value = this.$('.o_value');

        if (this.value === true) {
            $value.html(_t('Published'))
                  .removeClass('text-danger')
                  .addClass('text-success');
        } else {
            $value.html(_t('Unpublished'))
                  .removeClass('text-success')
                  .addClass('text-danger');
        }
    },
    is_set: function () {
        return true;
    },
});

field_registry.add('website_button', WidgetWebsiteButton);

});
