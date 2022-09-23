/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerPatch({
    name: 'Timer',
    recordMethods: {
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
    },
    fields: {
        duration: {
            compute() {
                if (this.livechatButtonViewOwnerAsInitialFloatingTextVisibility) {
                    return 1 * 1000;
                }
                return this._super();
            },
        },
        livechatButtonViewOwnerAsInitialFloatingTextVisibility: one('LivechatButtonView', {
            inverse: 'initialFloatingTextViewVisibilityTimer',
            identifying: true,
        }),
    },
});
