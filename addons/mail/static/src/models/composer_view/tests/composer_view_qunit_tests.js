/** @odoo-module **/

import { registerFieldPatchModel, registerIdentifyingFieldsPatch, registerInstancePatchModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import { replace } from '@mail/model/model_field_command';

registerInstancePatchModel('mail.composer_view', 'qunit', {
    _computeComposer() {
        if (this.qunitTest && this.qunitTest.composer) {
            return replace(this.qunitTest.composer);
        }
        return this._super();
    }
});

registerFieldPatchModel('mail.composer_view', 'qunit', {
    qunitTest: one2one('mail.qunit_test', {
        inverse: 'composerView',
        readonly: true,
    }),
});

registerIdentifyingFieldsPatch('mail.composer_view', 'qunit', identifyingFields => {
    identifyingFields[0].push('qunitTest');
});
