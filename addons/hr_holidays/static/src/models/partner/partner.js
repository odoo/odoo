odoo.define('hr_holidays/static/src/models/partner/partner.js', function (require) {
'use strict';

const {
    registerClassPatchModel,
    registerFieldPatchModel,
} = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field_utils.js');

const { str_to_datetime } = require('web.time');

registerClassPatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {

    //----------------------------------------------------------------------
    // Public
    //----------------------------------------------------------------------

    convertData(data) {
        const data2 = this._super(data);
        if ('out_of_office_date_end' in data && data.date) {
            data2.__mfield_out_of_office_date_end = new Date(str_to_datetime(data.out_of_office_date_end));
        }
        return data2;
    },
});

registerFieldPatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {
    __mfield_out_of_office_date_end: attr({
        default() {
            return new Date();
        },
    }),
});

});
