odoo.define('sms.onchange_in_keyup', function (require) {
    "use strict";
    var FieldChar = require('web.basic_fields').FieldChar;
    var fieldRegistry = require('web.field_registry');

    var OnChangeInKeyup = FieldChar.extend({
        _renderEdit: function () {
            var def = this._super.apply(this, arguments);
            this.$el.on('keyup', (e) => {
                $(e.target).trigger('change')
            })
            return def;
        },
    });

    fieldRegistry.add('onchange_in_keyup', OnChangeInKeyup);
    return OnChangeInKeyup;
});