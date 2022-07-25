/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

function factory(dependencies) {

    class Locale extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeLanguage() {
            return this.env._t.database.parameters.code;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeTextDirection() {
            return this.env._t.database.parameters.direction;
        }

    }

    Locale.fields = {
        /**
         * Language used by interface, formatted like {language ISO 2}_{country ISO 2} (eg: fr_FR).
         */
        language: attr({
            compute: '_computeLanguage',
        }),
        textDirection: attr({
            compute: '_computeTextDirection',
        }),
    };
    Locale.identifyingFields = ['messaging'];
    Locale.modelName = 'mail.locale';

    return Locale;
}

registerNewModel('mail.locale', factory);
