/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { str_to_date } from 'web.time';

registerPatch({
    name: 'Partner',
    fields: {
        isOnline: {
            compute() {
                if (['leave_online', 'leave_away'].includes(this.im_status)) {
                    return true;
                }
                return this._super();
            },
        },
        /**
         * Date of end of the out of office period of the partner as string.
         * String is expected to use Odoo's date string format
         * (examples: '2011-12-01' or '2011-12-01').
         */
        out_of_office_date_end: attr(),
        /**
         * Text shown when partner is out of office.
         */
        outOfOfficeText: attr({
            compute() {
                if (!this.out_of_office_date_end) {
                    return clear();
                }
                if (!this.messaging.locale || !this.messaging.locale.language) {
                    return clear();
                }
                const currentDate = new Date();
                const date = str_to_date(this.out_of_office_date_end);
                const options = { day: 'numeric', month: 'short' };
                if (currentDate.getFullYear() !== date.getFullYear()) {
                    options.year = 'numeric';
                }
                let localeCode = this.messaging.locale.language.replace(/_/g, '-');
                if (localeCode === "sr@latin") {
                    localeCode = "sr-Latn-RS";
                }
                const formattedDate = date.toLocaleDateString(localeCode, options);
                return _.str.sprintf(this.env._t("Out of office until %s"), formattedDate);
            },
        }),
    },
});
