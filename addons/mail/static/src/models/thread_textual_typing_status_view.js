/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ThreadTextualTypingStatusView',
    fields: {
        composerViewOwner: one('ComposerView', {
            identifying: true,
            inverse: 'threadTextualTypingStatusView',
        }),
        thread: one('Thread', {
            compute() {
                return this.composerViewOwner.composer.activeThread;
            },
        })
    },
});
