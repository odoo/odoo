/** @odoo-module **/

import { addFields, patchRecordMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/timer';

addFields('Timer', {
    livechatButtonViewOwnerAsInitialFloatingTextVisibility: one('LivechatButtonView', {
        inverse: 'initialFloatingTextViewVisibilityTimer',
        identifying: true,
    }),
});

patchRecordMethods('Timer', {
    /**
     * @override
     */
    _computeDuration() {
        if (this.livechatButtonViewOwnerAsInitialFloatingTextVisibility) {
            return 1 * 1000;
        }
        return this._super();
    },
    /**
     * @override
     */
    onTimeout() {
        if (this.livechatButtonViewOwnerAsInitialFloatingTextVisibility) {
            this.livechatButtonViewOwnerAsInitialFloatingTextVisibility.update({ floatingTextView: {} });
            return;
        }
        return this._super();
    },
});
