/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'QUnitTest',
    identifyingFields: [], // singleton acceptable (only one test at a time)
    fields: {
        clockWatcher: one('ClockWatcher', {
            inverse: 'qunitTestOwner',
        }),
        composer: one('Composer', {
            isCausal: true,
        }),
        composerView: one('ComposerView', {
            inverse: 'qunitTest',
        }),
        followerListMenuView: one('FollowerListMenuView', {
            inverse: 'qunitTest',
        }),
        messageView: one('MessageView', {
            inverse: 'qunitTest',
        }),
        notificationListView: one('NotificationListView', {
            inverse: 'qunitTestOwner',
        }),
        threadViewer: one('ThreadViewer', {
            inverse: 'qunitTest',
        }),
    },
});
