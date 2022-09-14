/** @odoo-module **/

import { patchFields } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@mail/models/message_view';

patchFields('MessageView', {
    isInDiscuss: {
        compute() {
            return Boolean(
                this.messageListViewItemOwner &&
                this.messageListViewItemOwner.messageListViewOwner.threadViewOwner.threadViewer.discussPublicView
            );
        },
    },
});

