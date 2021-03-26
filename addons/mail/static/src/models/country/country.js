/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Country extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         * @returns {string|undefined}
         */
        _computeFlagUrl() {
            if (!this.code) {
                return clear();
            }
            return `/base/static/img/country_flags/${this.code}.png`;
        }

    }

    Country.fields = {
        code: attr(),
        flagUrl: attr({
            compute: '_computeFlagUrl',
            dependencies: [
                'code',
            ],
        }),
        id: attr({
            required: true,
        }),
        name: attr(),
    };

    Country.modelName = 'mail.country';

    return Country;
}

registerNewModel('mail.country', factory);
