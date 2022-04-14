/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'QUnitTest',
    identifyingFields: [], // singleton acceptable (only one test at a time)
    fields: {
        clockWatcher: one('ClockWatcher', {
            inverse: 'qunitTestOwner',
            isCausal: true,
        }),
        composer: one('Composer', {
            isCausal: true,
        }),
        composerView: one('ComposerView', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
        followerListMenuView: one('FollowerListMenuView', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
        messageView: one('MessageView', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
        notificationListView: one('NotificationListView', {
            inverse: 'qunitTestOwner',
            isCausal: true,
        }),
        threadViewer: one('ThreadViewer', {
            inverse: 'qunitTest',
            isCausal: true,
        }),
    },
});
