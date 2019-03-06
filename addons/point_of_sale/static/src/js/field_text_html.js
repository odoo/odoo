odoo.define('point_of_sale.fieldtexthtml', function (require) {
    'use strict';

    var FieldTextHtml = require('web_editor.backend').FieldTextHtml;

    FieldTextHtml.include({
        // avoid '414 Request-URI Too Large' errors to
        // /point_of_sale/field/customer_facing_display_template by
        // filtering out biggest fields
        getDatarecord: function () {
            var datarecord = this._super();
            if (this.model === 'pos.config') {
                datarecord = _.omit(datarecord, function (val, key) {
                    return _.isObject(val) || key === 'customer_facing_display_html';
                });
            }
            return datarecord;
        },
    });
});
