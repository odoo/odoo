/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the view that displays either the single record of the group or
        all the records in the group.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            NotificationGroup/openDocuments
        [Action/params]
            notificationGroup
                [type]
                    NotificationGroup
        [Action/behavior]
            {if}
                @notificationGroup
                .{NotificationGroup/thread}
            .{then}
                {Thread/open}
                    @notificationGroup
                    .{NotificationGroup/thread}
            .{else}
                {NotificationGroup/_openDocuments}
                    @notificationGroup
`;
