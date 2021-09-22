odoo.define('hr_holidays/static/src/models/partner/partner.js', function (require) {
'use strict';

const {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel,
} = require('@mail/model/model_core');
const { attr } = require('@mail/model/model_field');
const { clear } = require('@mail/model/model_field_command');

const { str_to_date } = require('web.time');

registerClassPatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('out_of_office_date_end' in data) {
            data2.outOfOfficeDateEnd = data.out_of_office_date_end ? data.out_of_office_date_end : clear();
        }
        return data2;
    },
});

registerInstancePatchModel('mail.partner', 'hr_holidays/static/src/models/partner/partner.js', {
    /**
     * @private
     */
    _computeOutOfOfficeText() {
        if (!this.outOfOfficeDateEnd) {
            return clear();
        }
        if (!this.messaging.locale || !this.messaging.locale.language) {
            return clear();
        }
        const currentDate = new Date();
        const date = str_to_date(this.outOfOfficeDateEnd);
        const options = { day: 'numeric', month: 'short' };
        if (currentDate.getFullYear() !== date.getFullYear()) {
            options.year = 'numeric';
        }
        const localeCode = this.messaging.locale.language.replace(/_/g, '-');
        const formattedDate = date.toLocaleDateString(localeCode, options);
        return _.str.sprintf(this.env._t("Out of office until %s"), formattedDate);
    },
    /**
     * @override
     */
    _computeIsOnline() {
        if (['leave_online', 'leave_away'].includes(this.im_status)) {
            return true;
        }
        return this._super();
    },
});

registerFieldPatchModel('mail.partner', 'hr/static/src/models/partner/partner.js', {
    /**
     * Date of end of the out of office period of the partner as string.
     * String is expected to use Odoo's date string format
     * (examples: '2011-12-01' or '2011-12-01').
     */
    outOfOfficeDateEnd: attr(),
    /**
     * Text shown when partner is out of office.
     */
    outOfOfficeText: attr({
        compute: '_computeOutOfOfficeText',
    }),
});

});
