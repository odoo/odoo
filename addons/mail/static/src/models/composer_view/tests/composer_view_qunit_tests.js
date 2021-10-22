/** @odoo-module **/

import { addFields, patchIdentifyingFields, patchRecordMethods } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/composer_view/composer_view';

patchRecordMethods('mail.composer_view', {
    _computeComposer() {
        if (this.qunitTest && this.qunitTest.composer) {
            return replace(this.qunitTest.composer);
        }
        return this._super();
    },
});

addFields('mail.composer_view', {
    qunitTest: one2one('mail.qunit_test', {
        inverse: 'composerView',
        readonly: true,
    }),
});

patchIdentifyingFields('mail.composer_view', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
