/** @odoo-module **/

import {
    registerFieldPatchModel,
    registerInstancePatchModel,
} from '@mail/model/model_core';
import { one2many } from '@mail/model/model_field';

registerInstancePatchModel('mail.messaging', 'im_livechat/static/src/models/messaging/messaging.js', {
    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @private
     * @returns [{mail.thread}]
     */
    _computeAllPinnedAndSortedLivechatTypeThreads() {
        const livechatThreads = this.allPinnedChannelModelThreads
            .filter(thread =>thread.channel_type === 'livechat')
            .sort((t1, t2) => {
                if(t1.lastActivityTime && t2.lastActivityTime) {
                    return t2.lastActivityTime - t1.lastActivityTime;
                }
                else if(t1.lastActivityTime) {
                    return -1;
                }
                else if(t2.lastActivityTime) {
                    return 1;
                }
                else {
                    return t2.id - t1.id;
                }
            });
        return [['replace', livechatThreads]];
    }
});

registerFieldPatchModel('mail.messaging', 'im_livechat/static/src/models/messaging/messaging.js', {
    allPinnedAndSortedLivechatTypeThreads: one2many('mail.thread', {
        compute: '_computeAllPinnedAndSortedLivechatTypeThreads',
        dependencies: ['allPinnedChannelModelThreads', 'allPinnedChannelModelThreadsChannelType', 'allPinnedChannelModelThreadsLastActivityTime'],
    }),
});
