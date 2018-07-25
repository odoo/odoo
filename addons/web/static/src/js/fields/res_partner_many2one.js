odoo.define('web.res_partner_many2one', function (require) {
    "use strict";

    var fieldRegistry = require('web.field_registry');
    var FieldMany2One = require('web.relational_fields').FieldMany2One;

    var PartnerFieldMany2One = FieldMany2One.extend({});

    fieldRegistry.add('res_partner_many2one', PartnerFieldMany2One);

    return {
        PartnerFieldMany2One: PartnerFieldMany2One,
    };

});