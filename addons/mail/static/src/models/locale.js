/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

import { localization } from '@web/core/l10n/localization';

registerModel({
    name: 'Locale',
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeLanguage() {
            return this.env.services.user.lang;
        },
        /**
         * @private
         * @returns {string}
         */
        _computeTextDirection() {
            return localization.direction;
        },
    },
    fields: {
        /**
         * Language used by interface, formatted like {language ISO 2}_{country ISO 2} (eg: fr_FR).
         */
        language: attr({
            compute: '_computeLanguage',
        }),
        textDirection: attr({
            compute: '_computeTextDirection',
        }),
    },
});
