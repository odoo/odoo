odoo.define('hr_holidays/static/src/models/partner/partner.js', function (require) {
'use strict';

const {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');
const { attr, one2one } = require('mail/static/src/model/model_field.js');

const { str_to_datetime } = require('web.time');


registerClassPatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('out_of_office_date_end' in data) {
            data2.out_of_office_date_end = data.out_of_office_date_end;
        }
        return data2;
    },
});

registerInstancePatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {
    /**
     *
     * @private
     */
    _computeOutOfOfficeText() {
        if (!this.out_of_office_date_end) {
            return;
        }
        const currentDate = new Date();
        const date = str_to_datetime(this.out_of_office_date_end);
        const options = { day: 'numeric', month: 'short' };
        if (currentDate.getFullYear() !== date.getFullYear()) {
            options.year = 'numeric';
        }
        //FIXME should use this.messaging.locale
        const formattedDate = date.toLocaleDateString(window.navigator.language, options);
        return _.str.sprintf(this.env._t("Out of office until %s"), formattedDate);
    },

});

registerFieldPatchModel('mail.partner', 'hr/static/src/models/partner/partner.js', {
    messagingLocale: one2one('mail.locale', {
        related: 'messaging.locale',
    }),
    /**
     * Date of end of the out of office period of the partner.
     */
    out_of_office_date_end: attr(),
    /**
     * Text shown when partner is out of office.
     */
    outOfOfficeText: attr({
        compute: '_computeOutOfOfficeText',
        dependencies: [
            'messagingLocale',
            'out_of_office_date_end',
        ]
    })
});

});
