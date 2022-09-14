
/** @odoo-module **/

import { patchFields } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/composer_view';

patchFields('ComposerView', {
    isInDiscuss: {
        compute() {
            return Boolean(this.threadView && this.threadView.threadViewer.discussPublicView);
        },
    },
});
