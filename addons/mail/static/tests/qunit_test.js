/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerModel({
    name: 'QUnitTest',
    identifyingFields: [], // singleton acceptable (only one test at a time)
    fields: {
        composer: one2one('Composer', {
            isCausal: true,
        }),
        composerView: one2one('ComposerView', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
        messageView: one2one('MessageView', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
        threadViewer: one2one('ThreadViewer', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
    },
});
