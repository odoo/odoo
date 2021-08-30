/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Chatter/onScrollScrollPanel
        [Action/params]
            record
                [type]
                    Chatter
            ev
                [type]
                    web.ScrollEvent
        [Action/behavior]
            {MessageListComponent/onScroll}
                [0]
                    @record
                    .{Chatter/threadView}
                    .{ThreadView/messageListView}
                    .{MessageListView/component}
                [1]
                    @ev
`;
