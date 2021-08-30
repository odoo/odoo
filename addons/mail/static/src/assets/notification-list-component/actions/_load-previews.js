/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Load previews of given thread. Basically consists of fetching all missing
        last messages of each thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            NotificationListComponent/_loadPreviews
        [Action/params]
            record
                [type]
                    NotificationListComponent
        [Action/behavior]
            :threads
                @record
                .{NotificationListComponent/notificationListView}
                .{NotificationListView/threadPreviewViews}
                .{Collection/map}
                    {Record/insert}
                        [Record/models]
                            Function
                        [Function/in]
                            item
                        [Function/out]
                            @item
                            .{ThreadPreviewView/thread}
            {Thread/loadPreviews}
                @threads
`;
