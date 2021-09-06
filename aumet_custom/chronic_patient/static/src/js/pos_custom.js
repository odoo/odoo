odoo.define('pos_chronic_patient', function (require) {
    "use strict";
    
    const models = require('point_of_sale.models');
    const {patch} = require('web.utils');
    const ClientDetailsEdit = require('point_of_sale.ClientDetailsEdit');

    models.load_fields('res.partner', ['chronic_patient',]);

    patch(ClientDetailsEdit, 'pos_chronic_patient', {
        captureChange(event) {
            this._super(event);
            if (event.target.type === 'checkbox') {
                this.changes[event.target.name] = event.currentTarget.checked;
            }
        }
    });

});